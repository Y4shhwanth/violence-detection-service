

import os
import torch
import numpy as np
from flask import Flask, render_template, request, jsonify
from flask_cors import CORS
from werkzeug.utils import secure_filename
from transformers import pipeline
from PIL import Image
import cv2
from moviepy import VideoFileClip
import librosa

# Initialize Flask app
app = Flask(__name__)
CORS(app)  # Enable CORS for React frontend
app.config['MAX_CONTENT_LENGTH'] = 100 * 1024 * 1024
app.config['UPLOAD_FOLDER'] = 'static/uploads'
app.config['SECRET_KEY'] = 'violence-detection-secret-key'

os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# Global model variables
text_classifier = None
image_classifier = None
audio_classifier = None

def load_pretrained_models():
    """Load pretrained models from Hugging Face"""
    global text_classifier, image_classifier, audio_classifier

    print("Loading pretrained models...")
    device = 0 if torch.cuda.is_available() else -1

    # Text toxicity/violence detector
    try:
        text_classifier = pipeline(
            "text-classification",
            model="unitary/toxic-bert",
            device=device
        )
        print("✓ Text toxicity model loaded")
    except:
        text_classifier = pipeline("sentiment-analysis", device=device)
        print("⚠ Using fallback sentiment model for text")

    # Image violence/NSFW detector
    try:
        image_classifier = pipeline(
            "image-classification",
            model="Falconsai/nsfw_image_detection",
            device=device
        )
        print("✓ Image safety model loaded")
    except Exception as e:
        print(f"⚠ Image model error: {e}")
        image_classifier = None

    # Audio classification model
    try:
        audio_classifier = pipeline(
            "audio-classification",
            model="MIT/ast-finetuned-audioset-10-10-0.4593",
            device=device
        )
        print("✓ Audio classification model loaded")
    except Exception as e:
        print(f"⚠ Audio model error: {e}")
        audio_classifier = None

    print("Models loaded successfully!")


def analyze_text_content(text):
    """ULTRA AGGRESSIVE: Analyze text for violence/toxicity with detailed reasoning"""
    if not text or len(text.strip()) == 0:
        return None

    try:
        import re

        # Violence keywords (expanded list)
        violence_keywords = {
            'extreme': ['kill', 'murder', 'assassinate', 'slaughter', 'massacre', 'execute'],
            'physical': ['beat', 'punch', 'kick', 'stab', 'shoot', 'hit', 'attack', 'assault', 'fight'],
            'weapons': ['gun', 'knife', 'weapon', 'bomb', 'explosive', 'rifle', 'pistol'],
            'threats': ['threat', 'threaten', 'hurt', 'harm', 'injure', 'damage', 'destroy'],
            'hate': ['hate', 'despise', 'loathe', 'detest'],
            'death': ['death', 'die', 'dead', 'corpse', 'blood', 'bleed'],
            'abuse': ['abuse', 'torture', 'rape', 'kidnap', 'hostage']
        }

        # Analyze text
        text_lower = text.lower()
        found_keywords = []
        violence_score = 0

        # Check for keywords
        for category, words in violence_keywords.items():
            for word in words:
                if word in text_lower:
                    found_keywords.append(f"{word} ({category})")
                    # More aggressive scoring
                    if category == 'extreme':
                        violence_score += 35
                    elif category == 'physical':
                        violence_score += 25
                    elif category in ['weapons', 'threats']:
                        violence_score += 20
                    else:
                        violence_score += 15

        # Check for threatening patterns
        threat_patterns = [
            r'i (will|gonna|going to) (kill|hurt|beat|destroy)',
            r'you (will|gonna|going to) (die|suffer|regret)',
            r'(deserve|should|must) (die|death|suffer)',
        ]

        for pattern in threat_patterns:
            if re.search(pattern, text_lower):
                violence_score += 40
                found_keywords.append("direct threat (pattern)")

        # Use ML model
        ml_result = text_classifier(text[:512])[0]
        ml_label = ml_result['label'].lower()
        ml_score = ml_result['score'] * 100

        # Check if ML detected violence (not just 'toxic' in label, but actual toxic classification)
        ml_detected_violence = (
            (ml_label == 'toxic' and ml_score > 50) or
            (ml_label == 'negative' and ml_score > 60)
        )

        # Combine scores (80% keyword + 20% ML for more aggressive)
        if found_keywords:
            combined_score = min(violence_score, 100)
        else:
            combined_score = ml_score if ml_detected_violence else 0

        # VERY AGGRESSIVE THRESHOLD: 15 (was implicit 50)
        is_violent = (
            violence_score > 15 or           # Very low threshold on keywords
            ml_detected_violence or          # ML says toxic with confidence
            len(found_keywords) > 0          # Any keyword found
        )

        # Build reasoning
        reasoning = []
        if found_keywords:
            reasoning.append(f"Found {len(found_keywords)} violence indicators: {', '.join(found_keywords[:5])}")
        if ml_detected_violence:
            reasoning.append(f"ML model detected: {ml_label} ({ml_score:.1f}% confidence)")

        if is_violent:
            final_confidence = max(combined_score + 20, 60.0)  # Boost + minimum
            return {
                'class': 'Violence',
                'confidence': min(final_confidence, 95.0),
                'reasoning': ' | '.join(reasoning) if reasoning else 'Toxic content detected',
                'keywords_found': found_keywords[:10],
                'ml_score': ml_score
            }
        else:
            return {
                'class': 'Non-Violence',
                'confidence': max(100 - combined_score, 60.0),
                'reasoning': 'No significant violence indicators found',
                'keywords_found': [],
                'ml_score': ml_score
            }
    except Exception as e:
        return {
            'class': 'Error',
            'confidence': 0,
            'error': str(e)
        }


