"""
Multi-modal fusion for Violence Detection System.
Combines results from text, video, and audio analyzers using parallel processing.

Enhanced with:
    - Weighted fusion with calibration (replaces majority vote)
    - Temporal violation detection and merging
    - Severity scoring
    - Embedding-based confidence refinement with cross-modal boost
    - False positive reduction
    - Policy-aware moderation
    - Structured explainability
    - LLM-based explainability
"""
from typing import Dict, Any, List, Optional
from concurrent.futures import ThreadPoolExecutor

from .base import BaseAnalyzer
from .text_analyzer import TextAnalyzer
from .video_analyzer import VideoAnalyzer
from .audio_analyzer import AudioAnalyzer
from .severity import compute_severity
from .calibration import get_calibration_layer
from ..config import get_config
from ..utils.logging import get_logger, log_performance
from ..utils.policy_engine import get_policy_engine
from ..utils.llm_explainer import get_llm_explainer

logger = get_logger(__name__)


class MultiModalFusion(BaseAnalyzer):
    """
    Combines multiple analysis modalities for comprehensive violence detection.
    Uses parallel processing for 2-3x speedup.
    """

    def __init__(self):
        super().__init__()
        self.text_analyzer = TextAnalyzer()
        self.video_analyzer = VideoAnalyzer()
        self.audio_analyzer = AudioAnalyzer()

    def analyze(self, content: Any) -> Dict[str, Any]:
        """Not used - use analyze_multimodal instead."""
        raise NotImplementedError("Use analyze_multimodal method")

    @log_performance('multimodal_fusion')
    def analyze_multimodal(
        self,
        video_path: Optional[str] = None,
        text: Optional[str] = None,
        parallel: bool = True
    ) -> Dict[str, Any]:
        """
        Analyze multiple modalities for violence detection.
        Uses temporal analysis for per-segment violation detection.
        """
        results = {
            'success': False,
            'video_prediction': None,
            'audio_prediction': None,
            'text_prediction': None,
            'fused_prediction': None,
            'violations': [],
            'message': ''
        }

        if parallel:
            results = self._analyze_parallel(video_path, text, results)
        else:
            results = self._analyze_sequential(video_path, text, results)

        # Merge temporal violations from all modalities
        all_violations = []
        for key in ['video_prediction', 'audio_prediction', 'text_prediction']:
            pred = results.get(key)
            if pred and 'violations' in pred:
                all_violations.extend(pred['violations'])

        # Sort violations by start_time (video/audio) or sentence_index (text)
        all_violations.sort(key=lambda v: v.get('start_seconds', v.get('sentence_index', 0)))
        results['violations'] = all_violations

        # Create fused prediction using weighted fusion
        predictions = [
            results['video_prediction'],
            results['audio_prediction'],
            results['text_prediction']
        ]
        valid_predictions = [p for p in predictions if p and p.get('class') != 'Error']

        if valid_predictions:
            results['fused_prediction'] = self._fuse_predictions(
                valid_predictions,
                results.get('embedding_similarity', 0)
            )

        # Generate recommended action from violations
        if all_violations:
            results['recommended_action'] = self._generate_recommended_action(all_violations)

        results['success'] = True
        results['message'] = 'Analysis completed using pretrained models'

        return results

    def _analyze_parallel(
        self,
        video_path: Optional[str],
        text: Optional[str],
        results: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Run temporal analyses in parallel using ThreadPoolExecutor."""
        futures = {}

        with ThreadPoolExecutor(max_workers=3) as executor:
            if video_path:
                futures['video'] = executor.submit(
                    self._safe_analyze_temporal,
                    self.video_analyzer,
                    video_path,
                    'video'
                )
                futures['audio'] = executor.submit(
                    self._safe_analyze_temporal,
                    self.audio_analyzer,
                    video_path,
                    'audio'
                )

            if text:
                futures['text'] = executor.submit(
                    self._safe_analyze_temporal,
                    self.text_analyzer,
                    text,
                    'text'
                )

            for name, future in futures.items():
                try:
                    result = future.result(timeout=120)
                    results[f'{name}_prediction'] = result
                except Exception as e:
                    logger.error(f"Parallel {name} analysis failed: {e}")

        return results

    def _analyze_sequential(
        self,
        video_path: Optional[str],
        text: Optional[str],
        results: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Run analyses sequentially (fallback mode)."""
        if video_path:
            results['video_prediction'] = self._safe_analyze_temporal(
                self.video_analyzer, video_path, 'video'
            )
            results['audio_prediction'] = self._safe_analyze_temporal(
                self.audio_analyzer, video_path, 'audio'
            )

        if text:
            results['text_prediction'] = self._safe_analyze_temporal(
                self.text_analyzer, text, 'text'
            )

        return results

    def _safe_analyze(
        self,
        analyzer: BaseAnalyzer,
        content: Any
    ) -> Optional[Dict[str, Any]]:
        """Safely run analyzer with error handling."""
        try:
            return analyzer.analyze(content)
        except Exception as e:
            logger.error(f"{analyzer.__class__.__name__} failed: {e}")
            return {
                'class': 'Error',
                'confidence': 0,
                'error': str(e)
            }

    def _safe_analyze_temporal(
        self,
        analyzer: BaseAnalyzer,
        content: Any,
        modality: str
    ) -> Optional[Dict[str, Any]]:
        """Safely run temporal analyzer with fallback to standard analysis."""
        try:
            if hasattr(analyzer, 'analyze_temporal'):
                return analyzer.analyze_temporal(content)
            return analyzer.analyze(content)
        except Exception as e:
            logger.error(f"{analyzer.__class__.__name__} temporal analysis failed: {e}")
            try:
                return analyzer.analyze(content)
            except Exception as e2:
                logger.error(f"{analyzer.__class__.__name__} fallback failed: {e2}")
                return {
                    'class': 'Error',
                    'confidence': 0,
                    'error': str(e2)
                }

    def _fuse_predictions(
        self,
        predictions: List[Dict[str, Any]],
        embedding_similarity: float = 0
    ) -> Dict[str, Any]:
        """
        Fuse predictions using strict weighted calibrated fusion.

        Three-tier decision:
        - Violation: any modality >= 90 calibrated, OR >= 2 modalities >= 70, OR fusion >= 75
        - Review Required: fusion score 55-74
        - Verified: fusion score < 55

        Strong negative guard: if ALL modalities < 60 and no weapon keywords → force Verified.
        Cross-modal boost capped at +5 (down from +8).
        """
        config = get_config()
        fusion_cfg = getattr(config, 'fusion', None)

        weights = {
            'video': getattr(fusion_cfg, 'video_weight', 0.4) if fusion_cfg else 0.4,
            'audio': getattr(fusion_cfg, 'audio_weight', 0.3) if fusion_cfg else 0.3,
            'text': getattr(fusion_cfg, 'text_weight', 0.3) if fusion_cfg else 0.3,
        }
        # Reduced cross-modal boost from 8 → 5
        cross_modal_boost = 5.0
        cross_modal_penalty = getattr(fusion_cfg, 'cross_modal_penalty', 10.0) if fusion_cfg else 10.0
        similarity_threshold = getattr(fusion_cfg, 'embedding_similarity_threshold', 0.65) if fusion_cfg else 0.65

        calibration = get_calibration_layer()

        # Calibrate each modality
        calibrated_scores = {}
        raw_scores = {}
        modality_classes = {}

        for pred in predictions:
            modality = pred.get('modality', 'unknown')
            raw_confidence = pred.get('confidence', 0)
            calibrated = calibration.calibrate(raw_confidence, modality)
            calibrated_scores[modality] = calibrated
            raw_scores[modality] = raw_confidence
            modality_classes[modality] = pred.get('class', 'Non-Violence')

        # --- Context filter (Step 4): reduce scores for sports/gaming/movie contexts ---
        try:
            from .context_detector import get_context_detector
            ctx_detector = get_context_detector()
            ctx_result = ctx_detector.detect(predictions)
            context_reduction = ctx_result.get('reduction_factor', 0)
        except Exception:
            context_reduction = self._detect_benign_context(predictions)

        if context_reduction > 0:
            for modality in calibrated_scores:
                calibrated_scores[modality] = calibrated_scores[modality] * (1 - context_reduction)
            logger.info(f"Context filter applied: -{context_reduction*100:.0f}% reduction")

        # Weighted combination — only violence-predicting modalities contribute positively
        weighted_score = 0.0
        total_weight = 0.0

        for modality, score in calibrated_scores.items():
            w = weights.get(modality, 0.2)
            if modality_classes[modality] == 'Violence':
                weighted_score += w * score
            else:
                weighted_score += w * (100 - score)
            total_weight += w

        if total_weight > 0:
            weighted_score = weighted_score / total_weight
        else:
            weighted_score = 0

        # Count violence-detecting modalities
        violence_count = sum(
            1 for cls in modality_classes.values()
            if cls == 'Violence'
        )

        # Conservative cross-modal adjustment (max +5, not +8)
        adjustment = 0
        adjustment_reason = 'none'

        if embedding_similarity > similarity_threshold and violence_count >= 2:
            adjustment = cross_modal_boost
            adjustment_reason = f'cross-modal agreement boost (+{cross_modal_boost}%)'
        elif violence_count > 0 and violence_count < len(predictions):
            non_violence_count = len(predictions) - violence_count
            if non_violence_count >= violence_count:
                halved_penalty = cross_modal_penalty / 2.0
                adjustment = -halved_penalty
                adjustment_reason = f'cross-modal contradiction penalty (-{halved_penalty}%)'

        final_confidence = max(0, min(100, weighted_score + adjustment))

        # --- Negative guard: only force Verified when ALL modalities < 45 ---
        all_below_threshold = all(
            calibrated_scores.get(m, 0) < 45
            for m in calibrated_scores
        )
        # Check for weapon keywords across predictions
        has_weapons = self._check_weapon_keywords(predictions)

        if all_below_threshold and not has_weapons:
            logger.info(
                f"Negative guard triggered: all calibrated scores < 45, no weapons. "
                f"Scores: {calibrated_scores}"
            )
            return {
                'class': 'Non-Violence',
                'confidence': float(max(0, 100 - final_confidence)),
                'fusion_method': 'weighted',
                'decision_tier': 'Verified',
                'decision_reason': 'negative_guard: all modalities below 45',
                'modality_weights': {k: float(v) for k, v in weights.items()},
                'calibrated_scores': {k: round(float(v), 2) for k, v in calibrated_scores.items()},
                'raw_scores': {k: round(float(v), 2) for k, v in raw_scores.items()},
                'modalities_detected': violence_count,
                'total_modalities': len(predictions),
                'cross_modal_adjustment': float(adjustment),
                'cross_modal_reason': adjustment_reason,
            }

        # --- Video-dominant bypass (Tier 0) ---
        # If video reports Violence with calibrated >= 70, skip weighted combination
        video_cal = calibrated_scores.get('video', 0)
        video_class = modality_classes.get('video', 'Non-Violence')
        if video_class == 'Violence' and video_cal >= 90:
            logger.info(
                f"Video-dominant bypass: video calibrated={video_cal:.1f}, "
                f"skipping weighted combination"
            )
            return {
                'class': 'Violence',
                'confidence': float(video_cal),
                'fusion_method': 'video_dominant_bypass',
                'decision_tier': 'Violation',
                'decision_reason': f'video_dominant: calibrated={video_cal:.1f}',
                'modality_weights': {k: float(v) for k, v in weights.items()},
                'calibrated_scores': {k: round(float(v), 2) for k, v in calibrated_scores.items()},
                'raw_scores': {k: round(float(v), 2) for k, v in raw_scores.items()},
                'modalities_detected': violence_count,
                'total_modalities': len(predictions),
                'cross_modal_adjustment': 0.0,
                'cross_modal_reason': 'bypassed',
            }

        # --- Strict 3-tier decision logic (Step 2) ---
        decision_tier = 'Verified'
        decision_reason = 'low_scores'
        is_violent = False

        # Tier 1: Any single modality >= 90 calibrated → Violation
        for modality, cls in modality_classes.items():
            if cls == 'Violence':
                cal_score = calibrated_scores.get(modality, 0)
                if cal_score >= 90:
                    is_violent = True
                    decision_tier = 'Violation'
                    decision_reason = f'single_modality_high: {modality}={cal_score:.1f}'
                    break

        # Tier 2: >= 2 modalities at >= 70 calibrated → Violation
        if not is_violent:
            high_modalities = [
                m for m, cls in modality_classes.items()
                if cls == 'Violence' and calibrated_scores.get(m, 0) >= 70
            ]
            if len(high_modalities) >= 2:
                is_violent = True
                decision_tier = 'Violation'
                decision_reason = f'multi_modality_agreement: {high_modalities}'

        # Tier 3: Fusion score >= 75 → Violation
        if not is_violent and final_confidence >= 75:
            is_violent = True
            decision_tier = 'Violation'
            decision_reason = f'fusion_score_high: {final_confidence:.1f}'

        # Middle tier: 55-74 → Review Required
        if not is_violent and final_confidence >= 55:
            decision_tier = 'Review Required'
            decision_reason = f'fusion_score_medium: {final_confidence:.1f}'

        logger.info(
            f"Fusion decision: tier={decision_tier}, confidence={final_confidence:.1f}, "
            f"violence_count={violence_count}, calibrated={calibrated_scores}, "
            f"reason={decision_reason}"
        )

        return {
            'class': 'Violence' if is_violent else 'Non-Violence',
            'confidence': float(final_confidence),
            'fusion_method': 'weighted',
            'decision_tier': decision_tier,
            'decision_reason': decision_reason,
            'modality_weights': {k: float(v) for k, v in weights.items()},
            'calibrated_scores': {k: round(float(v), 2) for k, v in calibrated_scores.items()},
            'raw_scores': {k: round(float(v), 2) for k, v in raw_scores.items()},
            'modalities_detected': violence_count,
            'total_modalities': len(predictions),
            'cross_modal_adjustment': float(adjustment),
            'cross_modal_reason': adjustment_reason,
        }

    @staticmethod
    def _check_weapon_keywords(predictions: List[Dict[str, Any]]) -> bool:
        """Check if any prediction contains weapon-related keywords."""
        weapon_words = {'gun', 'knife', 'weapon', 'bomb', 'explosive', 'rifle',
                        'pistol', 'sword', 'machete', 'grenade', 'firearm'}
        for pred in predictions:
            # Check text keywords
            for kw in pred.get('keywords_found', []):
                word = kw.split('(')[0].strip().lower()
                if word in weapon_words:
                    return True
            # Check video ML detections
            for frame in pred.get('violent_frames', []):
                ml_det = frame.get('ml_detection', '').lower()
                if any(w in ml_det for w in weapon_words):
                    return True
            # Check audio sounds
            for sound in pred.get('detected_sounds', []):
                if any(w in sound.lower() for w in ('gun', 'gunshot', 'explosion', 'bomb')):
                    return True
        return False

    @staticmethod
    def _detect_benign_context(predictions: List[Dict[str, Any]]) -> float:
        """
        Detect sports/gaming/movie/news context via keyword matching.
        Returns a reduction factor (0.0 = no reduction, 0.25 = reduce by 25%).
        """
        sports_keywords = {
            'boxing', 'boxer', 'fight card', 'mma', 'ufc', 'wrestling', 'wrestler',
            'match', 'tournament', 'championship', 'referee', 'round', 'knockout',
            'ring', 'arena', 'stadium', 'athlete', 'player', 'team', 'coach',
            'football', 'soccer', 'hockey', 'rugby', 'martial arts', 'karate',
            'taekwondo', 'judo', 'sparring', 'bout', 'heavyweight', 'lightweight',
            'sport', 'competition', 'league', 'score', 'goal', 'crowd cheered',
        }
        gaming_keywords = {
            'game', 'gaming', 'gamer', 'video game', 'gameplay', 'esports',
            'console', 'controller', 'level', 'boss fight', 'respawn', 'fps',
            'multiplayer', 'fortnite', 'call of duty', 'cod', 'minecraft',
            'playstation', 'xbox', 'nintendo', 'steam', 'twitch',
        }
        movie_keywords = {
            'movie', 'film', 'scene', 'actor', 'actress', 'director',
            'screenplay', 'cinema', 'trailer', 'sequel', 'prequel',
            'fictional', 'character', 'plot', 'storyline', 'episode',
            'series', 'tv show', 'netflix', 'hbo', 'disney',
        }
        news_keywords = {
            'reported', 'according to', 'news', 'journalist', 'reporter',
            'investigation', 'incident report', 'press conference', 'officials said',
            'authorities', 'police report', 'statement released',
        }

        # Collect all text from predictions
        all_text = ''
        for pred in predictions:
            reasoning = pred.get('reasoning', '')
            if isinstance(reasoning, str):
                all_text += ' ' + reasoning.lower()
            # Also check original text if available in keywords
            for kw in pred.get('keywords_found', []):
                all_text += ' ' + kw.lower()

        # Check original text content from text predictions
        for pred in predictions:
            if pred.get('modality') == 'text':
                # The text analyzer may store original text fragments in violations
                violations = pred.get('violations', [])
                for v in violations:
                    sentence = v.get('sentence', '')
                    if sentence:
                        all_text += ' ' + sentence.lower()

        if not all_text.strip():
            return 0.0

        # Count context matches
        sports_hits = sum(1 for kw in sports_keywords if kw in all_text)
        gaming_hits = sum(1 for kw in gaming_keywords if kw in all_text)
        movie_hits = sum(1 for kw in movie_keywords if kw in all_text)
        news_hits = sum(1 for kw in news_keywords if kw in all_text)

        max_hits = max(sports_hits, gaming_hits, movie_hits, news_hits)

        if max_hits >= 3:
            return 0.25  # Strong context signal → reduce by 25%
        elif max_hits >= 2:
            return 0.15  # Moderate context signal → reduce by 15%

        return 0.0

    def _generate_recommended_action(self, violations: List[Dict[str, Any]]) -> str:
        """Generate recommended action string from violations."""
        video_violations = [v for v in violations if v.get('modality') == 'video']
        audio_violations = [v for v in violations if v.get('modality') == 'audio']

        if video_violations:
            segments = []
            for v in video_violations:
                segments.append(f"{v['start_time']}-{v['end_time']}")
            return f"Cut or blur segment(s) {', '.join(segments)} to make video compliant."

        if audio_violations:
            segments = []
            for v in audio_violations:
                segments.append(f"{v['start_time']}-{v['end_time']}")
            return f"Mute audio segment(s) {', '.join(segments)}."

        text_violations = [v for v in violations if v.get('modality') == 'text']
        if text_violations:
            return f"Remove or revise {len(text_violations)} flagged sentence(s)."

        return "Review content for compliance."

    @staticmethod
    def _calculate_contributions(
        calibrated_scores: dict, weights: dict
    ) -> Dict[str, float]:
        """Calculate percentage contribution per modality."""
        contributions = {}
        total = 0
        for m, score in calibrated_scores.items():
            w = weights.get(m, 0.2)
            val = w * score
            contributions[m] = val
            total += val

        if total > 0:
            contributions = {m: round(v / total * 100, 1) for m, v in contributions.items()}
        else:
            contributions = {m: 0 for m in calibrated_scores}

        return contributions

    # ------------------------------------------------------------------
    # Enhanced fusion pipeline
    # ------------------------------------------------------------------
    def enhance_results(
        self,
        results: Dict[str, Any],
        text_input: Optional[str] = None,
        audio_data: Optional[tuple] = None,
        video_frames: Optional[list] = None,
    ) -> Dict[str, Any]:
        """
        Apply post-fusion enhancements to the analysis results.

        Ordering: embedding similarity -> fusion -> severity ->
        false positive -> explainability -> policy -> LLM explanation.
        """
        video = results.get('video_prediction')
        audio = results.get('audio_prediction')
        text = results.get('text_prediction')
        fused = results.get('fused_prediction')

        # 1) Embedding-based similarity (computed BEFORE fusion for boost)
        embedding_similarity = 0
        try:
            from .embedding_fusion import get_embedding_fusion

            embedding_fusion = get_embedding_fusion()
            current_confidence = fused.get('confidence', 0) if fused else 0
            audio_array, audio_sr = audio_data if audio_data else (None, None)

            embedding_result = embedding_fusion.refine_confidence(
                text_input=text_input,
                audio_array=audio_array,
                audio_sr=audio_sr,
                video_frames=video_frames,
                current_confidence=current_confidence,
            )
            results['embedding_adjustment'] = embedding_result
            sims = embedding_result.get('similarities', {})
            valid_sims = [v for v in sims.values() if v is not None]
            embedding_similarity = max(valid_sims) if valid_sims else 0

            # Cap embedding adjustment at +/-5 to prevent over-inflation
            raw_adj = embedding_result.get('adjustment', 0)
            capped_adj = max(-5, min(5, raw_adj))
            if fused and capped_adj != 0:
                fused['original_confidence'] = fused['confidence']
                fused['confidence'] = max(0, min(100, fused['confidence'] + capped_adj))
                fused['confidence_adjusted'] = True
                embedding_result['adjustment'] = capped_adj
                embedding_result['adjusted_confidence'] = fused['confidence']

        except Exception as e:
            logger.error(f"Embedding refinement failed: {e}")
            results['embedding_adjustment'] = {
                'adjusted_confidence': fused.get('confidence', 0) if fused else 0,
                'adjustment': 0,
                'adjustment_reason': f'Embedding refinement unavailable: {e}',
                'similarities': {},
                'embeddings_extracted': [],
            }

        # 2) Severity scoring
        try:
            results['severity'] = compute_severity(video, audio, text, fused)
        except Exception as e:
            logger.error(f"Severity scoring failed: {e}")
            results['severity'] = {
                'severity_score': 0,
                'severity_label': 'Unknown',
                'error': str(e),
            }

        # 3) False positive reduction
        try:
            if fused and fused.get('class') == 'Violence':
                from ..models.false_positive_reducer import get_false_positive_reducer
                reducer = get_false_positive_reducer()
                fp_result = reducer.analyze(video, audio, text, fused)
                results['fused_prediction'] = fp_result
                fused = fp_result  # Update reference
                results['false_positive_analysis'] = {
                    'category': fp_result.get('false_positive_category',
                                              fp_result.get('false_positive_warning', 'real_violence')),
                    'confidence': fp_result.get('false_positive_confidence', 0),
                }
            else:
                results['false_positive_analysis'] = {
                    'category': 'not_applicable',
                    'confidence': 0,
                }
        except Exception as e:
            logger.error(f"False positive reduction failed: {e}")
            results['false_positive_analysis'] = {
                'category': 'error',
                'confidence': 0,
                'error': str(e),
            }

        # 4) Structured explainability
        try:
            from ..utils.explainability import get_explainability_engine
            explainability = get_explainability_engine()
            results['structured_explanation'] = explainability.generate_explanation(
                fused or {}, video, audio, text,
                violations=results.get('violations', [])
            )
        except Exception as e:
            logger.error(f"Explainability failed: {e}")
            results['structured_explanation'] = {
                'error': str(e),
            }

        # 4b) Cross-modal reasoning
        try:
            from .reasoning_engine import get_reasoning_engine
            reasoning_engine = get_reasoning_engine()
            results['cross_modal_reasoning'] = reasoning_engine.analyze(video, audio, text)
        except Exception as e:
            logger.error(f"Cross-modal reasoning failed: {e}")
            results['cross_modal_reasoning'] = {
                'cross_modal_score': 0, 'agreements': [], 'contradictions': [],
                'reasoning': f'Unavailable: {e}',
            }

        # 4c) Event detection (merge violations into unified events)
        try:
            from .event_detector import get_event_detector
            event_detector = get_event_detector()
            results['violence_events'] = event_detector.detect_events(
                results.get('violations', [])
            )
        except Exception as e:
            logger.error(f"Event detection failed: {e}")
            results['violence_events'] = []

        # 4d) Modality contributions
        try:
            if fused:
                cal_scores = fused.get('calibrated_scores', {})
                mod_weights = fused.get('modality_weights', {})
                if cal_scores and mod_weights:
                    results['modality_contributions'] = self._calculate_contributions(
                        cal_scores, mod_weights
                    )
        except Exception as e:
            logger.error(f"Contributions calculation failed: {e}")

        # 5) Policy matching (try RAG first, fallback to keyword engine)
        try:
            rag_config = get_config().rag
            if rag_config.use_rag:
                try:
                    from ..rag import get_rag_policy_engine
                    rag_engine = get_rag_policy_engine()
                    results['policy_matches'] = rag_engine.evaluate(
                        video_result=video,
                        audio_result=audio,
                        text_result=text,
                        fused_result=fused,
                    )
                except Exception as rag_e:
                    logger.warning(f"RAG policy failed, falling back to keyword engine: {rag_e}")
                    policy_engine = get_policy_engine()
                    results['policy_matches'] = policy_engine.evaluate(
                        video_result=video, audio_result=audio,
                        text_result=text, fused_result=fused,
                    )
            else:
                policy_engine = get_policy_engine()
                results['policy_matches'] = policy_engine.evaluate(
                    video_result=video, audio_result=audio,
                    text_result=text, fused_result=fused,
                )
        except Exception as e:
            logger.error(f"Policy evaluation failed: {e}")
            results['policy_matches'] = {
                'policy_triggered': False,
                'matched_policies': [],
                'total_policies_matched': 0,
                'error': str(e),
            }

        # 5b) Risk scoring
        try:
            from .risk_scoring import get_risk_scorer
            risk_scorer = get_risk_scorer()
            results['risk_score'] = risk_scorer.compute_risk(
                video_prediction=video,
                audio_prediction=audio,
                text_prediction=text,
                fused_prediction=fused,
                violations=results.get('violations', []),
            )
        except Exception as e:
            logger.error(f"Risk scoring failed: {e}")
            results['risk_score'] = {
                'violence_probability': 0,
                'severity': 'Unknown',
                'risk_level': 'Unknown',
                'recommendation': 'Risk scoring unavailable.',
                'error': str(e),
            }

        # 6) LLM explanation (last, since it uses severity & policy data)
        try:
            llm_explainer = get_llm_explainer()
            results['llm_explanation'] = llm_explainer.generate_report(
                video_result=video,
                audio_result=audio,
                text_result=text,
                fused_result=fused,
                severity=results.get('severity'),
                policy_matches=results.get('policy_matches'),
            )
        except Exception as e:
            logger.error(f"LLM explanation failed: {e}")
            results['llm_explanation'] = {
                'summary': 'Explanation unavailable.',
                'risk_level': 'Unknown',
                'recommended_action': 'Manual review required.',
                'detailed_explanation': f'LLM explanation generation failed: {e}',
                'confidence_breakdown': {},
                'generation_method': 'error',
            }

        return results

    def analyze_video_only(self, video_path: str) -> Dict[str, Any]:
        """Analyze video only (no audio/text)."""
        return self._safe_analyze(self.video_analyzer, video_path)

    def analyze_text_only(self, text: str) -> Dict[str, Any]:
        """Analyze text only."""
        return self._safe_analyze(self.text_analyzer, text)

    def analyze_audio_only(self, video_path: str) -> Dict[str, Any]:
        """Analyze audio only from video file."""
        return self._safe_analyze(self.audio_analyzer, video_path)
