import { config } from '../config.js';
import type { AskAnalysisResponse } from '../types.js';

export const explainDecisionTool = {
  name: 'explain_decision' as const,
  description: 'Ask the AI moderation system to explain its decision. Provides detailed explanation with evidence and applicable policies. Use this when you need to understand why content was flagged or verified.',
  input_schema: {
    type: 'object' as const,
    properties: {
      question: {
        type: 'string' as const,
        description: 'The question to ask about the analysis (e.g., "Why was this flagged?", "What evidence supports this decision?")',
      },
      analysis_data: {
        type: 'object' as const,
        description: 'Optional: the full analysis result object to ask about',
      },
    },
    required: ['question'] as const,
  },
};

export async function executeExplainDecision(input: {
  question: string;
  analysis_data?: Record<string, unknown>;
}): Promise<string> {
  try {
    const payload: Record<string, unknown> = { question: input.question };
    if (input.analysis_data) {
      payload.analysis_data = input.analysis_data;
    }

    const response = await fetch(`${config.apiBaseUrl}/ask-analysis`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    });

    if (!response.ok) {
      return JSON.stringify({ error: `API returned ${response.status}: ${response.statusText}` });
    }

    const result: AskAnalysisResponse = await response.json();

    return JSON.stringify({
      answer: result.answer,
      question_type: result.question_type,
      evidence: result.evidence_frames,
      policies: result.policies,
    }, null, 2);
  } catch (error) {
    return JSON.stringify({ error: `Failed to explain decision: ${(error as Error).message}` });
  }
}