def detect_violence_heuristics(frame):
    """
    AGGRESSIVE violence detection - More sensitive to violence indicators
    Returns violence score 0-100
    """
    violence_score = 0

    # 1. RED COLOR INTENSITY (blood indicator) - MORE AGGRESSIVE
    red_channel = frame[:, :, 2]
    green_channel = frame[:, :, 1]
    blue_channel = frame[:, :, 0]

    red_intensity = np.mean(red_channel)
    red_dominance = np.mean(red_channel > (green_channel + blue_channel) / 2)

    # LOWERED THRESHOLDS - More sensitive
    if red_intensity > 130 and red_dominance > 0.25:  # Was 140/0.3
        violence_score += 45  # Was 35
    elif red_intensity > 110 and red_dominance > 0.15:  # Was 120/0.2
        violence_score += 30  # Was 20
    elif red_intensity > 100:  # NEW: Any significant red
        violence_score += 15

    # 2. DARKNESS (violent scenes often darker) - MORE AGGRESSIVE
    brightness = np.mean(cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY))
    if brightness < 90:  # Was 80
        violence_score += 20  # Was 15
    elif brightness < 110:  # NEW: Moderately dark
        violence_score += 10

    # 3. COLOR VARIANCE (chaos indicator) - MORE AGGRESSIVE
    color_variance = np.std(frame)
    if color_variance > 60:  # Was 70
        violence_score += 20  # Was 15
    elif color_variance > 50:  # NEW: Moderate chaos
        violence_score += 10

    # 4. EDGE DENSITY (sharp objects, weapons) - MORE AGGRESSIVE
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    edges = cv2.Canny(gray, 50, 150)
    edge_density = np.sum(edges > 0) / edges.size

    if edge_density > 0.12:  # Was 0.15
        violence_score += 25  # Was 20
    elif edge_density > 0.08:  # NEW: Moderate edges
        violence_score += 15

    # 5. NEW: Motion indicator (blur detection)
    # Blurry frames often indicate fast motion (fights)
    laplacian_var = cv2.Laplacian(gray, cv2.CV_64F).var()
    if laplacian_var < 100:  # Low variance = blurry
        violence_score += 10

    return min(violence_score, 100)


