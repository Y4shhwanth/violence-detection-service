"""
LLM-Based Explainability Layer for Violence Detection System.

Generates human-readable safety reports from structured analyzer outputs
by building a deterministic prompt and calling an LLM (Claude API placeholder).

Design principles:
    - Prompt is deterministic and evidence-only (no hallucination)
    - Structured JSON output with risk levels and recommended actions
    - Graceful fallback if the LLM call fails
    - Thread-safe, stateless
"""
import json
import re
import time
from typing import Dict, Any, Optional, List

from .logging import get_logger

logger = get_logger(__name__)


# ---------------------------------------------------------------------------
# Risk level mapping — ordered descending by threshold so first match wins
# ---------------------------------------------------------------------------
RISK_LEVELS: List[tuple] = [
    ('Critical', 80, 'Immediate removal. Escalate to Trust & Safety. Notify law enforcement if direct threat identified.'),
    ('High',     60, 'Remove content and flag for human review. Issue account warning.'),
    ('Medium',   40, 'Apply content warning label. Queue for human review within 24 hours.'),
    ('Low',       0, 'Monitor. No immediate action required. Log for trend analysis.'),
]

# Valid risk level names for validation
VALID_RISK_LEVELS = frozenset(level for level, _, _ in RISK_LEVELS)


def _score_to_risk(score: int) -> tuple:
    """Map severity score to (risk_level, recommended_action)."""
    for level, threshold, action in RISK_LEVELS:
        if score >= threshold:
            return level, action
    return 'Low', RISK_LEVELS[-1][2]


