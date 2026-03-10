"""
AI Moderation Copilot Service.

Provides an explainable AI chat interface for querying analysis results.
Pipeline: question + analysis_id -> retrieve stored result -> retrieve
policy matches via RAG -> generate LLM explanation.

Supports natural language questions like:
    - "Why was this flagged as violent?"
    - "What policy does this violate?"
    - "Show me the evidence"
    - "Is this a false positive?"
"""
import json
from typing import Dict, Any, Optional, List

from ..utils.logging import get_logger

logger = get_logger(__name__)

# Pre-defined question templates for common queries
QUESTION_TEMPLATES = {
    'why_flagged': [
        'why', 'flagged', 'detected', 'classified', 'violent', 'violation',
    ],
    'evidence': [
        'evidence', 'proof', 'frames', 'show me', 'what was detected',
    ],
    'policy': [
        'policy', 'rule', 'guideline', 'violate', 'compliance', 'regulation',
    ],
    'false_positive': [
        'false positive', 'mistake', 'incorrect', 'wrong', 'not violent',
        'false alarm', 'misclassified',
    ],
    'recommendation': [
        'recommend', 'suggest', 'what should', 'action', 'fix', 'resolve',
    ],
    'confidence': [
        'confidence', 'score', 'certain', 'sure', 'probability', 'how confident',
    ],
    'severity': [
        'severity', 'serious', 'how bad', 'risk level', 'danger',
    ],
}