def analyze_video_content(video_path):
    """IMPROVED: Analyze video frames with DETAILED REASONING about where and why violence detected"""
    try:
        import sys
        print(f"\n=== Analyzing video: {video_path} ===", flush=True)
        sys.stdout.flush()
        cap = cv2.VideoCapture(video_path)

        if not cap.isOpened():
            return {'class': 'Error', 'confidence': 0, 'error': 'Cannot open video'}

        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        fps = cap.get(cv2.CAP_PROP_FPS) or 30
        duration = total_frames / fps

        print(f"Total frames: {total_frames}, Duration: {duration:.1f}s, FPS: {fps:.1f}")

        # Sample multiple frames (15 frames across the video)
        num_samples = min(15, total_frames)
        frame_indices = np.linspace(0, total_frames - 1, num_samples, dtype=int)

        violence_scores = []
        ml_scores = []
        frame_details = []  # Store details for each frame

        for idx, frame_idx in enumerate(frame_indices):
            cap.set(cv2.CAP_PROP_POS_FRAMES, frame_idx)
            ret, frame = cap.read()

            if not ret:
                continue

            # Calculate timestamp
            timestamp = frame_idx / fps

            # Get detailed violence indicators
            frame_analysis = analyze_frame_detailed(frame)

            heuristic_score = frame_analysis['score']
            violence_scores.append(heuristic_score)

            # Build frame-specific reasoning
            frame_info = {
                'frame_number': frame_idx,
                'timestamp': f"{int(timestamp//60)}:{int(timestamp%60):02d}",
                'score': heuristic_score,
                'indicators': frame_analysis['indicators'],
                'reasoning': frame_analysis['reasoning']
            }

            # Method 2: ML-based detection (every 3rd frame)
            if image_classifier and idx % 3 == 0:
                try:
                    frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                    pil_image = Image.fromarray(frame_rgb)
                    results = image_classifier(pil_image)

                    frame_violence_score = 0
                    ml_labels = []
                    for result in results:
                        label = result['label'].lower()
                        score = result['score']
                        if any(word in label for word in ['nsfw', 'violence', 'blood', 'weapon', 'explicit']):
                            frame_violence_score = max(frame_violence_score, score * 100)
                            ml_labels.append(f"{label}({score*100:.0f}%)")

                    ml_scores.append(frame_violence_score)
                    if ml_labels:
                        frame_info['ml_detection'] = ', '.join(ml_labels)
                except:
                    pass

            frame_details.append(frame_info)

        cap.release()

        if not violence_scores:
            return {'class': 'Error', 'confidence': 0, 'error': 'No frames analyzed'}

        # Calculate statistics
        avg_heuristic = np.mean(violence_scores)
        max_heuristic = np.max(violence_scores)

        print(f"Heuristic: avg={avg_heuristic:.1f}, max={max_heuristic:.1f}")

        if ml_scores:
            avg_ml = np.mean(ml_scores)
            max_ml = np.max(ml_scores)
            print(f"ML: avg={avg_ml:.1f}, max={max_ml:.1f}")
            combined_score = (avg_heuristic * 0.6) + (max_ml * 0.4)
        else:
            combined_score = avg_heuristic

        print(f"Combined score: {combined_score:.1f}")

        # Find most violent frames (top 3)
        violent_frames = sorted(frame_details, key=lambda x: x['score'], reverse=True)[:3]

        # VERY AGGRESSIVE THRESHOLD: 20 (was 30)
        is_violent = (
            combined_score > 20 or
            max_heuristic > 35 or
            avg_heuristic > 25 or
            (ml_scores and max(ml_scores) > 40)
        )

        # Build comprehensive reasoning
        reasoning_parts = []

        if is_violent:
            reasoning_parts.append(f"Violence detected across {len([f for f in frame_details if f['score'] > 30])} frames")

            # Top violent moments
            for i, vf in enumerate(violent_frames, 1):
                if vf['score'] > 30:
                    reasoning_parts.append(
                        f"[{vf['timestamp']}] Frame #{vf['frame_number']}: {vf['reasoning']} (Score: {vf['score']:.0f})"
                    )

            confidence = min(combined_score + 20, 95.0)

            # Convert numpy types to Python native types for JSON serialization
            violent_frames_clean = []
            for vf in violent_frames:
                violent_frames_clean.append({
                    'frame_number': int(vf['frame_number']),
                    'timestamp': vf['timestamp'],
                    'score': int(vf['score']),
                    'indicators': vf['indicators'],
                    'reasoning': vf['reasoning']
                })

            return {
                'class': 'Violence',
                'confidence': float(max(confidence, 60.0)),
                'reasoning': ' | '.join(reasoning_parts),
                'violent_frames': violent_frames_clean,
                'avg_score': float(avg_heuristic),
                'max_score': float(max_heuristic),
                'total_frames_analyzed': len(frame_details)
            }
        else:
            return {
                'class': 'Non-Violence',
                'confidence': float(100 - combined_score),
                'reasoning': f'Low violence indicators across all frames (avg: {avg_heuristic:.1f})',
                'avg_score': float(avg_heuristic),
                'max_score': float(max_heuristic),
                'total_frames_analyzed': len(frame_details)
            }

    except Exception as e:
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()
        return {
            'class': 'Error',
            'confidence': 0,
            'error': str(e)
        }


