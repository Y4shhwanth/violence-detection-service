"""
Learned fusion model for multi-modal violence detection.
Uses MLP/Logistic Regression to intelligently combine modality scores.
"""
import numpy as np
from typing import Dict, Any, Optional, List, Tuple
import pickle
import os
from pathlib import Path

from sklearn.neural_network import MLPClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler
import joblib

from ..utils.logging import get_logger

logger = get_logger(__name__)


class LearnedFusionModel:
    """
    Learned fusion model that combines multi-modal scores intelligently.

    Input features: [video_score, audio_score, text_score, object_score,
                     emotion_score, temporal_consistency, cross_modal_agreement]
    Output: Violence probability (0-1)
    """

    def __init__(self, model_type: str = 'mlp'):
        """
        Initialize fusion model.

        Args:
            model_type: 'mlp' or 'logistic'
        """
        self.model_type = model_type
        self.model = None
        self.scaler = StandardScaler()
        self.is_trained = False

        # Feature names for transparency
        self.feature_names = [
            'video_score',
            'audio_score',
            'text_score',
            'object_detection_score',
            'emotion_score',
            'temporal_consistency',
            'cross_modal_agreement',
            'video_confidence',
            'audio_confidence',
            'text_confidence'
        ]

        # Try to load pre-trained model
        self._load_pretrained()

    def _load_pretrained(self):
        """Load pre-trained model if available."""
        model_path = Path(__file__).parent / 'pretrained_fusion.pkl'
        scaler_path = Path(__file__).parent / 'pretrained_scaler.pkl'

        if model_path.exists() and scaler_path.exists():
            try:
                self.model = joblib.load(model_path)
                self.scaler = joblib.load(scaler_path)
                self.is_trained = True
                logger.info(f"Loaded pre-trained fusion model from {model_path}")
            except Exception as e:
                logger.warning(f"Failed to load pre-trained model: {e}")
                self._initialize_default_model()
        else:
            self._initialize_default_model()

    def _initialize_default_model(self):
        """Initialize model with default parameters."""
        if self.model_type == 'mlp':
            self.model = MLPClassifier(
                hidden_layer_sizes=(64, 32, 16),
                activation='relu',
                solver='adam',
                max_iter=1000,
                random_state=42,
                early_stopping=True
            )
        else:
            self.model = LogisticRegression(
                max_iter=1000,
                random_state=42
            )

        logger.info(f"Initialized default {self.model_type} fusion model")

    def extract_features(
        self,
        video: Optional[Dict[str, Any]],
        audio: Optional[Dict[str, Any]],
        text: Optional[Dict[str, Any]]
    ) -> np.ndarray:
        """
        Extract feature vector from predictions.

        Returns:
            Feature vector of shape (10,)
        """
        features = []

        # Video features
        if video and video.get('class') != 'Error':
            features.append(video.get('weighted_score', 0) / 100)
            video_conf = video.get('confidence', 0) / 100
        else:
            features.append(0)
            video_conf = 0

        # Audio features
        if audio and audio.get('class') != 'Error':
            audio_score = audio.get('violence_score', 0) / 100
            features.append(audio_score)
            audio_conf = audio.get('confidence', 0) / 100
        else:
            features.append(0)
            audio_conf = 0

        # Text features
        if text and text.get('class') != 'Error':
            text_score = text.get('ml_score', 0) / 100
            features.append(text_score)
            text_conf = text.get('confidence', 0) / 100
        else:
            features.append(0)
            text_conf = 0

        # Object detection score (from video)
        object_score = 0
        if video and 'violent_frames' in video:
            for frame in video.get('violent_frames', []):
                if 'Weapon' in str(frame.get('indicators', [])):
                    object_score = 1.0
                    break
        features.append(object_score)

        # Emotion score (from audio)
        emotion_score = 0
        if audio and 'score_breakdown' in audio:
            emotion_score = audio['score_breakdown'].get('fear_emotion', 0) / 100
        features.append(emotion_score)

        # Temporal consistency (from video)
        temporal_consistency = 0
        if video and 'temporal_consistency' in video:
            temporal_consistency = video['temporal_consistency']
        features.append(temporal_consistency)

        # Cross-modal agreement
        available = [v for v in [video, audio, text] if v and v.get('class') != 'Error']
        if len(available) >= 2:
            violence_count = sum(1 for v in available if v['class'] == 'Violence')
            agreement = violence_count / len(available)
        else:
            agreement = 0.5
        features.append(agreement)

        # Confidence scores
        features.extend([video_conf, audio_conf, text_conf])

        return np.array(features).reshape(1, -1)

    def predict(
        self,
        video: Optional[Dict[str, Any]],
        audio: Optional[Dict[str, Any]],
        text: Optional[Dict[str, Any]]
    ) -> Tuple[float, Dict[str, Any]]:
        """
        Predict violence probability using learned model.

        Returns:
            (violence_probability, explanation_dict)
        """
        # Extract features
        features = self.extract_features(video, audio, text)

        # If model not trained, use rule-based fallback
        if not self.is_trained:
            return self._rule_based_fallback(features[0])

        # Scale features
        features_scaled = self.scaler.transform(features)

        # Predict
        violence_prob = self.model.predict_proba(features_scaled)[0][1]

        # Get feature importances (for MLP, approximate with input sensitivity)
        explanation = self._explain_prediction(features[0], violence_prob)

        return violence_prob, explanation

    def _rule_based_fallback(self, features: np.ndarray) -> Tuple[float, Dict[str, Any]]:
        """Fallback to rule-based fusion if model not trained."""
        video_score = features[0]
        audio_score = features[1]
        text_score = features[2]
        object_score = features[3]
        emotion_score = features[4]
        temporal_consistency = features[5]
        agreement = features[6]

        # Weighted combination with learned-like behavior
        base_score = (
            video_score * 0.45 +
            audio_score * 0.30 +
            text_score * 0.15 +
            object_score * 0.05 +
            emotion_score * 0.05
        )

        # Boost for high agreement
        if agreement > 0.7:
            base_score *= 1.15

        # Boost for temporal consistency
        if temporal_consistency > 0.5:
            base_score *= 1.1

        violence_prob = min(base_score, 1.0)

        explanation = {
            'method': 'rule_based_fallback',
            'top_contributors': [
                ('video', video_score),
                ('audio', audio_score),
                ('text', text_score)
            ]
        }

        return violence_prob, explanation

    def _explain_prediction(self, features: np.ndarray, prob: float) -> Dict[str, Any]:
        """Generate explanation for prediction."""
        # Identify top contributors
        feature_contributions = []
        for i, (name, value) in enumerate(zip(self.feature_names, features)):
            if value > 0.1:  # Only significant features
                feature_contributions.append((name, float(value)))

        # Sort by value
        feature_contributions.sort(key=lambda x: x[1], reverse=True)

        return {
            'method': 'learned_model',
            'model_type': self.model_type,
            'top_contributors': feature_contributions[:5],
            'violence_probability': float(prob)
        }

    def train(self, X: np.ndarray, y: np.ndarray):
        """
        Train the fusion model on labeled data.

        Args:
            X: Feature matrix of shape (n_samples, n_features)
            y: Binary labels (0=non-violence, 1=violence)
        """
        logger.info(f"Training fusion model on {len(X)} samples...")

        # Scale features
        X_scaled = self.scaler.fit_transform(X)

        # Train model
        self.model.fit(X_scaled, y)
        self.is_trained = True

        # Log training performance
        train_score = self.model.score(X_scaled, y)
        logger.info(f"Fusion model training complete. Accuracy: {train_score:.3f}")

    def save(self, path: str):
        """Save trained model and scaler."""
        joblib.dump(self.model, path)
        joblib.dump(self.scaler, path.replace('.pkl', '_scaler.pkl'))
        logger.info(f"Saved fusion model to {path}")
