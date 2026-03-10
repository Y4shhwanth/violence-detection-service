"""
Dataclass-based output schemas for structured API responses.
Provides validation and consistent output format.
"""
import time
from dataclasses import dataclass, field, asdict
from typing import Dict, Any, List, Optional


@dataclass
class ViolationEvent:
    """A single violation event."""
    modality: str = ''
    start_time: Optional[str] = None
    end_time: Optional[str] = None
    start_seconds: Optional[float] = None
    end_seconds: Optional[float] = None
    reason: str = ''
    confidence: float = 0.0
    sentence_index: Optional[int] = None
    sentence: Optional[str] = None

    def to_dict(self) -> dict:
        d = asdict(self)
        return {k: v for k, v in d.items() if v is not None}


@dataclass
class ModalityResult:
    """Result from a single modality analyzer."""
    modality: str = 'unknown'
    classification: str = 'Non-Violence'  # Violence or Non-Violence
    confidence: float = 0.0
    reasoning: str = ''
    violations: List[Dict] = field(default_factory=list)

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class FusedResult:
    """Fused prediction result."""
    classification: str = 'Non-Violence'
    confidence: float = 0.0
    decision_tier: str = 'Verified'
    decision_reason: str = ''
    fusion_method: str = 'weighted'
    calibrated_scores: Dict[str, float] = field(default_factory=dict)
    modalities_detected: int = 0

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class SeverityInfo:
    """Severity scoring information."""
    severity_score: float = 0.0
    severity_label: str = 'Unknown'

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class AnalysisOutput:
    """Complete analysis output schema."""
    success: bool = False
    job_id: Optional[str] = None
    final_decision: str = 'Verified'
    confidence: float = 0.0
    message: str = ''
    recommended_action: Optional[str] = None

    # Per-modality results
    video_prediction: Optional[Dict] = None
    audio_prediction: Optional[Dict] = None
    text_prediction: Optional[Dict] = None
    fused_prediction: Optional[Dict] = None

    # Enhanced data
    violations: List[Dict] = field(default_factory=list)
    violence_events: List[Dict] = field(default_factory=list)
    severity: Optional[Dict] = None
    modality_contributions: Optional[Dict] = None
    cross_modal_reasoning: Optional[Dict] = None

    # Risk scoring
    risk_score: Optional[Dict] = None

    # Policy & explanation
    structured_explanation: Optional[Dict] = None
    policy_matches: Optional[Dict] = None
    llm_explanation: Optional[Dict] = None
    false_positive_analysis: Optional[Dict] = None
    embedding_adjustment: Optional[Dict] = None

    # Meta
    processing_time_ms: Optional[int] = None

    def to_dict(self) -> dict:
        d = asdict(self)
        # Remove None values for cleaner output
        return {k: v for k, v in d.items() if v is not None}

    @classmethod
    def from_results(cls, results: Dict[str, Any]) -> 'AnalysisOutput':
        """Create AnalysisOutput from raw results dict."""
        return cls(
            success=results.get('success', False),
            job_id=results.get('job_id'),
            final_decision=results.get('final_decision', 'Verified'),
            confidence=results.get('confidence', 0),
            message=results.get('message', ''),
            recommended_action=results.get('recommended_action'),
            video_prediction=results.get('video_prediction'),
            audio_prediction=results.get('audio_prediction'),
            text_prediction=results.get('text_prediction'),
            fused_prediction=results.get('fused_prediction'),
            violations=results.get('violations', []),
            violence_events=results.get('violence_events', []),
            severity=results.get('severity'),
            modality_contributions=results.get('modality_contributions'),
            cross_modal_reasoning=results.get('cross_modal_reasoning'),
            risk_score=results.get('risk_score'),
            structured_explanation=results.get('structured_explanation'),
            policy_matches=results.get('policy_matches'),
            llm_explanation=results.get('llm_explanation'),
            false_positive_analysis=results.get('false_positive_analysis'),
            embedding_adjustment=results.get('embedding_adjustment'),
            processing_time_ms=results.get('processing_time_ms'),
        )