def analyze_frame_detailed(frame):
    """
    Analyze a single frame and return detailed reasoning
    Returns: dict with score, indicators, and reasoning
    """
    violence_score = 0
    indicators = []
    reasoning_parts = []

    # 1. RED COLOR INTENSITY (blood indicator)
    red_channel = frame[:, :, 2]
    green_channel = frame[:, :, 1]
    blue_channel = frame[:, :, 0]

    red_intensity = np.mean(red_channel)
    red_dominance = np.mean(red_channel > (green_channel + blue_channel) / 2)

    if red_intensity > 130 and red_dominance > 0.25:
        violence_score += 45
        indicators.append('High red intensity')
        reasoning_parts.append(f"Significant red/blood-like colors (intensity: {red_intensity:.0f})")
    elif red_intensity > 110 and red_dominance > 0.15:
        violence_score += 30
        indicators.append('Moderate red')
        reasoning_parts.append(f"Moderate red tones (intensity: {red_intensity:.0f})")
    elif red_intensity > 100:
        violence_score += 15
        indicators.append('Some red')

    # 2. DARKNESS
    brightness = np.mean(cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY))
    if brightness < 90:
        violence_score += 20
        indicators.append('Very dark')
        reasoning_parts.append(f"Dark scene (brightness: {brightness:.0f})")
    elif brightness < 110:
        violence_score += 10
        indicators.append('Moderately dark')

    # 3. COLOR VARIANCE (chaos)
    color_variance = np.std(frame)
    if color_variance > 60:
        violence_score += 20
        indicators.append('High chaos')
        reasoning_parts.append(f"Chaotic/varied colors (variance: {color_variance:.0f})")
    elif color_variance > 50:
        violence_score += 10
        indicators.append('Moderate chaos')

    # 4. EDGE DENSITY (weapons/objects)
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    edges = cv2.Canny(gray, 50, 150)
    edge_density = np.sum(edges > 0) / edges.size

    if edge_density > 0.12:
        violence_score += 25
        indicators.append('Many sharp edges')
        reasoning_parts.append(f"Many sharp objects/edges detected ({edge_density:.3f})")
    elif edge_density > 0.08:
        violence_score += 15
        indicators.append('Some edges')

    # 5. MOTION (blur)
    laplacian_var = cv2.Laplacian(gray, cv2.CV_64F).var()
    if laplacian_var < 100:
        violence_score += 10
        indicators.append('Motion blur')
        reasoning_parts.append("Fast motion/blur detected")

    # Build reasoning string
    if not reasoning_parts:
        reasoning = "No significant violence indicators"
    else:
        reasoning = '; '.join(reasoning_parts)

    return {
        'score': min(violence_score, 100),
        'indicators': indicators,
        'reasoning': reasoning
    }


