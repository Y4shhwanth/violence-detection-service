"""
Real-Time Violence Detection (Live Monitoring Mode).

Captures frames from webcam or RTSP/CCTV streams via OpenCV,
processes every Nth frame through the existing video analysis pipeline,
and emits results via Flask-SocketIO WebSocket events.

WebSocket events emitted:
    - 'detection_result': Per-frame violence detection result
    - 'live_status':      Stream status updates (started, stopped, error)
    - 'live_alert':       High-confidence violence alert notification

Configuration via LiveDetectionConfig in app/config.py.
"""
import time
import threading
import uuid
from typing import Dict, Any, Optional

import cv2
import numpy as np

from ..utils.logging import get_logger
from ..config import get_config

logger = get_logger(__name__)


class LiveDetector:
    """
    Real-time violence detector for webcam/CCTV streams.

    Captures frames from an OpenCV VideoCapture source, runs violence
    analysis on every Nth frame, and emits results via a callback
    (typically a SocketIO emit function).
    """

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

        config = get_config()
        live_cfg = getattr(config, 'live_detection', None)

        # Configuration with sensible defaults
        self.frame_skip = getattr(live_cfg, 'frame_skip', 5) if live_cfg else 5
        self.alert_threshold = getattr(live_cfg, 'alert_threshold', 70.0) if live_cfg else 70.0
        self.max_fps = getattr(live_cfg, 'max_fps', 30) if live_cfg else 30
        self.frame_width = getattr(live_cfg, 'frame_width', 640) if live_cfg else 640
        self.frame_height = getattr(live_cfg, 'frame_height', 480) if live_cfg else 480

        # State tracking
        self._active_sessions: Dict[str, dict] = {}
        self._lock = threading.Lock()

        # Lazy-loaded analyzer
        self._video_analyzer = None
        self._prev_frame = None

        logger.info(
            f"LiveDetector initialized: skip={self.frame_skip}, "
            f"threshold={self.alert_threshold}, max_fps={self.max_fps}"
        )

    @property
    def video_analyzer(self):
        """Lazily load the video analyzer to avoid heavy imports at startup."""
        if self._video_analyzer is None:
            from .video_analyzer import VideoAnalyzer
            self._video_analyzer = VideoAnalyzer()
        return self._video_analyzer

    def start_stream(
        self,
        source: Any = 0,
        emit_callback=None,
        session_id: Optional[str] = None,
    ) -> str:
        """
        Start a live detection stream in a background thread.

        Args:
            source:        OpenCV video source (0 for webcam, or RTSP URL string).
            emit_callback: Function to emit results (e.g., socketio.emit).
            session_id:    Optional session identifier. Auto-generated if not provided.

        Returns:
            session_id for the started stream.
        """
        if session_id is None:
            session_id = str(uuid.uuid4())[:8]

        with self._lock:
            if session_id in self._active_sessions:
                logger.warning(f"Session {session_id} already active, stopping first")
                self._stop_session(session_id)

            self._active_sessions[session_id] = {
                'active': True,
                'source': source,
                'frame_count': 0,
                'detection_count': 0,
                'alerts': 0,
                'start_time': time.time(),
            }

        # Start capture thread
        thread = threading.Thread(
            target=self._capture_loop,
            args=(source, emit_callback, session_id),
            daemon=True,
            name=f"live-detector-{session_id}",
        )
        thread.start()

        logger.info(f"Live detection started: session={session_id}, source={source}")

        if emit_callback:
            emit_callback('live_status', {
                'session_id': session_id,
                'status': 'started',
                'source': str(source),
            })

        return session_id

    def stop_stream(self, session_id: str) -> bool:
        """Stop an active live detection stream."""
        with self._lock:
            return self._stop_session(session_id)

    def _stop_session(self, session_id: str) -> bool:
        """Internal: mark a session as inactive (caller must hold lock)."""
        session = self._active_sessions.get(session_id)
        if session:
            session['active'] = False
            logger.info(
                f"Stopping session {session_id}: "
                f"frames={session['frame_count']}, "
                f"detections={session['detection_count']}, "
                f"alerts={session['alerts']}"
            )
            return True
        return False

    def get_active_sessions(self) -> Dict[str, dict]:
        """Return metadata for all active sessions."""
        with self._lock:
            return {
                sid: {
                    'source': str(s['source']),
                    'frame_count': s['frame_count'],
                    'detection_count': s['detection_count'],
                    'alerts': s['alerts'],
                    'uptime_seconds': int(time.time() - s['start_time']),
                }
                for sid, s in self._active_sessions.items()
                if s['active']
            }

    def _capture_loop(
        self, source: Any, emit_callback, session_id: str
    ) -> None:
        """
        Main capture loop: read frames from OpenCV, analyze every Nth frame,
        and emit results via the callback.
        """
        cap = None
        try:
            cap = cv2.VideoCapture(source)
            if not cap.isOpened():
                logger.error(f"Failed to open video source: {source}")
                if emit_callback:
                    emit_callback('live_status', {
                        'session_id': session_id,
                        'status': 'error',
                        'error': f'Failed to open source: {source}',
                    })
                return

            # Set resolution
            cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.frame_width)
            cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.frame_height)

            frame_interval = 1.0 / self.max_fps
            frame_count = 0
            prev_frame = None

            while True:
                # Check if session is still active
                with self._lock:
                    session = self._active_sessions.get(session_id)
                    if not session or not session['active']:
                        break

                loop_start = time.time()

                ret, frame = cap.read()
                if not ret:
                    logger.warning(f"Frame read failed for session {session_id}")
                    # Try to reconnect for RTSP streams
                    if isinstance(source, str):
                        time.sleep(1)
                        cap.release()
                        cap = cv2.VideoCapture(source)
                        continue
                    break

                frame_count += 1
                with self._lock:
                    if session_id in self._active_sessions:
                        self._active_sessions[session_id]['frame_count'] = frame_count

                # Only analyze every Nth frame
                if frame_count % self.frame_skip == 0:
                    result = self._analyze_frame(frame, prev_frame)

                    with self._lock:
                        if session_id in self._active_sessions:
                            self._active_sessions[session_id]['detection_count'] += 1

                    # Emit detection result
                    if emit_callback:
                        detection_payload = {
                            'session_id': session_id,
                            'frame_number': frame_count,
                            'timestamp': time.strftime('%H:%M:%S'),
                            'violence_detected': result.get('is_violent', False),
                            'confidence': round(result.get('confidence', 0), 1),
                            'violence_score': round(result.get('violence_score', 0), 1),
                            'details': result.get('details', {}),
                        }
                        emit_callback('detection_result', detection_payload)

                        # High-confidence alert
                        if result.get('confidence', 0) >= self.alert_threshold:
                            with self._lock:
                                if session_id in self._active_sessions:
                                    self._active_sessions[session_id]['alerts'] += 1

                            emit_callback('live_alert', {
                                'session_id': session_id,
                                'alert_type': 'violence_detected',
                                'confidence': round(result['confidence'], 1),
                                'timestamp': time.strftime('%H:%M:%S'),
                                'frame_number': frame_count,
                            })

                prev_frame = frame.copy()

                # Frame rate limiting
                elapsed = time.time() - loop_start
                sleep_time = frame_interval - elapsed
                if sleep_time > 0:
                    time.sleep(sleep_time)

        except Exception as e:
            logger.error(f"Live detection error in session {session_id}: {e}")
            if emit_callback:
                emit_callback('live_status', {
                    'session_id': session_id,
                    'status': 'error',
                    'error': str(e),
                })
        finally:
            if cap:
                cap.release()

            # Clean up session
            with self._lock:
                if session_id in self._active_sessions:
                    self._active_sessions[session_id]['active'] = False

            if emit_callback:
                emit_callback('live_status', {
                    'session_id': session_id,
                    'status': 'stopped',
                })

            logger.info(f"Live detection session {session_id} ended")

    def _analyze_frame(
        self, frame: np.ndarray, prev_frame: Optional[np.ndarray] = None
    ) -> Dict[str, Any]:
        """
        Analyze a single frame for violence using the video analyzer pipeline.

        Reuses the existing VideoAnalyzer._analyze_frame() for heuristics
        and _analyze_frame_ml() for ML classification.
        """
        try:
            analyzer = self.video_analyzer

            # Run heuristic analysis
            heuristic_result = {}
            if hasattr(analyzer, '_analyze_frame'):
                heuristic_result = analyzer._analyze_frame(frame, prev_frame)

            # Run ML classification
            ml_result = {}
            if hasattr(analyzer, '_analyze_frame_ml'):
                ml_result = analyzer._analyze_frame_ml(frame)

            # Combine scores
            heuristic_score = heuristic_result.get('violence_score', 0)
            ml_score = ml_result.get('ml_score', 0)

            # Weighted combination (60% ML + 40% heuristic)
            combined_score = 0.6 * ml_score + 0.4 * heuristic_score
            confidence = min(100.0, combined_score)

            # Determine if violent
            is_violent = confidence >= 50.0

            return {
                'is_violent': is_violent,
                'confidence': confidence,
                'violence_score': combined_score,
                'heuristic_score': heuristic_score,
                'ml_score': ml_score,
                'details': {
                    'heuristic': {k: v for k, v in heuristic_result.items()
                                  if k != 'violence_score'},
                    'ml': {k: v for k, v in ml_result.items()
                           if k != 'ml_score'},
                },
            }

        except Exception as e:
            logger.error(f"Frame analysis failed: {e}")
            return {
                'is_violent': False,
                'confidence': 0,
                'violence_score': 0,
                'error': str(e),
            }

    def analyze_single_frame(self, frame: np.ndarray) -> Dict[str, Any]:
        """
        Public method to analyze a single frame without streaming.
        Useful for one-off frame analysis via REST API.
        """
        return self._analyze_frame(frame, self._prev_frame)


# Singleton accessor
_live_detector = None


def get_live_detector() -> LiveDetector:
    """Get or create the global LiveDetector instance."""
    global _live_detector
    if _live_detector is None:
        _live_detector = LiveDetector()
    return _live_detector
