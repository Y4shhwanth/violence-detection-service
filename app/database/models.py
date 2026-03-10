"""SQLAlchemy ORM models for Violence Detection System."""
import datetime
from sqlalchemy import Column, String, Float, Integer, Text, DateTime, Boolean, JSON
from sqlalchemy.orm import declarative_base

Base = declarative_base()


class AnalysisResult(Base):
    """Stores completed analysis results."""
    __tablename__ = 'analysis_results'

    id = Column(String(36), primary_key=True)
    job_id = Column(String(36), index=True, nullable=False)
    created_at = Column(DateTime, default=datetime.datetime.utcnow, index=True)

    # Input metadata
    has_video = Column(Boolean, default=False)
    has_text = Column(Boolean, default=False)
    video_filename = Column(String(255), nullable=True)
    text_length = Column(Integer, default=0)

    # Decision
    final_decision = Column(String(50), nullable=False)
    confidence = Column(Float, default=0.0)
    decision_tier = Column(String(50), nullable=True)

    # Per-modality scores
    video_confidence = Column(Float, nullable=True)
    audio_confidence = Column(Float, nullable=True)
    text_confidence = Column(Float, nullable=True)

    # Severity
    severity_score = Column(Float, nullable=True)
    severity_label = Column(String(50), nullable=True)

    # Full result JSON
    result_json = Column(JSON, nullable=True)

    # Processing time
    processing_time_ms = Column(Integer, nullable=True)


class FeedbackRecord(Base):
    """Stores user feedback on analysis results."""
    __tablename__ = 'feedback_records'

    id = Column(String(36), primary_key=True)
    job_id = Column(String(36), index=True, nullable=False)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    # Feedback type: correct, false_positive, false_negative
    feedback_type = Column(String(50), nullable=False)
    comment = Column(Text, nullable=True)

    # Ground truth (what the user says the correct answer is)
    ground_truth_decision = Column(String(50), nullable=True)
    original_decision = Column(String(50), nullable=True)
    original_confidence = Column(Float, nullable=True)


class ModerationStats(Base):
    """Aggregated moderation statistics."""
    __tablename__ = 'moderation_stats'

    id = Column(Integer, primary_key=True, autoincrement=True)
    date = Column(String(10), index=True, nullable=False)  # YYYY-MM-DD

    total_analyses = Column(Integer, default=0)
    violations = Column(Integer, default=0)
    reviews = Column(Integer, default=0)
    verified = Column(Integer, default=0)

    avg_confidence = Column(Float, default=0.0)
    avg_processing_time_ms = Column(Integer, default=0)

    false_positives = Column(Integer, default=0)
    false_negatives = Column(Integer, default=0)
