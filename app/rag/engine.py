"""
RAG Policy Engine.
Builds query from evidence, retrieves top-5 policy sections via vector similarity.
Same output format as existing PolicyEngine.
"""
import re
from typing import Dict, Any, List, Optional, Set

from .vector_store import FAISSVectorStore
from .policy_documents import POLICY_DOCUMENTS
from ..config import get_config
from ..utils.logging import get_logger

logger = get_logger(__name__)


class RAGPolicyEngine:
    """Semantic policy matching using FAISS + sentence-transformers."""

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return

        config = get_config().rag
        self.vector_store = FAISSVectorStore(
            embedding_model=config.embedding_model,
            index_path=config.index_path,
        )
        self._build_index()
        self._initialized = True

    def _build_index(self):
        """Build vector index from policy documents."""
        # Try loading existing index first
        if self.vector_store.load():
            logger.info("Loaded existing FAISS policy index")
            return

        # Build new index
        documents = []
        for policy in POLICY_DOCUMENTS:
            for section in policy['sections']:
                documents.append({
                    'text': section['text'],
                    'section': section['section'],
                    'title': policy['title'],
                    'policy_id': policy['id'],
                })

        self.vector_store.build_index(documents)

        # Save for next time
        try:
            self.vector_store.save()
        except Exception as e:
            logger.warning(f"Failed to save FAISS index: {e}")

    def evaluate(
        self,
        video_result: Optional[Dict[str, Any]] = None,
        audio_result: Optional[Dict[str, Any]] = None,
        text_result: Optional[Dict[str, Any]] = None,
        fused_result: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Evaluate analysis results against policies using semantic search.
        Returns same format as keyword-based PolicyEngine.
        """
        # Build search query from evidence
        query = self._build_query(video_result, audio_result, text_result, fused_result)

        if not query.strip():
            return {
                'policy_triggered': False,
                'matched_policies': [],
                'total_policies_matched': 0,
                'recommended_severity': 'none',
            }

        # Search vector store
        results = self.vector_store.search(query, top_k=5)

        # Filter by relevance threshold
        matched = []
        for r in results:
            if r.get('similarity_score', 0) > 0.3:  # Minimum relevance
                matched.append({
                    'title': r.get('title', ''),
                    'policy_id': r.get('policy_id', ''),
                    'section': r.get('section', ''),
                    'explanation': r.get('text', ''),
                    'relevance_score': round(r.get('similarity_score', 0), 3),
                    'matched_keywords': [],  # Semantic matching doesn't use keywords
                })

        # Determine severity
        evidence_keywords = self._extract_evidence_keywords(video_result, audio_result, text_result)
        recommended_severity = self._determine_severity(matched, evidence_keywords)

        logger.info(f"RAG policy evaluation: {len(matched)} sections matched, severity={recommended_severity}")

        return {
            'policy_triggered': len(matched) > 0,
            'matched_policies': matched,
            'total_policies_matched': len(matched),
            'recommended_severity': recommended_severity,
            'search_method': 'rag_semantic',
        }

    def _build_query(
        self,
        video_result: Optional[Dict[str, Any]],
        audio_result: Optional[Dict[str, Any]],
        text_result: Optional[Dict[str, Any]],
        fused_result: Optional[Dict[str, Any]],
    ) -> str:
        """Build a natural language query from evidence."""
        parts = []

        if fused_result:
            decision = fused_result.get('decision_tier', fused_result.get('class', ''))
            if decision:
                parts.append(f"Content classified as {decision}")

        if video_result and video_result.get('class') == 'Violence':
            reasoning = video_result.get('reasoning', '')
            if reasoning:
                parts.append(f"Video shows: {reasoning[:200]}")

        if audio_result and audio_result.get('class') == 'Violence':
            sounds = audio_result.get('detected_sounds', [])
            if sounds:
                parts.append(f"Audio contains: {', '.join(sounds[:5])}")

        if text_result and text_result.get('class') == 'Violence':
            keywords = text_result.get('keywords_found', [])
            if keywords:
                parts.append(f"Text contains violence indicators: {', '.join(keywords[:5])}")

        return '. '.join(parts)

    def _extract_evidence_keywords(
        self,
        video_result: Optional[Dict[str, Any]],
        audio_result: Optional[Dict[str, Any]],
        text_result: Optional[Dict[str, Any]],
    ) -> Set[str]:
        """Extract keywords for severity determination."""
        keywords = set()

        if text_result and text_result.get('class') == 'Violence':
            for kw in text_result.get('keywords_found', []):
                word = kw.split('(')[0].strip().lower()
                keywords.add(word)

        if video_result and video_result.get('class') == 'Violence':
            keywords.add('violence')
            keywords.add('graphic')

        if audio_result and audio_result.get('class') == 'Violence':
            for sound in audio_result.get('detected_sounds', []):
                word = sound.split('(')[0].strip().lower()
                keywords.add(word)

        return keywords

    def _determine_severity(self, matched: List[Dict], evidence_keywords: Set[str]) -> str:
        """Determine severity from matches and evidence."""
        if not matched:
            return 'none'

        critical_keywords = {'kill', 'murder', 'massacre', 'genocide', 'threat'}
        if evidence_keywords & critical_keywords:
            return 'critical'

        max_relevance = max(m['relevance_score'] for m in matched) if matched else 0
        if max_relevance > 0.6 or len(matched) >= 4:
            return 'high'
        if max_relevance > 0.4 or len(matched) >= 2:
            return 'medium'
        return 'low'


_rag_policy_engine: Optional[RAGPolicyEngine] = None


def get_rag_policy_engine() -> RAGPolicyEngine:
    """Get global RAGPolicyEngine instance."""
    global _rag_policy_engine
    if _rag_policy_engine is None:
        _rag_policy_engine = RAGPolicyEngine()
    return _rag_policy_engine