class AICopilot:
    """
    Explainable AI assistant for content moderation analysis.

    Retrieves stored analysis results and generates contextual,
    evidence-backed answers to moderator questions.
    """

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def ask(
        self,
        question: str,
        analysis_id: Optional[str] = None,
        analysis_data: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Answer a question about an analysis result.

        Args:
            question:      Natural language question from the moderator.
            analysis_id:   Job ID to look up stored results (optional).
            analysis_data: Pre-loaded analysis results dict (optional).

        Returns:
            Dict with answer, evidence_frames, policies, and metadata.
        """
        # Step 1: Retrieve analysis data
        result = analysis_data
        if not result and analysis_id:
            result = self._retrieve_analysis(analysis_id)

        if not result:
            return {
                'answer': 'No analysis data found. Please provide an analysis ID or run an analysis first.',
                'evidence_frames': [],
                'policies': [],
                'question_type': 'unknown',
            }

        # Step 2: Classify the question type
        question_type = self._classify_question(question)

        # Step 3: Retrieve relevant policy context via RAG
        policies = self._retrieve_policies(question, result)

        # Step 4: Generate answer based on question type and data
        answer = self._generate_answer(question, question_type, result, policies)

        # Step 5: Extract evidence frames if relevant
        evidence_frames = self._extract_evidence(result, question_type)

        response = {
            'answer': answer,
            'evidence_frames': evidence_frames,
            'policies': policies,
            'question_type': question_type,
            'analysis_id': analysis_id,
            'final_decision': result.get('final_decision', 'Unknown'),
            'confidence': result.get('confidence', 0),
        }

        logger.info(
            f"Copilot answered question_type={question_type}, "
            f"analysis_id={analysis_id}, policies={len(policies)}"
        )

        return response

    def _retrieve_analysis(self, analysis_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve stored analysis result from database by job_id."""
        try:
            from ..database.session import get_db_session
            from ..database.models import AnalysisResult

            with get_db_session() as session:
                record = session.query(AnalysisResult).filter_by(
                    job_id=analysis_id
                ).first()
                if record and record.result_json:
                    return json.loads(record.result_json)
        except Exception as e:
            logger.warning(f"Failed to retrieve analysis {analysis_id}: {e}")
        return None

    def _classify_question(self, question: str) -> str:
        """Classify the user's question into a known category."""
        q_lower = question.lower()

        best_match = 'general'
        best_score = 0

        for category, keywords in QUESTION_TEMPLATES.items():
            score = sum(1 for kw in keywords if kw in q_lower)
            if score > best_score:
                best_score = score
                best_match = category

        return best_match

    def _retrieve_policies(
        self, question: str, result: Dict[str, Any]
    ) -> List[Dict[str, str]]:
        """Retrieve relevant policy sections using RAG or keyword engine."""
        policies = []

        # First try: use existing policy_matches from the analysis
        existing_policies = result.get('policy_matches', {})
        matched = existing_policies.get('matched_policies', [])
        if matched:
            for p in matched[:3]:
                policies.append({
                    'title': p.get('policy', p.get('title', 'Policy')),
                    'description': p.get('description', p.get('section', '')),
                    'relevance': p.get('relevance', 'matched'),
                })

        # Second try: RAG semantic search for question-specific policies
        if len(policies) < 3:
            try:
                from ..config import get_config
                rag_config = get_config().rag
                if rag_config.use_rag:
                    from ..rag import get_rag_policy_engine
                    rag = get_rag_policy_engine()
                    rag_results = rag.search(question, top_k=3)
                    for doc in rag_results:
                        policies.append({
                            'title': doc.get('title', 'Policy'),
                            'description': doc.get('text', doc.get('content', '')),
                            'relevance': f"similarity: {doc.get('score', 0):.2f}",
                        })
            except Exception as e:
                logger.debug(f"RAG policy search unavailable: {e}")

        return policies[:5]

    def _generate_answer(
        self,
        question: str,
        question_type: str,
        result: Dict[str, Any],
        policies: List[Dict],
    ) -> str:
        """
        Generate a human-readable answer based on the question type
        and analysis data. Uses LLM when available, falls back to
        deterministic template-based responses.
        """
        # Try LLM-based answer first
        llm_answer = self._try_llm_answer(question, result, policies)
        if llm_answer:
            return llm_answer

        # Deterministic fallback based on question type
        return self._deterministic_answer(question_type, result, policies)

    def _try_llm_answer(
        self,
        question: str,
        result: Dict[str, Any],
        policies: List[Dict],
    ) -> Optional[str]:
        """Attempt to generate an LLM-based answer. Returns None on failure."""
        try:
            from ..utils.llm_explainer import get_llm_explainer
            explainer = get_llm_explainer()

            # Build context for the LLM
            context = self._build_llm_context(result, policies)

            prompt = (
                f"You are an AI content moderation assistant. "
                f"A moderator asks: \"{question}\"\n\n"
                f"Analysis context:\n{context}\n\n"
                f"Provide a clear, evidence-based answer. Be specific about "
                f"what was detected and reference the data."
            )

            # Use the explainer's underlying model if it has one
            if hasattr(explainer, 'generate_text'):
                return explainer.generate_text(prompt, max_length=300)
        except Exception as e:
            logger.debug(f"LLM answer generation failed: {e}")
        return None

    def _build_llm_context(
        self, result: Dict[str, Any], policies: List[Dict]
    ) -> str:
        """Build a concise context string for LLM prompting."""
        parts = []

        decision = result.get('final_decision', 'Unknown')
        confidence = result.get('confidence', 0)
        parts.append(f"Decision: {decision} (confidence: {confidence:.1f}%)")

        # Modality summaries
        for modality in ['video', 'audio', 'text']:
            pred = result.get(f'{modality}_prediction')
            if pred and pred.get('class') != 'Error':
                parts.append(
                    f"{modality.title()}: {pred.get('class')} "
                    f"({pred.get('confidence', 0):.0f}%)"
                )

        # Violations
        violations = result.get('violations', [])
        if violations:
            parts.append(f"Violations: {len(violations)} detected")
            for v in violations[:3]:
                parts.append(
                    f"  - {v.get('modality', '?')}: {v.get('reason', 'N/A')} "
                    f"({v.get('start_time', 'N/A')})"
                )

        # Severity
        severity = result.get('severity', {})
        if severity:
            parts.append(
                f"Severity: {severity.get('severity_label', 'N/A')} "
                f"({severity.get('severity_score', 0):.0f})"
            )

        # Risk scoring
        risk = result.get('risk_score', {})
        if risk:
            parts.append(
                f"Risk: {risk.get('violence_probability', 0):.1f}% "
                f"({risk.get('risk_level', 'N/A')})"
            )

        # Policies
        if policies:
            parts.append("Relevant policies:")
            for p in policies[:2]:
                parts.append(f"  - {p.get('title', 'N/A')}")

        return '\n'.join(parts)

    def _deterministic_answer(
        self,
        question_type: str,
        result: Dict[str, Any],
        policies: List[Dict],
    ) -> str:
        """Generate a template-based answer when LLM is unavailable."""
        decision = result.get('final_decision', 'Unknown')
        confidence = result.get('confidence', 0)

        if question_type == 'why_flagged':
            return self._answer_why_flagged(result, decision, confidence)
        elif question_type == 'evidence':
            return self._answer_evidence(result)
        elif question_type == 'policy':
            return self._answer_policy(result, policies)
        elif question_type == 'false_positive':
            return self._answer_false_positive(result)
        elif question_type == 'recommendation':
            return self._answer_recommendation(result)
        elif question_type == 'confidence':
            return self._answer_confidence(result, confidence)
        elif question_type == 'severity':
            return self._answer_severity(result)
        else:
            return self._answer_general(result, decision, confidence)

    def _answer_why_flagged(
        self, result: Dict, decision: str, confidence: float
    ) -> str:
        """Explain why content was flagged."""
        parts = [f"The content was classified as **{decision}** with {confidence:.1f}% confidence."]

        # Add modality-specific reasons
        for modality in ['video', 'audio', 'text']:
            pred = result.get(f'{modality}_prediction')
            if pred and pred.get('class') == 'Violence':
                reasoning = pred.get('reasoning', '')
                parts.append(
                    f"\n**{modality.title()} analysis:** Detected violence "
                    f"({pred.get('confidence', 0):.0f}% confidence). "
                    f"{reasoning[:200] if reasoning else ''}"
                )

        violations = result.get('violations', [])
        if violations:
            parts.append(f"\n**{len(violations)} violation(s)** were identified across the content.")

        explanation = result.get('structured_explanation', {})
        summary = explanation.get('summary', '')
        if summary:
            parts.append(f"\n**Summary:** {summary}")

        return '\n'.join(parts)

    def _answer_evidence(self, result: Dict) -> str:
        """Describe the evidence found."""
        parts = ["Here is the evidence found in the analysis:"]

        # Video evidence
        video = result.get('video_prediction', {})
        if video:
            violent_frames = video.get('violent_frames', [])
            if violent_frames:
                parts.append(
                    f"\n**Video:** {len(violent_frames)} frame(s) with violent content detected."
                )
                for f in violent_frames[:3]:
                    parts.append(
                        f"  - Frame at {f.get('timestamp', 'N/A')}: "
                        f"score {f.get('violence_score', 0):.0f}"
                    )

        # Audio evidence
        audio = result.get('audio_prediction', {})
        if audio:
            sounds = audio.get('detected_sounds', [])
            if sounds:
                parts.append(f"\n**Audio:** Detected sounds: {', '.join(sounds[:5])}")

        # Text evidence
        text = result.get('text_prediction', {})
        if text:
            keywords = text.get('keywords_found', [])
            if keywords:
                parts.append(f"\n**Text:** Keywords found: {', '.join(keywords[:5])}")

        if len(parts) == 1:
            parts.append("\nNo specific evidence items were recorded in this analysis.")

        return '\n'.join(parts)

    def _answer_policy(self, result: Dict, policies: List[Dict]) -> str:
        """Explain which policies apply."""
        if not policies:
            pm = result.get('policy_matches', {})
            matched = pm.get('matched_policies', [])
            if not matched:
                return "No specific policy violations were identified in this analysis."
            policies = [
                {'title': p.get('policy', 'Policy'), 'description': p.get('description', '')}
                for p in matched
            ]

        parts = ["The following policies are relevant to this content:"]
        for p in policies[:5]:
            parts.append(f"\n**{p.get('title', 'Policy')}:** {p.get('description', 'N/A')[:300]}")

        return '\n'.join(parts)

    def _answer_false_positive(self, result: Dict) -> str:
        """Assess false positive likelihood."""
        fp = result.get('false_positive_analysis', {})
        category = fp.get('category', 'unknown')

        if category in ('sports_context', 'gaming_context', 'movie_context', 'news_context'):
            return (
                f"This may be a **false positive**. The system detected a "
                f"**{category.replace('_', ' ')}** which can contain staged or "
                f"fictional violence. Consider reviewing the context before taking action."
            )
        elif category == 'not_applicable':
            return "The content was not flagged as violent, so false positive analysis is not applicable."
        else:
            confidence = result.get('confidence', 0)
            if confidence < 60:
                return (
                    "The confidence score is relatively low, suggesting some uncertainty. "
                    "Manual review is recommended to confirm the classification."
                )
            return (
                "Based on the analysis, the detection appears genuine. "
                "Multiple indicators support the classification. "
                "If you believe this is incorrect, please submit feedback."
            )

    def _answer_recommendation(self, result: Dict) -> str:
        """Provide recommended actions."""
        action = result.get('recommended_action', '')
        decision = result.get('final_decision', 'Unknown')

        parts = []
        if action:
            parts.append(f"**Recommended action:** {action}")

        if decision == 'Violation':
            parts.append("The content should be removed or edited before publishing.")
        elif decision == 'Review Required':
            parts.append("Manual review is recommended. The content has moderate indicators.")
        else:
            parts.append("No action required. The content appears safe for publishing.")

        explanation = result.get('structured_explanation', {})
        suggestion = explanation.get('compliance_suggestion', '')
        if suggestion:
            parts.append(f"\n**Compliance suggestion:** {suggestion}")

        return '\n'.join(parts) if parts else "No specific recommendations available."

    def _answer_confidence(self, result: Dict, confidence: float) -> str:
        """Explain confidence levels."""
        parts = [f"The overall confidence score is **{confidence:.1f}%**."]

        fused = result.get('fused_prediction', {})
        cal_scores = fused.get('calibrated_scores', {})
        if cal_scores:
            parts.append("\n**Per-modality confidence (calibrated):**")
            for m, s in cal_scores.items():
                parts.append(f"  - {m.title()}: {s:.1f}%")

        fusion_method = fused.get('fusion_method', 'weighted')
        parts.append(f"\nFusion method: {fusion_method}")

        return '\n'.join(parts)

    def _answer_severity(self, result: Dict) -> str:
        """Explain severity assessment."""
        severity = result.get('severity', {})
        risk = result.get('risk_score', {})

        parts = []
        if severity:
            parts.append(
                f"**Severity:** {severity.get('severity_label', 'Unknown')} "
                f"(score: {severity.get('severity_score', 0):.0f}/100)"
            )

        if risk:
            parts.append(
                f"**Risk level:** {risk.get('risk_level', 'Unknown')} "
                f"(probability: {risk.get('violence_probability', 0):.1f}%)"
            )
            rec = risk.get('recommendation', '')
            if rec:
                parts.append(f"\n{rec}")

        if not parts:
            return "Severity information is not available for this analysis."

        return '\n'.join(parts)

    def _answer_general(
        self, result: Dict, decision: str, confidence: float
    ) -> str:
        """General answer for unclassified questions."""
        parts = [
            f"This content was classified as **{decision}** "
            f"with **{confidence:.1f}%** confidence.",
        ]

        violations = result.get('violations', [])
        if violations:
            parts.append(f"\n{len(violations)} violation(s) were detected.")

        parts.append(
            "\nYou can ask specific questions like:\n"
            "- \"Why was this flagged?\"\n"
            "- \"Show me the evidence\"\n"
            "- \"What policies apply?\"\n"
            "- \"Is this a false positive?\"\n"
            "- \"What should I do?\""
        )

        return '\n'.join(parts)

    def _extract_evidence(
        self, result: Dict[str, Any], question_type: str
    ) -> List[Dict[str, Any]]:
        """Extract evidence frame data for the frontend to display."""
        evidence = []

        video = result.get('video_prediction', {})
        if video:
            for frame in video.get('violent_frames', [])[:5]:
                evidence.append({
                    'type': 'video_frame',
                    'timestamp': frame.get('timestamp', 'N/A'),
                    'score': frame.get('violence_score', 0),
                    'description': frame.get('ml_detection', 'Violent frame'),
                })

        # Add violation events as evidence
        for v in result.get('violations', [])[:5]:
            evidence.append({
                'type': 'violation',
                'modality': v.get('modality', 'unknown'),
                'time_range': f"{v.get('start_time', 'N/A')} - {v.get('end_time', 'N/A')}",
                'reason': v.get('reason', 'N/A'),
                'confidence': v.get('confidence', 0),
            })

        return evidence


# Singleton accessor
_copilot = None


def get_ai_copilot() -> AICopilot:
    """Get or create the global AICopilot instance."""
    global _copilot
    if _copilot is None:
        _copilot = AICopilot()
    return _copilot
