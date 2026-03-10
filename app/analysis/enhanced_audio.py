"""
Enhanced Audio Analyzer with ensemble: AST + wav2vec2 emotion model.
Sliding window (3s, 1s overlap) for temporal analysis.
"""
import numpy as np
from typing import Dict, Any, List, Optional

from .base import BaseAnalyzer
from ..config import get_config
from ..models.loader import get_model_manager
from ..utils.logging import get_logger

logger = get_logger(__name__)

# Emotion labels that correlate with violence
VIOLENCE_EMOTIONS = {
    'angry': 0.8, 'anger': 0.8,
    'fear': 0.6, 'fearful': 0.6,
    'disgust': 0.4, 'disgusted': 0.4,
    'sad': 0.2, 'sadness': 0.2,
}


class EnhancedAudioAnalyzer(BaseAnalyzer):
    """Enhanced audio analyzer with AST + emotion ensemble."""

    def __init__(self):
        super().__init__()
        self._modality = 'audio'
        self.config = get_config().audio
        self.model_manager = get_model_manager()

    def analyze(self, video_path: str) -> Dict[str, Any]:
        """Analyze audio with ensemble approach."""
        from .audio_analyzer import AudioAnalyzer

        # Get base AST result
        base_analyzer = AudioAnalyzer()
        ast_result = base_analyzer.analyze(video_path)

        # Get emotion result
        emotion_result = self._analyze_emotion(video_path)

        # Combine scores
        ast_score = ast_result.get('violence_score', 0) if ast_result.get('class') == 'Violence' else 0
        emotion_score = emotion_result.get('violence_score', 0)

        # Weighted ensemble: 0.6 * AST + 0.4 * emotion
        combined_score = 0.6 * ast_score + 0.4 * emotion_score

        is_violent = combined_score > self.config.violence_threshold or ast_result.get('class') == 'Violence'

        reasoning_parts = []
        if ast_result.get('reasoning'):
            reasoning_parts.append(f"AST: {ast_result['reasoning']}")
        if emotion_result.get('dominant_emotion'):
            reasoning_parts.append(
                f"Emotion: {emotion_result['dominant_emotion']} ({emotion_result.get('emotion_confidence', 0):.0f}%)"
            )

        result = self._create_result(
            is_violent=is_violent,
            confidence=min(95, max(60, combined_score + 20)) if is_violent else max(60, 100 - combined_score),
            reasoning=' | '.join(reasoning_parts) if reasoning_parts else 'No significant audio indicators',
            detected_sounds=ast_result.get('detected_sounds', []),
            violence_score=float(combined_score),
            emotion_analysis=emotion_result,
            ensemble_method='ast_emotion',
        )

        # Carry over violations
        result['violations'] = ast_result.get('violations', [])
        return result

    def _analyze_emotion(self, video_path: str) -> Dict[str, Any]:
        """Analyze audio for emotional content using wav2vec2."""
        try:
            emotion_classifier = self.model_manager.emotion_classifier
            if emotion_classifier is None:
                return {'violence_score': 0, 'dominant_emotion': None}

            import librosa
            import torch
            from .audio_analyzer import AudioAnalyzer

            base = AudioAnalyzer()
            with base._extract_audio_ffmpeg(video_path) as audio_path:
                if audio_path is None:
                    return {'violence_score': 0, 'dominant_emotion': None}

                audio, sr = librosa.load(audio_path, sr=16000, duration=30)

            # Sliding window analysis (3s windows, 1s overlap)
            window_size = 3 * sr
            hop_size = 1 * sr
            emotion_scores = []

            for start in range(0, len(audio) - window_size + 1, hop_size):
                segment = audio[start:start + window_size]
                with torch.no_grad():
                    preds = emotion_classifier(segment, sampling_rate=sr, top_k=5)

                for pred in preds:
                    label = pred['label'].lower()
                    score = pred['score'] * 100
                    for emotion_kw, weight in VIOLENCE_EMOTIONS.items():
                        if emotion_kw in label:
                            emotion_scores.append(score * weight)
                            break

                if len(emotion_scores) > 30:  # Cap at 30 windows
                    break

            if not emotion_scores:
                return {'violence_score': 0, 'dominant_emotion': None}

            # Use top-3 average for robustness
            top_scores = sorted(emotion_scores, reverse=True)[:3]
            avg_violence = sum(top_scores) / len(top_scores)

            # Get dominant emotion from last prediction
            dominant_emotion = preds[0]['label'] if preds else None
            emotion_confidence = preds[0]['score'] * 100 if preds else 0

            return {
                'violence_score': avg_violence,
                'dominant_emotion': dominant_emotion,
                'emotion_confidence': emotion_confidence,
                'windows_analyzed': len(emotion_scores),
            }

        except Exception as e:
            logger.warning(f"Emotion analysis failed: {e}")
            return {'violence_score': 0, 'dominant_emotion': None, 'error': str(e)}
