"""
Evaluation service for computing precision, recall, F1, accuracy
from predictions + ground truth (feedback data).
"""
from typing import Dict, Any, List, Optional
from collections import Counter

from ..utils.logging import get_logger
from ..database.session import get_db_session
from ..database.models import FeedbackRecord, AnalysisResult

logger = get_logger(__name__)


class EvaluationService:
    """Computes evaluation metrics from feedback data."""

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def compute_metrics(self, days: int = 30) -> Dict[str, Any]:
        """Compute evaluation metrics from recent feedback."""
        try:
            with get_db_session() as session:
                feedbacks = (
                    session.query(FeedbackRecord)
                    .order_by(FeedbackRecord.created_at.desc())
                    .limit(1000)
                    .all()
                )

                if not feedbacks:
                    return {'error': 'No feedback data available', 'total_feedback': 0}

                # Build confusion matrix
                tp = 0  # True positive: predicted Violence, actually Violence (correct)
                fp = 0  # False positive: predicted Violence, actually Non-Violence
                tn = 0  # True negative: predicted Non-Violence, actually Non-Violence (correct)
                fn = 0  # False negative: predicted Non-Violence, actually Violence

                for fb in feedbacks:
                    is_violation = fb.original_decision in ('Violation', 'Review Required')
                    if fb.feedback_type == 'correct':
                        if is_violation:
                            tp += 1
                        else:
                            tn += 1
                    elif fb.feedback_type == 'false_positive':
                        fp += 1
                    elif fb.feedback_type == 'false_negative':
                        fn += 1

                total = tp + fp + tn + fn
                if total == 0:
                    return {'error': 'Insufficient data', 'total_feedback': len(feedbacks)}

                precision = tp / (tp + fp) if (tp + fp) > 0 else 0
                recall = tp / (tp + fn) if (tp + fn) > 0 else 0
                f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0
                accuracy = (tp + tn) / total

                return {
                    'total_feedback': len(feedbacks),
                    'precision': round(precision, 4),
                    'recall': round(recall, 4),
                    'f1_score': round(f1, 4),
                    'accuracy': round(accuracy, 4),
                    'confusion_matrix': {
                        'true_positive': tp,
                        'false_positive': fp,
                        'true_negative': tn,
                        'false_negative': fn,
                    },
                    'feedback_distribution': {
                        'correct': tp + tn,
                        'false_positive': fp,
                        'false_negative': fn,
                    },
                }

        except Exception as e:
            logger.error(f"Evaluation metrics computation failed: {e}")
            return {'error': str(e)}


_evaluation_service = None


def get_evaluation_service() -> EvaluationService:
    global _evaluation_service
    if _evaluation_service is None:
        _evaluation_service = EvaluationService()
    return _evaluation_service
