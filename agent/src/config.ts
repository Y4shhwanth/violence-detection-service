export const config = {
  apiBaseUrl: process.env.API_BASE_URL || 'http://localhost:5001',
  anthropicApiKey: process.env.ANTHROPIC_API_KEY || '',
  model: 'claude-sonnet-4-6' as const,
} as const;