def analyze_audio_content(video_path):
    """
    Extract and analyze audio from video for violence detection
    Returns: dict with class, confidence, and reasoning
    """
    try:
        if not audio_classifier:
            return {
                'class': 'Error',
                'confidence': 0,
                'error': 'Audio model not loaded'
            }

        # Extract audio from video
        print(f"Extracting audio from: {video_path}")

        # Create temporary audio file
        audio_path = video_path.replace('.mp4', '_audio.wav')

        try:
            video_clip = VideoFileClip(video_path)
            if video_clip.audio is None:
                return {
                    'class': 'Non-Violence',
                    'confidence': 100.0,
                    'reasoning': 'No audio track found in video'
                }

            video_clip.audio.write_audiofile(audio_path)
            video_clip.close()
        except Exception as e:
            print(f"Audio extraction error: {e}")
            return {
                'class': 'Non-Violence',
                'confidence': 100.0,
                'reasoning': 'Could not extract audio from video'
            }

        # Load audio with librosa
        audio, sr = librosa.load(audio_path, sr=16000, duration=30)  # First 30 seconds

        # Analyze audio with pretrained model
        results = audio_classifier(audio, sampling_rate=sr, top_k=10)

        # Violence-related sound categories
        violence_sounds = {
            'gunshot': 60, 'gun': 60, 'explosion': 60, 'bomb': 60,
            'scream': 50, 'screaming': 50, 'shout': 45, 'yell': 45,
            'siren': 40, 'alarm': 40, 'police': 40, 'fire': 35,
            'crash': 35, 'smash': 35, 'breaking': 35, 'glass': 30,
            'fight': 40, 'punch': 40, 'hit': 35, 'bang': 35,
            'emergency': 35, 'distress': 40, 'panic': 40
        }

        violence_score = 0
        detected_sounds = []
        reasoning_parts = []

        # Check detected sounds against violence categories
        for result in results:
            label = result['label'].lower()
            score = result['score'] * 100

            # Check if label contains violence-related keywords
            for keyword, violence_weight in violence_sounds.items():
                if keyword in label:
                    weighted_score = (score * violence_weight) / 100
                    violence_score += weighted_score
                    detected_sounds.append(f"{label} ({score:.1f}%)")
                    reasoning_parts.append(f"Detected '{label}' with {score:.1f}% confidence")
                    break

        # Clean up temp audio file
        try:
            os.remove(audio_path)
        except:
            pass

        # Analyze audio features for additional violence indicators
        # Loudness analysis (violence often has high amplitude spikes)
        rms = librosa.feature.rms(y=audio)[0]
        loudness_spikes = np.sum(rms > np.mean(rms) + 2 * np.std(rms))

        if loudness_spikes > 10:
            violence_score += 20
            reasoning_parts.append(f"Detected {loudness_spikes} loud spikes (possible screams/impacts)")

        # Zero-crossing rate (measures noisiness - high for chaotic sounds)
        zcr = librosa.feature.zero_crossing_rate(audio)[0]
        if np.mean(zcr) > 0.15:
            violence_score += 15
            reasoning_parts.append(f"High audio chaos/noisiness detected")

        # Determine if violent
        is_violent = violence_score > 30 or len(detected_sounds) > 0

        if is_violent:
            final_confidence = min(violence_score + 20, 95.0)
            reasoning = ' | '.join(reasoning_parts) if reasoning_parts else 'Violence-related sounds detected'

            return {
                'class': 'Violence',
                'confidence': max(final_confidence, 60.0),
                'reasoning': reasoning,
                'detected_sounds': detected_sounds[:5],  # Top 5
                'violence_score': violence_score
            }
        else:
            return {
                'class': 'Non-Violence',
                'confidence': max(100 - violence_score, 60.0),
                'reasoning': 'No significant violence-related sounds detected',
                'detected_sounds': [],
                'violence_score': violence_score
            }

    except Exception as e:
        print(f"Audio analysis error: {e}")
        import traceback
        traceback.print_exc()
        return {
            'class': 'Error',
            'confidence': 0,
            'error': str(e),
            'reasoning': f'Audio analysis failed: {str(e)}'
        }


