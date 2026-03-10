import { config } from '../config.js';
import type { AnalysisResult } from '../types.js';

export const analyzeContentTool = {
  name: 'analyze_content' as const,
  description: 'Analyze text content for violence detection. Sends the text to the backend /predict_text endpoint and returns a risk assessment with confidence scores, severity, and detailed explanation.',
  input_schema: {
    type: 'object' as const,
    properties: {
      text: {
        type: 'string' as const,
        description: 'The text content to analyze for violence or harmful content',
      },
    },
    required: ['text'] as const,
  },
};

export async function executeAnalyzeContent(input: { text: string }): Promise<string> {
  try {
    const response = await fetch(`${config.apiBaseUrl}/predict_text`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ text: input.text }),
    });

    if (!response.ok) {
      return JSON.stringify({ error: `API returned ${response.status}: ${response.statusText}` });
    }

    const result: AnalysisResult = await response.json();

    return JSON.stringify({
      decision: result.final_decision,
      confidence: result.confidence,
      message: result.message,
      text_prediction: result.text_prediction,
      risk_score: result.risk_score,
      severity: result.severity,
      violations: result.violations,
      explanation: result.structured_explanation,
    }, null, 2);
  } catch (error) {
    return JSON.stringify({ error: `Failed to analyze content: ${(error as Error).message}` });
  }
}
