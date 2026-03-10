import Anthropic from '@anthropic-ai/sdk';
import { config } from './config.js';
import { analyzeContentTool, executeAnalyzeContent } from './tools/analyzeContent.js';
import { explainDecisionTool, executeExplainDecision } from './tools/explainDecision.js';
import { queryPolicyTool, executeQueryPolicy } from './tools/queryPolicy.js';
import { getRiskScoreTool, executeGetRiskScore } from './tools/getRiskScore.js';

const client = new Anthropic({
  apiKey: config.anthropicApiKey,
});

const SYSTEM_PROMPT = `You are an expert content moderation agent specializing in multimodal violence detection. You help moderators understand and act on content analysis results.

Your capabilities:
1. **Analyze Content**: Send text content for violence detection analysis
2. **Explain Decisions**: Ask the AI system why it made specific decisions, get evidence and policy references
3. **Query Policies**: Look up applicable content moderation policies for different types of violations
4. **Compute Risk Scores**: Calculate weighted risk scores from individual modality predictions

When a user asks you to analyze content:
- Use the analyze_content tool to get a risk assessment
- Interpret the results clearly, explaining what was detected and why
- Reference applicable policies using query_policy
- Provide actionable recommendations

When explaining decisions:
- Use explain_decision to get detailed explanations with evidence
- Present evidence in a structured, easy-to-understand format
- Always mention confidence levels and severity

Be concise, professional, and prioritize safety. Always err on the side of caution when content is ambiguous.`;

const tools = [analyzeContentTool, explainDecisionTool, queryPolicyTool, getRiskScoreTool];

type ToolInput = Record<string, unknown>;

async function executeTool(name: string, input: ToolInput): Promise<string> {
  switch (name) {
    case 'analyze_content':
      return executeAnalyzeContent(input as { text: string });
    case 'explain_decision':
      return executeExplainDecision(input as { question: string; analysis_data?: Record<string, unknown> });
    case 'query_policy':
      return executeQueryPolicy(input as { query: string; violation_type?: string });
    case 'get_risk_score':
      return executeGetRiskScore(input as {
        video_confidence: number;
        audio_confidence: number;
        text_confidence: number;
        video_weight?: number;
        audio_weight?: number;
        text_weight?: number;
      });
    default:
      return JSON.stringify({ error: `Unknown tool: ${name}` });
  }
}

export async function runAgent(userMessage: string): Promise<string> {
  const messages: Anthropic.MessageParam[] = [
    { role: 'user', content: userMessage },
  ];

  let finalResponse = '';

  // Agentic loop
  while (true) {
    const response = await client.messages.create({
      model: config.model,
      max_tokens: 4096,
      system: SYSTEM_PROMPT,
      tools: tools as Anthropic.Tool[],
      messages,
    });

    // Collect text blocks
    const textBlocks = response.content
      .filter((block): block is Anthropic.TextBlock => block.type === 'text')
      .map(block => block.text);

    if (textBlocks.length > 0) {
      finalResponse = textBlocks.join('\n');
    }

    // Check for tool use
    const toolUseBlocks = response.content.filter(
      (block): block is Anthropic.ToolUseBlock => block.type === 'tool_use'
    );

    if (toolUseBlocks.length === 0 || response.stop_reason === 'end_turn') {
      break;
    }

    // Execute tools and add results
    messages.push({ role: 'assistant', content: response.content });

    const toolResults: Anthropic.ToolResultBlockParam[] = [];
    for (const toolUse of toolUseBlocks) {
      console.log(`[Agent] Calling tool: ${toolUse.name}`);
      const result = await executeTool(toolUse.name, toolUse.input as ToolInput);
      toolResults.push({
        type: 'tool_result',
        tool_use_id: toolUse.id,
        content: result,
      });
    }

    messages.push({ role: 'user', content: toolResults });
  }

  return finalResponse;
}

// CLI entrypoint
async function main() {
  const userInput = process.argv.slice(2).join(' ');

  if (!userInput) {
    console.log('Usage: npm start -- "Analyze this text for violence"');
    console.log('       npm start -- "What policies apply to fighting content?"');
    process.exit(0);
  }

  if (!config.anthropicApiKey) {
    console.error('Error: ANTHROPIC_API_KEY environment variable is required');
    process.exit(1);
  }

  console.log('[Agent] Processing request...\n');
  const result = await runAgent(userInput);
  console.log(result);
}

main().catch(console.error);