@app.route('/')
def index():
    """Render React-style modern UI"""
    return render_template('react_style.html')

@app.route('/old')
def old_index():
    """Render old UI"""
    return render_template('index.html')


@app.route('/predict', methods=['POST'])
def predict():
    """Main prediction endpoint"""
    try:
        results = {
            'success': False,
            'video_prediction': None,
            'audio_prediction': None,
            'text_prediction': None,
            'fused_prediction': None,
            'message': ''
        }

        # Process video
        video_file = request.files.get('video')
        if video_file and video_file.filename:
            filename = secure_filename(video_file.filename)
            video_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            video_file.save(video_path)

            results['video_prediction'] = analyze_video_content(video_path)
            results['audio_prediction'] = analyze_audio_content(video_path)

        # Process text
        text_input = request.form.get('text', '')
        if text_input:
            results['text_prediction'] = analyze_text_content(text_input)

        # Create fused prediction (include audio now)
        predictions = [
            results['video_prediction'],
            results['audio_prediction'],
            results['text_prediction']
        ]
        valid_predictions = [p for p in predictions if p and p.get('class') != 'Error']

        if valid_predictions:
            violence_count = sum(1 for p in valid_predictions if p['class'] == 'Violence')
            avg_confidence = np.mean([p['confidence'] for p in valid_predictions])

            if violence_count > len(valid_predictions) / 2:
                results['fused_prediction'] = {
                    'class': 'Violence',
                    'confidence': avg_confidence
                }
            else:
                results['fused_prediction'] = {
                    'class': 'Non-Violence',
                    'confidence': avg_confidence
                }

        results['success'] = True
        results['message'] = 'Analysis completed using pretrained models'

        return jsonify(results)

    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Error: {str(e)}'
        }), 500


@app.route('/predict_text', methods=['POST'])
def predict_text():
    """Text-only prediction with detailed reasoning"""
    try:
        data = request.get_json()
        text = data.get('text', '')

        if not text:
            return jsonify({'success': False, 'message': 'No text provided'}), 400

        result = analyze_text_content(text)

        # Return all fields including reasoning
        response = {
            'success': True,
            'prediction': result['class'],
            'confidence': result['confidence']
        }

        # Add reasoning fields if present
        if 'reasoning' in result:
            response['reasoning'] = result['reasoning']
        if 'keywords_found' in result:
            response['keywords_found'] = result['keywords_found']
        if 'ml_score' in result:
            response['ml_score'] = result['ml_score']

        return jsonify(response)

    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500


@app.route('/predict_video', methods=['POST'])
def predict_video():
    """Video-only prediction with detailed reasoning"""
    try:
        if 'video' not in request.files:
            return jsonify({'success': False, 'message': 'No video provided'}), 400

        video_file = request.files['video']
        filename = secure_filename(video_file.filename)
        video_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        video_file.save(video_path)

        result = analyze_video_content(video_path)

        # Return all fields including reasoning
        response = {
            'success': True,
            'prediction': result['class'],
            'confidence': result['confidence'],
            'video_path': filename
        }

        # Add reasoning fields if present
        if 'reasoning' in result:
            response['reasoning'] = result['reasoning']
        if 'violent_frames' in result:
            response['violent_frames'] = result['violent_frames']
        if 'avg_score' in result:
            response['avg_score'] = result['avg_score']
        if 'max_score' in result:
            response['max_score'] = result['max_score']
        if 'total_frames_analyzed' in result:
            response['total_frames_analyzed'] = result['total_frames_analyzed']

        return jsonify(response)

    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500


if __name__ == '__main__':
    print("Initializing Violence Detection System (Pretrained Models)...")
    load_pretrained_models()
    print("Starting Flask server...")
    app.run(debug=True, host='0.0.0.0', port=5001)
