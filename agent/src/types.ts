export interface AnalysisResult {
  success: boolean;
  final_decision: 'Violation' | 'Verified' | 'Review Required';
  confidence: number;
  message: string;
  fused_prediction: {
    class: string;
    confidence: number;
    fusion_method: string;
    modality_weights: Record<string, number>;
  };
  video_prediction?: ModalityPrediction;
  audio_prediction?: ModalityPrediction;
  text_prediction?: ModalityPrediction;
  violations: Violation[];
  risk_score?: RiskScore;
  severity?: SeverityInfo;
  structured_explanation?: Explanation;
  processing_time_ms?: number;
}

export interface ModalityPrediction {
  class: string;
  confidence: number;
  reasoning?: string;
  violent_frames?: ViolentFrame[];
}

export interface Violation {
  modality: 'video' | 'audio' | 'text';
  type: string;
  severity: string;
  confidence: number;
  reason: string;
  start_seconds?: number;
  end_seconds?: number;
  start_time?: string;
  end_time?: string;
  sentence_index?: number;
  sentence?: string;
  peak_score?: number;
  keywords?: string[];
  detected_sounds?: string[];
}

export interface ViolentFrame {
  frame_number: number;
  timestamp: string;
  score: number;
  indicators: string[];
  reasoning: string;
  ml_detection?: string;
  ml_score?: number;
}

export interface RiskScore {
  violence_probability: number;
  severity: string;
  risk_level: string;
  recommendation: string;
  modality_scores: Record<string, number>;
  contributing_factors: Array<{ description: string; impact: string }>;
  risk_color: string;
}

export interface SeverityInfo {
  severity_score: number;
  severity_label: string;
}

export interface Explanation {
  summary: string;
  risk_level: string;
  why_flagged: string;
  compliance_suggestion: string;
  keywords: string[];
  top_factors: string[];
}

export interface AskAnalysisResponse {
  answer: string;
  question_type: string;
  evidence_frames: Array<{
    type: string;
    timestamp?: string;
    score?: number;
    modality?: string;
    reason?: string;
    time_range?: string;
  }>;
  policies: Array<{
    title: string;
    description?: string;
  }>;
}

export interface PolicyInfo {
  title: string;
  description: string;
  category: string;
  applicable_violations: string[];
}
