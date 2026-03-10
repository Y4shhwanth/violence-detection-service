"""
Embedding-Based Confidence Refinement for Violence Detection System.

Extracts CLS / pooled embeddings from the existing pretrained models
(Toxic-BERT, AST, NSFW image classifier) and uses cross-modal cosine
similarity to adjust the final confidence score.

No training. No fine-tuning. Pure inference on existing models.
"""
from typing import Dict, Any, Optional, List, Tuple

import numpy as np
import torch
import cv2
from PIL import Image

from ..utils.logging import get_logger
from ..models.loader import get_model_manager

logger = get_logger(__name__)

# Thresholds for confidence adjustment
SIMILARITY_BOOST_THRESHOLD = 0.6    # boost if similarity > this across >=2 pairs
SIMILARITY_REDUCE_THRESHOLD = 0.2   # reduce if similarity < this across all pairs
CONFIDENCE_BOOST_PERCENT = 10.0
CONFIDENCE_REDUCE_PERCENT = 10.0

# Skip cosine similarity if dimension ratio exceeds this (meaningless comparison)
MAX_DIM_RATIO = 10


class EmbeddingFusion:
    """
    Extracts embeddings from existing pretrained models and uses
    cross-modal cosine similarity to refine confidence.
    """

    def __init__(self):
        self.logger = get_logger(__name__)
        self.model_manager = get_model_manager()

    def refine_confidence(
        self,
        text_input: Optional[str] = None,
        audio_array: Optional[np.ndarray] = None,
        audio_sr: Optional[int] = None,
        video_frames: Optional[List[np.ndarray]] = None,
        current_confidence: float = 0.0,
    ) -> Dict[str, Any]:
        """
        Extract embeddings and compute cross-modal similarity to adjust confidence.

        Args:
            text_input: Raw text string (for Toxic-BERT embedding)
            audio_array: Audio waveform numpy array (for AST embedding)
            audio_sr: Audio sample rate
            video_frames: List of video frames as numpy arrays (for NSFW model embedding)
            current_confidence: The current fused confidence score (0-100)

        Returns:
            {
                "adjusted_confidence": float,
                "adjustment": float,         # delta applied
                "adjustment_reason": str,
                "similarities": {
                    "text_video": float | null,
                    "text_audio": float | null,
                    "video_audio": float | null,
                },
                "avg_similarity": float,
                "embeddings_extracted": list[str],
            }
        """
        embeddings: Dict[str, Optional[np.ndarray]] = {}
        extracted: List[str] = []

        # Extract embeddings from each available modality
        if text_input:
            emb = self._extract_text_embedding(text_input)
            if emb is not None:
                embeddings['text'] = emb
                extracted.append('text')

        if audio_array is not None and audio_sr is not None:
            emb = self._extract_audio_embedding(audio_array, audio_sr)
            if emb is not None:
                embeddings['audio'] = emb
                extracted.append('audio')

        if video_frames:
            emb = self._extract_video_embedding(video_frames)
            if emb is not None:
                embeddings['video'] = emb
                extracted.append('video')

        # Compute pairwise cosine similarities
        similarities, sim_values = self._compute_similarities(embeddings)

        # Determine adjustment — require at least 2 similarity pairs for any action
        adjustment = 0.0
        reason = 'No adjustment — insufficient embeddings'

        if len(sim_values) >= 2:
            avg_sim = float(np.mean(sim_values))
            high_agreement_count = sum(1 for s in sim_values if s > SIMILARITY_BOOST_THRESHOLD)
            all_low = all(s < SIMILARITY_REDUCE_THRESHOLD for s in sim_values)

            if high_agreement_count >= 2:
                adjustment = CONFIDENCE_BOOST_PERCENT
                reason = (
                    f'High cross-modal agreement ({high_agreement_count} pairs > '
                    f'{SIMILARITY_BOOST_THRESHOLD}): boosting confidence by +{CONFIDENCE_BOOST_PERCENT}%'
                )
            elif high_agreement_count >= 1 and avg_sim > 0.4:
                adjustment = CONFIDENCE_BOOST_PERCENT * 0.5
                reason = (
                    f'Moderate cross-modal agreement (avg={avg_sim:.3f}): '
                    f'boosting confidence by +{adjustment}%'
                )
            elif all_low:
                adjustment = -CONFIDENCE_REDUCE_PERCENT
                reason = (
                    f'Low cross-modal agreement (all pairs < {SIMILARITY_REDUCE_THRESHOLD}): '
                    f'reducing confidence by -{CONFIDENCE_REDUCE_PERCENT}%'
                )
            else:
                reason = f'Neutral cross-modal agreement (avg={avg_sim:.3f}): no adjustment'
        elif len(sim_values) == 1:
            avg_sim = float(sim_values[0])
            reason = f'Only 1 similarity pair available (sim={avg_sim:.3f}): no adjustment'
        else:
            avg_sim = 0.0

        adjusted = max(0.0, min(100.0, current_confidence + adjustment))

        self.logger.info(
            f"Embedding refinement: extracted={extracted}, avg_sim={avg_sim:.3f}, "
            f"adjustment={adjustment:+.1f}, confidence {current_confidence:.1f} -> {adjusted:.1f}"
        )

        return {
            'adjusted_confidence': round(adjusted, 2),
            'adjustment': round(adjustment, 2),
            'adjustment_reason': reason,
            'similarities': similarities,
            'avg_similarity': round(avg_sim, 4),
            'embeddings_extracted': extracted,
        }

    # ------------------------------------------------------------------
    # Embedding extraction
    # ------------------------------------------------------------------
    def _extract_text_embedding(self, text: str) -> Optional[np.ndarray]:
        """
        Extract CLS embedding from Toxic-BERT.

        Note: Toxic-BERT uses BertForSequenceClassification which provides
        last_hidden_state by default. We pass output_hidden_states=True
        for robustness.
        """
        try:
            classifier = self.model_manager.text_classifier
            if classifier is None:
                return None

            tokenizer = classifier.tokenizer
            model = classifier.model

            inputs = tokenizer(
                text[:512],
                return_tensors='pt',
                truncation=True,
                max_length=512,
                padding=True,
            )

            # Move to same device as model
            device = next(model.parameters()).device
            inputs = {k: v.to(device) for k, v in inputs.items()}

            with torch.no_grad():
                outputs = model(**inputs, output_hidden_states=True)

            # CLS token is the first token's hidden state
            if hasattr(outputs, 'hidden_states') and outputs.hidden_states:
                cls_embedding = outputs.hidden_states[-1][:, 0, :].cpu().numpy().flatten()
            elif hasattr(outputs, 'last_hidden_state') and outputs.last_hidden_state is not None:
                cls_embedding = outputs.last_hidden_state[:, 0, :].cpu().numpy().flatten()
            else:
                # Fallback: use logits as a lower-dimensional representation
                cls_embedding = outputs.logits.cpu().numpy().flatten()

            return self._normalize(cls_embedding)

        except Exception as e:
            self.logger.warning(f"Text embedding extraction failed: {e}")
            return None

    def _extract_audio_embedding(
        self,
        audio: np.ndarray,
        sr: int,
    ) -> Optional[np.ndarray]:
        """Extract pooled embedding from AST model."""
        try:
            classifier = self.model_manager.audio_classifier
            if classifier is None:
                return None

            model = classifier.model
            feature_extractor = classifier.feature_extractor

            inputs = feature_extractor(
                audio,
                sampling_rate=sr,
                return_tensors='pt',
                padding=True,
            )

            device = next(model.parameters()).device
            inputs = {k: v.to(device) for k, v in inputs.items()}

            with torch.no_grad():
                outputs = model(**inputs)

            # Use pooler output or mean of last hidden state
            if hasattr(outputs, 'pooler_output') and outputs.pooler_output is not None:
                embedding = outputs.pooler_output.cpu().numpy().flatten()
            elif hasattr(outputs, 'last_hidden_state') and outputs.last_hidden_state is not None:
                embedding = outputs.last_hidden_state.mean(dim=1).cpu().numpy().flatten()
            else:
                embedding = outputs.logits.cpu().numpy().flatten()

            return self._normalize(embedding)

        except Exception as e:
            self.logger.warning(f"Audio embedding extraction failed: {e}")
            return None

    def _extract_video_embedding(
        self,
        frames: List[np.ndarray],
    ) -> Optional[np.ndarray]:
        """Extract average frame embedding from NSFW image classifier."""
        try:
            classifier = self.model_manager.image_classifier
            if classifier is None:
                return None

            model = classifier.model
            feature_extractor = (
                getattr(classifier, 'feature_extractor', None)
                or getattr(classifier, 'image_processor', None)
            )
            if feature_extractor is None:
                self.logger.warning("No feature_extractor or image_processor found on image classifier")
                return None

            frame_embeddings = []

            # Sample up to 5 frames for efficiency
            step = max(1, len(frames) // 5)
            sampled = frames[::step][:5]

            # Hoist device detection outside the loop
            device = next(model.parameters()).device

            for frame in sampled:
                if len(frame.shape) == 3 and frame.shape[2] == 3:
                    frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                else:
                    frame_rgb = frame

                pil_image = Image.fromarray(frame_rgb)
                inputs = feature_extractor(images=pil_image, return_tensors='pt')
                inputs = {k: v.to(device) for k, v in inputs.items()}

                with torch.no_grad():
                    outputs = model(**inputs)

                if hasattr(outputs, 'pooler_output') and outputs.pooler_output is not None:
                    emb = outputs.pooler_output.cpu().numpy().flatten()
                elif hasattr(outputs, 'last_hidden_state') and outputs.last_hidden_state is not None:
                    emb = outputs.last_hidden_state.mean(dim=1).cpu().numpy().flatten()
                else:
                    emb = outputs.logits.cpu().numpy().flatten()

                frame_embeddings.append(emb)

            if not frame_embeddings:
                return None

            # Average frame embeddings
            avg_embedding = np.mean(frame_embeddings, axis=0)
            return self._normalize(avg_embedding)

        except Exception as e:
            self.logger.warning(f"Video embedding extraction failed: {e}")
            return None

    # ------------------------------------------------------------------
    # Similarity computation
    # ------------------------------------------------------------------
    def _compute_similarities(
        self,
        embeddings: Dict[str, Optional[np.ndarray]],
    ) -> Tuple[Dict[str, Optional[float]], List[float]]:
        """Compute pairwise cosine similarities between available embeddings."""
        pairs = [
            ('text', 'video', 'text_video'),
            ('text', 'audio', 'text_audio'),
            ('video', 'audio', 'video_audio'),
        ]

        similarities: Dict[str, Optional[float]] = {}
        sim_values: List[float] = []

        for key_a, key_b, pair_name in pairs:
            emb_a = embeddings.get(key_a)
            emb_b = embeddings.get(key_b)

            if emb_a is not None and emb_b is not None:
                sim = self._cosine_similarity(emb_a, emb_b)
                if sim is not None:
                    similarities[pair_name] = round(float(sim), 4)
                    sim_values.append(float(sim))
                else:
                    similarities[pair_name] = None
            else:
                similarities[pair_name] = None

        return similarities, sim_values

    @staticmethod
    def _cosine_similarity(a: np.ndarray, b: np.ndarray) -> Optional[float]:
        """
        Compute cosine similarity between two vectors.

        Returns None if dimension mismatch is too extreme (ratio > MAX_DIM_RATIO),
        since truncation would discard too much information.
        """
        if a.shape != b.shape:
            max_dim = max(len(a), len(b))
            min_dim = min(len(a), len(b))

            if min_dim == 0:
                return 0.0

            if max_dim / min_dim > MAX_DIM_RATIO:
                logger.warning(
                    f"Dimension mismatch too large ({len(a)} vs {len(b)}), "
                    f"skipping similarity computation"
                )
                return None

            # Truncate to common dimensions
            logger.debug(f"Truncating embeddings from {len(a)},{len(b)} to {min_dim}")
            a = a[:min_dim]
            b = b[:min_dim]

        dot = np.dot(a, b)
        norm_a = np.linalg.norm(a)
        norm_b = np.linalg.norm(b)

        if norm_a == 0 or norm_b == 0:
            return 0.0

        return float(dot / (norm_a * norm_b))

    @staticmethod
    def _normalize(vec: np.ndarray) -> np.ndarray:
        """L2-normalize a vector."""
        norm = np.linalg.norm(vec)
        if norm == 0:
            return vec
        return vec / norm


# ---------------------------------------------------------------------------
# Module-level singleton
# ---------------------------------------------------------------------------
_embedding_fusion: Optional[EmbeddingFusion] = None


def get_embedding_fusion() -> EmbeddingFusion:
    """Get or create global EmbeddingFusion instance."""
    global _embedding_fusion
    if _embedding_fusion is None:
        _embedding_fusion = EmbeddingFusion()
    return _embedding_fusion
