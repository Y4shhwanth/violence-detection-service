"""
Policy-Aware Moderation Engine for Violence Detection System.

Lightweight RAG-style retrieval against hardcoded policy documents.
No vector database required — uses keyword matching and TF-IDF-like scoring
to surface the most relevant policy sections when violence is detected.
"""
from typing import Dict, Any, List, Optional, Set
import re

from .logging import get_logger

logger = get_logger(__name__)


# ---------------------------------------------------------------------------
# Hardcoded policy documents
# ---------------------------------------------------------------------------
POLICY_DOCUMENTS: List[Dict[str, Any]] = [
    {
        'id': 'violence-policy',
        'title': 'Platform Violence Policy',
        'sections': [
            {
                'section': '1.1 - Prohibited Violent Content',
                'text': (
                    'Content that depicts, promotes, or glorifies acts of physical '
                    'violence against individuals or groups is strictly prohibited. '
                    'This includes but is not limited to: assault, battery, fighting, '
                    'torture, and any form of physical harm.'
                ),
                'keywords': frozenset({
                    'violence', 'assault', 'attack', 'fight', 'beat', 'punch',
                    'kick', 'hit', 'harm', 'torture', 'battery',
                }),
            },
            {
                'section': '1.2 - Graphic Violence Exceptions',
                'text': (
                    'Educational, documentary, or newsworthy content depicting violence '
                    'may be permitted with appropriate content warnings and age-gating. '
                    'Such content must not glorify or promote the violent acts depicted.'
                ),
                'keywords': frozenset({
                    'educational', 'documentary', 'news', 'graphic', 'warning',
                }),
            },
            {
                'section': '1.3 - Enforcement Actions',
                'text': (
                    'Violations result in content removal and escalating account actions: '
                    'first offense receives a warning, second offense results in temporary '
                    'suspension, third offense leads to permanent account termination.'
                ),
                'keywords': frozenset({
                    'violation', 'removal', 'suspension', 'termination', 'enforce',
                }),
            },
        ],
    },
    {
        'id': 'community-safety',
        'title': 'Community Safety Policy',
        'sections': [
            {
                'section': '2.1 - Safe Environment Standards',
                'text': (
                    'All users are expected to maintain a respectful and safe environment. '
                    'Content that creates a hostile, intimidating, or threatening atmosphere '
                    'is subject to moderation and removal. This includes content depicting '
                    'real-world violence, dangerous activities, or harmful behavior.'
                ),
                'keywords': frozenset({
                    'safety', 'hostile', 'intimidating', 'threatening', 'dangerous',
                    'harmful', 'moderation',
                }),
            },
            {
                'section': '2.2 - User Reporting and Response',
                'text': (
                    'Reports of violent or threatening content are reviewed within 24 hours. '
                    'Content posing imminent danger to individuals is escalated immediately '
                    'to the Trust & Safety team and, where appropriate, law enforcement.'
                ),
                'keywords': frozenset({
                    'report', 'danger', 'imminent', 'escalate', 'law',
                    'enforcement', 'trust', 'safety',
                }),
            },
        ],
    },
    {
        'id': 'hate-speech',
        'title': 'Hate Speech Policy',
        'sections': [
            {
                'section': '3.1 - Prohibited Hate Content',
                'text': (
                    'Content that attacks, demeans, or incites violence against individuals '
                    'or groups based on protected characteristics — including race, ethnicity, '
                    'religion, gender, sexual orientation, disability, or national origin — '
                    'is strictly prohibited.'
                ),
                'keywords': frozenset({
                    'hate', 'discrimination', 'racism', 'bigotry', 'slur',
                    'dehumanize', 'incite', 'demean',
                }),
            },
            {
                'section': '3.2 - Hate-Motivated Violence',
                'text': (
                    'Content depicting or promoting violence motivated by hatred toward '
                    'protected groups is treated with maximum severity. Such content is '
                    'immediately removed and the account is permanently suspended. '
                    'Cases may be referred to law enforcement.'
                ),
                'keywords': frozenset({
                    'hate', 'violence', 'attack', 'kill', 'murder', 'massacre',
                    'genocide',
                }),
            },
        ],
    },
    {
        'id': 'threat-escalation',
        'title': 'Threat Escalation Policy',
        'sections': [
            {
                'section': '4.1 - Direct Threats',
                'text': (
                    'Any content containing direct, credible threats of violence against '
                    'specific individuals or groups is immediately escalated to the highest '
                    'priority review queue. This includes threats to kill, harm, or injure.'
                ),
                'keywords': frozenset({
                    'threat', 'threaten', 'kill', 'murder', 'harm', 'hurt',
                    'injure', 'destroy', 'die',
                }),
            },
            {
                'section': '4.2 - Escalation Protocol',
                'text': (
                    'Severity levels for threats: Level 1 (vague/indirect) — content review '
                    'within 4 hours. Level 2 (specific target) — immediate review and potential '
                    'law enforcement notification. Level 3 (imminent danger) — immediate law '
                    'enforcement contact and account suspension.'
                ),
                'keywords': frozenset({
                    'escalation', 'severity', 'imminent', 'law', 'enforcement',
                    'suspension', 'urgent',
                }),
            },
        ],
    },
    {
        'id': 'graphic-content',
        'title': 'Graphic Content Policy',
        'sections': [
            {
                'section': '5.1 - Graphic Visual Content',
                'text': (
                    'Content depicting graphic violence, gore, severe injuries, or death '
                    'is prohibited unless it serves a clearly educational or newsworthy '
                    'purpose. Gratuitous depictions of blood, wounds, or corpses are '
                    'always removed.'
                ),
                'keywords': frozenset({
                    'graphic', 'gore', 'blood', 'wound', 'corpse', 'death',
                    'dead', 'injury', 'bleed', 'dismember',
                }),
            },
            {
                'section': '5.2 - Disturbing Audio Content',
                'text': (
                    'Audio content capturing real violence — including screams, gunshots, '
                    'explosions, or sounds of physical assault — is subject to the same '
                    'restrictions as visual content. Such audio must be flagged for review.'
                ),
                'keywords': frozenset({
                    'scream', 'gunshot', 'explosion', 'assault', 'audio',
                    'sound', 'distress',
                }),
            },
            {
                'section': '5.3 - Content Warning Requirements',
                'text': (
                    'Permitted graphic content (educational/news) must include prominent '
                    'content warnings, be age-gated to 18+, and must not appear in '
                    'recommendation feeds or public listings without explicit user opt-in.'
                ),
                'keywords': frozenset({
                    'warning', 'age', 'gate', 'content', 'sensitive',
                }),
            },
        ],
    },
]


