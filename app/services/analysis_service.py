"""
Analysis service orchestrating the full pipeline for async jobs.
Reuses existing MultiModalFusion and reports progress at each stage.
"""
import os
import time
import uuid
from typing import Optional, Dict, Any

from ..utils.logging import get_logger
from ..database.session import get_db_session
from ..database.models import AnalysisResult, ModerationStats

logger = get_logger(__name__)

PIPELINE_STEPS = [
    (10, 'Extracting video frames'),
    (30, 'Analyzing video content'),
    (45, 'Analyzing audio content'),
    (60, 'Analyzing text content'),
    (75, 'Fusing modality results'),
    (85, 'Enhancing results'),
    (95, 'Generating report'),
    (100, 'Complete'),
]


class AnalysisService:
    """Orchestrates the full analysis pipeline for async jobs."""

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self._initialized = True

    def process_job(self, job) -> Dict[str, Any]:
        """Process a single analysis job. Called by JobQueue worker."""
        from .job_queue import get_job_queue
        from ..analysis import MultiModalFusion
        from ..api.validators import validate_text_input
        from ..config import get_config

        jq = get_job_queue()
        start_time = time.time()

        fusion = MultiModalFusion()
        config = get_config()
        results = {
            'success': False,
            'video_prediction': None,
            'audio_prediction': None,
            'text_prediction': None,
            'fused_prediction': None,
            'violations': [],
        }

        video_path = job.video_path
        text_input = job.text_input

        # Step 1-2: Video analysis
        if video_path and os.path.exists(video_path):
            jq.update_job(job.id, progress=10, current_step='Analyzing video content')
            results['video_prediction'] = fusion._safe_analyze_temporal(
                fusion.video_analyzer, video_path, 'video'
            )

            # Step 3: Audio analysis
            jq.update_job(job.id, progress=45, current_step='Analyzing audio content')
            results['audio_prediction'] = fusion._safe_analyze_temporal(
                fusion.audio_analyzer, video_path, 'audio'
            )

        # Step 4: Text analysis
        if text_input:
            jq.update_job(job.id, progress=60, current_step='Analyzing text content')
            text_input = validate_text_input(text_input)
            results['text_prediction'] = fusion._safe_analyze_temporal(
                fusion.text_analyzer, text_input, 'text'
            )

        # Step 5: Fusion
        jq.update_job(job.id, progress=75, current_step='Fusing modality results')
        predictions = [
            results['video_prediction'],
            results['audio_prediction'],
            results['text_prediction']
        ]
        valid_predictions = [p for p in predictions if p and p.get('class') != 'Error']
        if valid_predictions:
            results['fused_prediction'] = fusion._fuse_predictions(valid_predictions)

        # Merge violations
        all_violations = []
        for key in ['video_prediction', 'audio_prediction', 'text_prediction']:
            pred = results.get(key)
            if pred and 'violations' in pred:
                all_violations.extend(pred['violations'])
        all_violations.sort(key=lambda v: v.get('start_seconds', v.get('sentence_index', 0)))
        results['violations'] = all_violations

        # Step 6: Enhancement pipeline
        jq.update_job(job.id, progress=85, current_step='Enhancing results')
        try:
            results = fusion.enhance_results(
                results,
                text_input=text_input,
                audio_data=None,
                video_frames=None,
            )
        except Exception as e:
            logger.warning(f"Enhancement pipeline failed (non-fatal): {e}")

        # Build final response
        results['success'] = True
        fused = results.get('fused_prediction') or {}
        fused_class = fused.get('class', 'Non-Violence')
        confidence = fused.get('confidence', 0)

        decision_tier = fused.get('decision_tier', None)
        final_decision = decision_tier if decision_tier else (
            'Violation' if fused_class == 'Violence' else 'Verified'
        )

        results['final_decision'] = final_decision
        results['confidence'] = float(confidence)
        results['message'] = 'Analysis completed'

        processing_time_ms = int((time.time() - start_time) * 1000)
        results['processing_time_ms'] = processing_time_ms
        results['job_id'] = job.id

        # Step 7: Store in DB
        jq.update_job(job.id, progress=95, current_step='Storing results')
        try:
            self._store_result(job, results, processing_time_ms)
        except Exception as e:
            logger.warning(f"Failed to store result in DB: {e}")

        # Cleanup video file
        if video_path and os.path.exists(video_path):
            try:
                os.remove(video_path)
            except OSError:
                pass

        return results

    def _store_result(self, job, results: Dict[str, Any], processing_time_ms: int):
        """Store analysis result in database."""
        import datetime

        with get_db_session() as session:
            record = AnalysisResult(
                id=str(uuid.uuid4()),
                job_id=job.id,
                has_video=job.video_path is not None,
                has_text=job.text_input is not None,
                video_filename=os.path.basename(job.video_path) if job.video_path else None,
                text_length=len(job.text_input) if job.text_input else 0,
                final_decision=results.get('final_decision', 'Unknown'),
                confidence=results.get('confidence', 0),
                decision_tier=results.get('fused_prediction', {}).get('decision_tier'),
                video_confidence=(results.get('video_prediction') or {}).get('confidence'),
                audio_confidence=(results.get('audio_prediction') or {}).get('confidence'),
                text_confidence=(results.get('text_prediction') or {}).get('confidence'),
                severity_score=(results.get('severity') or {}).get('severity_score'),
                severity_label=(results.get('severity') or {}).get('severity_label'),
                result_json=results,
                processing_time_ms=processing_time_ms,
            )
            session.add(record)

            # Update daily stats
            today = datetime.date.today().isoformat()
            stats = session.query(ModerationStats).filter_by(date=today).first()
            if not stats:
                stats = ModerationStats(date=today)
                session.add(stats)

            stats.total_analyses += 1
            decision = results.get('final_decision', '')
            if decision == 'Violation':
                stats.violations += 1
            elif decision == 'Review Required':
                stats.reviews += 1
            else:
                stats.verified += 1

            # Running average
            n = stats.total_analyses
            stats.avg_confidence = (
                (stats.avg_confidence * (n - 1) + results.get('confidence', 0)) / n
            )
            stats.avg_processing_time_ms = (
                (stats.avg_processing_time_ms * (n - 1) + processing_time_ms) / n
            )


_analysis_service = None


def get_analysis_service() -> AnalysisService:
    """Get global AnalysisService instance."""
    global _analysis_service
    if _analysis_service is None:
        _analysis_service = AnalysisService()
    return _analysis_service
