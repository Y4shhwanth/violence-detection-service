export const getRiskScoreTool = {
  name: 'get_risk_score' as const,
  description: 'Compute a weighted risk score from modality predictions. Mirrors the backend risk computation logic. Use this to understand how different modalities contribute to the overall risk assessment.',
  input_schema: {
    type: 'object' as const,
    properties: {
      video_confidence: {
        type: 'number' as const,
        description: 'Video modality violence confidence (0-100)',
      },
      audio_confidence: {
        type: 'number' as const,
        description: 'Audio modality violence confidence (0-100)',
      },
      text_confidence: {
        type: 'number' as const,
        description: 'Text modality violence confidence (0-100)',
      },
      video_weight: {
        type: 'number' as const,
        description: 'Weight for video modality (default 0.5)',
      },
      audio_weight: {
        type: 'number' as const,
        description: 'Weight for audio modality (default 0.3)',
      },
      text_weight: {
        type: 'number' as const,
        description: 'Weight for text modality (default 0.2)',
      },
    },
    required: ['video_confidence', 'audio_confidence', 'text_confidence'] as const,
  },
};

export async function executeGetRiskScore(input: {
  video_confidence: number;
  audio_confidence: number;
  text_confidence: number;
  video_weight?: number;
  audio_weight?: number;
  text_weight?: number;
}): Promise<string> {
  const weights = {
    video: input.video_weight ?? 0.5,
    audio: input.audio_weight ?? 0.3,
    text: input.text_weight ?? 0.2,
  };

  // Normalize weights
  const totalWeight = weights.video + weights.audio + weights.text;
  const normalizedWeights = {
    video: weights.video / totalWeight,
    audio: weights.audio / totalWeight,
    text: weights.text / totalWeight,
  };

  // Weighted risk score
  const riskScore =
    input.video_confidence * normalizedWeights.video +
    input.audio_confidence * normalizedWeights.audio +
    input.text_confidence * normalizedWeights.text;

  // Severity classification
  let severity: string;
  let risk_level: string;
  let risk_color: string;

  if (riskScore >= 90) {
    severity = 'Critical';
    risk_level = 'Critical';
    risk_color = '#dc2626';
  } else if (riskScore >= 70) {
    severity = 'High';
    risk_level = 'High';
    risk_color = '#f97316';
  } else if (riskScore >= 40) {
    severity = 'Moderate';
    risk_level = 'Moderate';
    risk_color = '#eab308';
  } else {
    severity = 'Low';
    risk_level = 'Low';
    risk_color = '#22c55e';
  }

  // Contributing factors
  const factors = [];
  if (input.video_confidence > 70) factors.push({ description: 'High video violence confidence', impact: 'high' });
  if (input.audio_confidence > 70) factors.push({ description: 'High audio violence indicators', impact: 'high' });
  if (input.text_confidence > 70) factors.push({ description: 'High text violence signals', impact: 'high' });
  if (input.video_confidence > 40 && input.audio_confidence > 40) {
    factors.push({ description: 'Cross-modal violence correlation (video + audio)', impact: 'high' });
  }

  // Recommendation
  let recommendation: string;
  if (riskScore >= 70) {
    recommendation = 'Content should be reviewed immediately and likely removed or restricted.';
  } else if (riskScore >= 40) {
    recommendation = 'Content should be queued for human review before publication.';
  } else {
    recommendation = 'Content appears safe but continued monitoring is recommended.';
  }

  return JSON.stringify({
    violence_probability: Math.round(riskScore * 100) / 100,
    severity,
    risk_level,
    risk_color,
    recommendation,
    modality_scores: {
      video: input.video_confidence,
      audio: input.audio_confidence,
      text: input.text_confidence,
    },
    weights: normalizedWeights,
    contributing_factors: factors,
  }, null, 2);
}