class PolicyEngine:
    """
    Matches detected violence indicators against platform policy documents.
    Returns relevant policy sections that apply to the flagged content.
    """

    def __init__(self):
        self.policies = POLICY_DOCUMENTS
        self.logger = get_logger(__name__)

    def evaluate(
        self,
        video_result: Optional[Dict[str, Any]] = None,
        audio_result: Optional[Dict[str, Any]] = None,
        text_result: Optional[Dict[str, Any]] = None,
        fused_result: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Evaluate analyzer outputs against policy documents.

        Returns:
            {
                "policy_triggered": bool,
                "matched_policies": [
                    {
                        "title": str,
                        "section": str,
                        "explanation": str,
                        "relevance_score": float
                    }
                ],
                "total_policies_matched": int,
                "recommended_severity": str
            }
        """
        # Extract all evidence keywords from results
        evidence_keywords = self._extract_evidence_keywords(
            video_result, audio_result, text_result
        )

        if not evidence_keywords:
            return {
                'policy_triggered': False,
                'matched_policies': [],
                'total_policies_matched': 0,
                'recommended_severity': 'none',
            }

        # Match against policies
        matched = self._match_policies(evidence_keywords)

        # Determine recommended severity from matches
        recommended_severity = self._determine_severity(matched, evidence_keywords)

        self.logger.info(
            f"Policy evaluation: {len(matched)} sections matched, "
            f"severity={recommended_severity}"
        )

        return {
            'policy_triggered': len(matched) > 0,
            'matched_policies': matched,
            'total_policies_matched': len(matched),
            'recommended_severity': recommended_severity,
        }

    def _extract_evidence_keywords(
        self,
        video_result: Optional[Dict[str, Any]],
        audio_result: Optional[Dict[str, Any]],
        text_result: Optional[Dict[str, Any]],
    ) -> Set[str]:
        """Extract all relevant keywords from analyzer outputs."""
        keywords: Set[str] = set()

        # Text keywords
        if text_result and text_result.get('class') == 'Violence':
            for kw in text_result.get('keywords_found', []):
                word = kw.split('(')[0].strip().lower()
                keywords.add(word)
            # Also extract from reasoning
            reasoning = text_result.get('reasoning', '').lower()
            keywords.update(self._extract_words(reasoning))

        # Video indicators
        if video_result and video_result.get('class') == 'Violence':
            for frame in video_result.get('violent_frames', []):
                for indicator in frame.get('indicators', []):
                    keywords.update(self._extract_words(str(indicator).lower()))
                ml = frame.get('ml_detection', '')
                if ml:
                    keywords.update(self._extract_words(ml.lower()))
            keywords.add('violence')
            keywords.add('graphic')

        # Audio indicators
        if audio_result and audio_result.get('class') == 'Violence':
            for sound in audio_result.get('detected_sounds', []):
                word = sound.split('(')[0].strip().lower()
                keywords.add(word)
            keywords.add('audio')
            keywords.add('sound')

        return keywords

    def _extract_words(self, text: str) -> Set[str]:
        """Extract meaningful words from text."""
        words = set(re.findall(r'[a-z]+', text))
        # Filter out very short / common words
        return {w for w in words if len(w) > 2}

    def _match_policies(
        self,
        evidence_keywords: Set[str],
    ) -> List[Dict[str, Any]]:
        """Match evidence keywords against policy sections."""
        matched = []

        for policy in self.policies:
            for section in policy['sections']:
                section_keywords = section['keywords']
                overlap = evidence_keywords & section_keywords

                if not overlap:
                    continue

                # Relevance score: fraction of section keywords matched
                relevance = len(overlap) / len(section_keywords)

                if relevance >= 0.1:  # At least 10% keyword overlap
                    matched.append({
                        'title': policy['title'],
                        'policy_id': policy['id'],
                        'section': section['section'],
                        'explanation': section['text'],
                        'matched_keywords': sorted(overlap),
                        'relevance_score': round(relevance, 3),
                    })

        # Sort by relevance (highest first) and deduplicate
        matched.sort(key=lambda x: x['relevance_score'], reverse=True)

        # Return top 5 most relevant
        return matched[:5]

    def _determine_severity(
        self,
        matched: List[Dict[str, Any]],
        evidence_keywords: Set[str],
    ) -> str:
        """Determine recommended severity based on matched policies."""
        if not matched:
            return 'none'

        # Check for critical indicators
        critical_keywords = {'kill', 'murder', 'massacre', 'genocide', 'threat'}
        if evidence_keywords & critical_keywords:
            return 'critical'

        # Check for high-severity based on policy match density
        max_relevance = max(m['relevance_score'] for m in matched)
        if max_relevance > 0.5 or len(matched) >= 4:
            return 'high'

        if max_relevance > 0.3 or len(matched) >= 2:
            return 'medium'

        return 'low'


# ---------------------------------------------------------------------------
# Module-level singleton
# ---------------------------------------------------------------------------
_policy_engine: Optional[PolicyEngine] = None


def get_policy_engine() -> PolicyEngine:
    """Get or create global PolicyEngine instance."""
    global _policy_engine
    if _policy_engine is None:
        _policy_engine = PolicyEngine()
    return _policy_engine
