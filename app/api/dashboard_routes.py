"""Dashboard, feedback, and export endpoints."""
import uuid
import datetime
from flask import Blueprint, request, jsonify, send_file

from ..utils.logging import get_logger
from ..database.session import get_db_session
from ..database.models import FeedbackRecord, ModerationStats, AnalysisResult

logger = get_logger(__name__)

dashboard_bp = Blueprint('dashboard', __name__)


@dashboard_bp.route('/dashboard/stats')
def dashboard_stats():
    """Get aggregated moderation statistics."""
    days = int(request.args.get('days', 30))

    try:
        with get_db_session() as session:
            cutoff = (datetime.date.today() - datetime.timedelta(days=days)).isoformat()
            stats = (
                session.query(ModerationStats)
                .filter(ModerationStats.date >= cutoff)
                .order_by(ModerationStats.date.desc())
                .all()
            )

            daily = []
            totals = {
                'total_analyses': 0, 'violations': 0, 'reviews': 0,
                'verified': 0, 'false_positives': 0, 'false_negatives': 0,
            }

            for s in stats:
                daily.append({
                    'date': s.date,
                    'total_analyses': s.total_analyses,
                    'violations': s.violations,
                    'reviews': s.reviews,
                    'verified': s.verified,
                    'avg_confidence': round(s.avg_confidence, 1),
                    'avg_processing_time_ms': s.avg_processing_time_ms,
                })
                for k in totals:
                    totals[k] += getattr(s, k, 0)

            return jsonify({
                'success': True,
                'totals': totals,
                'daily': daily,
            })

    except Exception as e:
        logger.error(f"Dashboard stats failed: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@dashboard_bp.route('/feedback', methods=['POST'])
def submit_feedback():
    """Submit feedback on an analysis result."""
    data = request.get_json()
    if not data:
        return jsonify({'success': False, 'error': 'No data provided'}), 400

    job_id = data.get('job_id')
    feedback_type = data.get('feedback_type')

    if not job_id or not feedback_type:
        return jsonify({'success': False, 'error': 'job_id and feedback_type required'}), 400

    if feedback_type not in ('correct', 'false_positive', 'false_negative'):
        return jsonify({'success': False, 'error': 'Invalid feedback_type'}), 400

    try:
        with get_db_session() as session:
            # Look up original result
            original = session.query(AnalysisResult).filter_by(job_id=job_id).first()

            record = FeedbackRecord(
                id=str(uuid.uuid4()),
                job_id=job_id,
                feedback_type=feedback_type,
                comment=data.get('comment', ''),
                original_decision=original.final_decision if original else None,
                original_confidence=original.confidence if original else None,
                ground_truth_decision=data.get('ground_truth'),
            )
            session.add(record)

            # Update daily stats for FP/FN
            if feedback_type in ('false_positive', 'false_negative'):
                today = datetime.date.today().isoformat()
                stats = session.query(ModerationStats).filter_by(date=today).first()
                if stats:
                    if feedback_type == 'false_positive':
                        stats.false_positives += 1
                    else:
                        stats.false_negatives += 1

        return jsonify({'success': True, 'feedback_id': record.id})

    except Exception as e:
        logger.error(f"Feedback submission failed: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@dashboard_bp.route('/dashboard/evaluation')
def evaluation_metrics():
    """Get evaluation metrics from feedback data."""
    try:
        from ..services.evaluation import get_evaluation_service
        svc = get_evaluation_service()
        metrics = svc.compute_metrics()
        return jsonify({'success': True, **metrics})
    except Exception as e:
        logger.error(f"Evaluation metrics failed: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@dashboard_bp.route('/export/<job_id>')
def export_report(job_id):
    """Export analysis result as PDF report."""
    try:
        from ..services.report_generator import get_report_generator

        with get_db_session() as session:
            record = session.query(AnalysisResult).filter_by(job_id=job_id).first()
            if not record:
                return jsonify({'error': 'Job not found'}), 404

            generator = get_report_generator()
            pdf_path = generator.generate(record.result_json, job_id)

            return send_file(
                pdf_path,
                as_attachment=True,
                download_name=f'report_{job_id[:8]}.pdf',
                mimetype='application/pdf',
            )

    except ImportError:
        return jsonify({'error': 'PDF generation not available (install fpdf2)'}), 500
    except Exception as e:
        logger.error(f"Export failed: {e}")
        return jsonify({'error': str(e)}), 500