class LLMExplainer:
    """
    Generates structured safety reports from violence detection outputs.
    Uses an LLM when available, falls back to deterministic generation.
    """

    def __init__(self):
        self.logger = get_logger(__name__)

    @staticmethod
    def call_llm(prompt: str, max_tokens: int = 1024) -> Optional[str]:
        """
        Placeholder for LLM API call.

        Replace this body with actual Claude API integration:

            import anthropic
            client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
            message = client.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=max_tokens,
                messages=[{"role": "user", "content": prompt}],
            )
            return message.content[0].text

        Returns:
            LLM response string, or None if unavailable.
        """
        # Return None to trigger the deterministic fallback.
        # When you wire up a real LLM, this method returns the model's text.
        return None

    def generate_report(
        self,
        video_result: Optional[Dict[str, Any]] = None,
        audio_result: Optional[Dict[str, Any]] = None,
        text_result: Optional[Dict[str, Any]] = None,
        fused_result: Optional[Dict[str, Any]] = None,
        severity: Optional[Dict[str, Any]] = None,
        policy_matches: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Generate a structured safety report.

        Returns:
            {
                "summary": str,
                "risk_level": "Low" | "Medium" | "High" | "Critical",
                "recommended_action": str,
                "detailed_explanation": str,
                "confidence_breakdown": {
                    "video": {"class": ..., "confidence": ...},
                    "audio": {"class": ..., "confidence": ...},
                    "text":  {"class": ..., "confidence": ...},
                    "fused": {"class": ..., "confidence": ...},
                },
                "generation_method": "llm" | "deterministic",
            }
        """
        start = time.time()

        # Try LLM-based generation first
        try:
            prompt = self._build_prompt(
                video_result, audio_result, text_result,
                fused_result, severity, policy_matches,
            )
            llm_response = self.call_llm(prompt)

            if llm_response:
                report = self._parse_llm_response(llm_response)
                if report:
                    report['generation_method'] = 'llm'
                    report['latency_ms'] = round((time.time() - start) * 1000, 2)
                    return report
        except Exception as e:
            self.logger.warning(f"LLM generation failed, using fallback: {e}")

        # Deterministic fallback
        report = self._generate_deterministic(
            video_result, audio_result, text_result,
            fused_result, severity, policy_matches,
        )
        report['generation_method'] = 'deterministic'
        report['latency_ms'] = round((time.time() - start) * 1000, 2)
        return report

    # ------------------------------------------------------------------
    # Prompt builder
    # ------------------------------------------------------------------
    def _build_prompt(
        self,
        video_result: Optional[Dict[str, Any]],
        audio_result: Optional[Dict[str, Any]],
        text_result: Optional[Dict[str, Any]],
        fused_result: Optional[Dict[str, Any]],
        severity: Optional[Dict[str, Any]],
        policy_matches: Optional[Dict[str, Any]],
    ) -> str:
        """Build a structured, deterministic prompt for the LLM."""
        sections = []

        sections.append(
            "You are a content safety analyst. Based ONLY on the evidence provided below, "
            "generate a structured safety report. Do NOT infer, assume, or hallucinate "
            "any details not present in the evidence. Respond with valid JSON only."
        )

        sections.append("\n--- EVIDENCE ---\n")

        # Video evidence
        if video_result and video_result.get('class') != 'Error':
            sections.append("[VIDEO ANALYSIS]")
            sections.append(f"  Classification: {video_result.get('class')}")
            sections.append(f"  Confidence: {video_result.get('confidence', 0):.1f}%")
            sections.append(f"  Reasoning: {video_result.get('reasoning', 'N/A')}")
            violent_frames = video_result.get('violent_frames', [])
            if violent_frames:
                sections.append(f"  Violent frames: {len(violent_frames)}")
                for vf in violent_frames[:3]:
                    sections.append(
                        f"    - [{vf.get('timestamp', '?')}] Score={vf.get('score', 0)}, "
                        f"Indicators: {', '.join(vf.get('indicators', []))}"
                    )

        # Audio evidence
        if audio_result and audio_result.get('class') != 'Error':
            sections.append("\n[AUDIO ANALYSIS]")
            sections.append(f"  Classification: {audio_result.get('class')}")
            sections.append(f"  Confidence: {audio_result.get('confidence', 0):.1f}%")
            sections.append(f"  Reasoning: {audio_result.get('reasoning', 'N/A')}")
            sounds = audio_result.get('detected_sounds', [])
            if sounds:
                sections.append(f"  Detected sounds: {', '.join(sounds)}")

        # Text evidence
        if text_result and text_result.get('class') != 'Error':
            sections.append("\n[TEXT ANALYSIS]")
            sections.append(f"  Classification: {text_result.get('class')}")
            sections.append(f"  Confidence: {text_result.get('confidence', 0):.1f}%")
            sections.append(f"  Reasoning: {text_result.get('reasoning', 'N/A')}")
            keywords = text_result.get('keywords_found', [])
            if keywords:
                sections.append(f"  Keywords found: {', '.join(keywords[:10])}")

        # Fused result
        if fused_result:
            sections.append("\n[FUSED PREDICTION]")
            sections.append(f"  Classification: {fused_result.get('class')}")
            sections.append(f"  Confidence: {fused_result.get('confidence', 0):.1f}%")
            sections.append(f"  Modalities detecting violence: {fused_result.get('modalities_detected', 0)}/{fused_result.get('total_modalities', 0)}")

        # Severity
        if severity:
            sections.append("\n[SEVERITY]")
            sections.append(f"  Score: {severity.get('severity_score', 0)}/100")
            sections.append(f"  Label: {severity.get('severity_label', 'N/A')}")

        # Policy matches
        if policy_matches and policy_matches.get('matched_policies'):
            sections.append("\n[POLICY VIOLATIONS]")
            for pm in policy_matches['matched_policies'][:3]:
                sections.append(f"  - {pm['title']} / {pm['section']}")

        sections.append("\n--- OUTPUT FORMAT ---\n")
        sections.append(
            'Respond with ONLY this JSON structure:\n'
            '{\n'
            '  "summary": "<1-2 sentence safety summary>",\n'
            '  "risk_level": "Low|Medium|High|Critical",\n'
            '  "recommended_action": "<specific action to take>",\n'
            '  "detailed_explanation": "<paragraph explaining the findings>",\n'
            '  "confidence_breakdown": {\n'
            '    "video": {"class": "...", "confidence": 0},\n'
            '    "audio": {"class": "...", "confidence": 0},\n'
            '    "text": {"class": "...", "confidence": 0},\n'
            '    "fused": {"class": "...", "confidence": 0}\n'
            '  }\n'
            '}'
        )

        return '\n'.join(sections)

    # ------------------------------------------------------------------
    # LLM response parser
    # ------------------------------------------------------------------
    def _parse_llm_response(self, response: str) -> Optional[Dict[str, Any]]:
        """Parse and validate LLM JSON response."""
        try:
            response = response.strip()

            # Robust JSON extraction: find the outermost {...} block
            # Handles markdown fences, preamble text, etc.
            match = re.search(r'\{.*\}', response, re.DOTALL)
            if match:
                response = match.group(0)
            else:
                self.logger.warning("No JSON object found in LLM response")
                return None

            data = json.loads(response)

            # Validate required keys
            required = {'summary', 'risk_level', 'recommended_action', 'detailed_explanation'}
            if not required.issubset(data.keys()):
                self.logger.warning(f"LLM response missing keys: {required - data.keys()}")
                return None

            # Validate risk_level
            if data['risk_level'] not in VALID_RISK_LEVELS:
                data['risk_level'] = 'Medium'  # safe default

            return data

        except (json.JSONDecodeError, KeyError, TypeError) as e:
            self.logger.warning(f"Failed to parse LLM response: {e}")
            return None

    # ------------------------------------------------------------------
    # Deterministic fallback
    # ------------------------------------------------------------------
    def _generate_deterministic(
        self,
        video_result: Optional[Dict[str, Any]],
        audio_result: Optional[Dict[str, Any]],
        text_result: Optional[Dict[str, Any]],
        fused_result: Optional[Dict[str, Any]],
        severity: Optional[Dict[str, Any]],
        policy_matches: Optional[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """Generate a deterministic report without an LLM using specific evidence."""
        is_violent = fused_result and fused_result.get('class') == 'Violence'
        severity_score = severity.get('severity_score', 0) if severity else 0
        severity_label = severity.get('severity_label', 'Mild') if severity else 'Mild'

        # Determine risk level from severity score (uses ordered list)
        risk_level, recommended_action = _score_to_risk(severity_score)

        # Build summary with specific evidence
        summary_parts = []
        if is_violent:
            modalities_violent = fused_result.get('modalities_detected', 0) if fused_result else 0
            total = fused_result.get('total_modalities', 0) if fused_result else 0
            summary_parts.append(
                f"Violence detected by {modalities_violent}/{total} analysis modalities."
            )
            summary_parts.append(f"Severity: {severity_label} ({severity_score}/100).")

            # Add specific evidence to summary
            if text_result and text_result.get('keywords_found'):
                keywords = [k.split(' (')[0] for k in text_result['keywords_found'][:3]]
                summary_parts.append(f"Keywords: {', '.join(keywords)}.")
            if audio_result and audio_result.get('detected_sounds'):
                summary_parts.append(f"Sounds: {', '.join(audio_result['detected_sounds'][:2])}.")
            if video_result and video_result.get('violent_frames'):
                n_frames = len(video_result['violent_frames'])
                summary_parts.append(f"{n_frames} violent frame(s) detected.")
        else:
            summary_parts.append("No significant violence indicators detected across analyzed modalities.")

        # Build detailed explanation with specific evidence
        explanation_parts = []

        if video_result and video_result.get('class') != 'Error':
            v_class = video_result.get('class')
            v_conf = video_result.get('confidence', 0)
            v_detail = f"Video analysis: {v_class} ({v_conf:.1f}% confidence)."
            # Add frame timestamps
            violent_frames = video_result.get('violent_frames', [])
            if violent_frames:
                timestamps = [f['timestamp'] for f in violent_frames[:3]]
                v_detail += f" Flagged at timestamps: {', '.join(timestamps)}."
            explanation_parts.append(v_detail)

        if audio_result and audio_result.get('class') != 'Error':
            a_class = audio_result.get('class')
            a_conf = audio_result.get('confidence', 0)
            a_detail = f"Audio analysis: {a_class} ({a_conf:.1f}% confidence)."
            sounds = audio_result.get('detected_sounds', [])
            if sounds:
                a_detail += f" Detected: {', '.join(sounds[:3])}."
            explanation_parts.append(a_detail)

        if text_result and text_result.get('class') != 'Error':
            t_class = text_result.get('class')
            t_conf = text_result.get('confidence', 0)
            t_detail = f"Text analysis: {t_class} ({t_conf:.1f}% confidence)."
            keywords = text_result.get('keywords_found', [])
            if keywords:
                t_detail += f" Keywords: {', '.join(keywords[:5])}."
            explanation_parts.append(t_detail)

        if severity:
            explanation_parts.append(
                f"Severity score: {severity_score}/100 ({severity_label})."
            )

        if policy_matches and policy_matches.get('matched_policies'):
            policies = policy_matches['matched_policies']
            policy_names = [p.get('title', 'Unknown') for p in policies[:3]]
            explanation_parts.append(
                f"Policy violations: {', '.join(policy_names)}."
            )

        # Generate compliance suggestion from violations
        compliance_suggestion = "No action required."
        if is_violent:
            compliance_suggestion = recommended_action

        # Build confidence breakdown
        confidence_breakdown = {}
        for name, result in [('video', video_result), ('audio', audio_result), ('text', text_result)]:
            if result and result.get('class') != 'Error':
                confidence_breakdown[name] = {
                    'class': result.get('class'),
                    'confidence': round(float(result.get('confidence', 0)), 2),
                }
            else:
                confidence_breakdown[name] = {
                    'class': 'N/A',
                    'confidence': 0,
                }

        if fused_result:
            confidence_breakdown['fused'] = {
                'class': fused_result.get('class'),
                'confidence': round(float(fused_result.get('confidence', 0)), 2),
            }

        return {
            'summary': ' '.join(summary_parts),
            'risk_level': risk_level,
            'recommended_action': recommended_action,
            'compliance_suggestion': compliance_suggestion,
            'detailed_explanation': ' '.join(explanation_parts) if explanation_parts else 'No analysis data available.',
            'confidence_breakdown': confidence_breakdown,
        }


# ---------------------------------------------------------------------------
# Module-level singleton
# ---------------------------------------------------------------------------
_llm_explainer: Optional[LLMExplainer] = None


def get_llm_explainer() -> LLMExplainer:
    """Get or create global LLMExplainer instance."""
    global _llm_explainer
    if _llm_explainer is None:
        _llm_explainer = LLMExplainer()
    return _llm_explainer
