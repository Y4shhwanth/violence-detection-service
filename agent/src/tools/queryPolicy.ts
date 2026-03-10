import type { PolicyInfo } from '../types.js';

// Built-in policy database for quick lookups
const POLICIES: PolicyInfo[] = [
  {
    title: 'Physical Violence Policy',
    description: 'Content depicting real physical violence, assault, or battery against persons is prohibited. This includes fighting, hitting, kicking, or use of weapons against individuals.',
    category: 'violence',
    applicable_violations: ['physical_violence', 'assault', 'fighting', 'weapon_use'],
  },
  {
    title: 'Graphic Content Policy',
    description: 'Excessively graphic depictions of injuries, blood, or gore are prohibited. Content that glorifies or sensationalizes violence or its aftermath is not permitted.',
    category: 'graphic',
    applicable_violations: ['graphic_violence', 'gore', 'blood', 'injury'],
  },
  {
    title: 'Threatening Behavior Policy',
    description: 'Content containing threats of violence, intimidation, or incitement to harm others is prohibited. This includes verbal threats, menacing gestures, and calls to action.',
    category: 'threats',
    applicable_violations: ['threat', 'intimidation', 'incitement', 'verbal_abuse'],
  },
  {
    title: 'Self-Harm Policy',
    description: 'Content that depicts, promotes, or provides instructions for self-harm or suicide is prohibited. Supportive and educational content in appropriate contexts may be permitted.',
    category: 'self_harm',
    applicable_violations: ['self_harm', 'suicide', 'self_injury'],
  },
  {
    title: 'Audio Violence Policy',
    description: 'Audio content containing sounds of violence (gunshots, screaming, explosions) or verbal threats and violent speech is subject to review. Context is considered in assessment.',
    category: 'audio_violence',
    applicable_violations: ['gunshot', 'explosion', 'screaming', 'violent_speech'],
  },
  {
    title: 'Contextual Safety Policy',
    description: 'Content is evaluated in context. News reporting, educational content, documentary footage, and artistic expression may be given different consideration while maintaining safety standards.',
    category: 'context',
    applicable_violations: ['contextual_review'],
  },
];

export const queryPolicyTool = {
  name: 'query_policy' as const,
  description: 'Look up content moderation policies by content type or violation category. Returns applicable policy details including titles, descriptions, and which violation types they cover.',
  input_schema: {
    type: 'object' as const,
    properties: {
      query: {
        type: 'string' as const,
        description: 'The type of content or violation to look up policies for (e.g., "physical violence", "audio threats", "graphic content")',
      },
      violation_type: {
        type: 'string' as const,
        description: 'Optional: specific violation type to match against (e.g., "fighting", "gunshot")',
      },
    },
    required: ['query'] as const,
  },
};

export async function executeQueryPolicy(input: {
  query: string;
  violation_type?: string;
}): Promise<string> {
  const query = input.query.toLowerCase();
  const violationType = input.violation_type?.toLowerCase();

  const matchedPolicies = POLICIES.filter(policy => {
    // Match by category or description
    if (policy.category.includes(query) || policy.description.toLowerCase().includes(query) || policy.title.toLowerCase().includes(query)) {
      return true;
    }
    // Match by violation type
    if (violationType && policy.applicable_violations.some(v => v.includes(violationType) || violationType.includes(v))) {
      return true;
    }
    // Fuzzy match on applicable violations
    return policy.applicable_violations.some(v => query.includes(v) || v.includes(query));
  });

  if (matchedPolicies.length === 0) {
    return JSON.stringify({
      message: 'No specific policies found for this query. The general Contextual Safety Policy applies.',
      policies: [POLICIES[POLICIES.length - 1]],
    }, null, 2);
  }

  return JSON.stringify({
    query: input.query,
    matched_policies: matchedPolicies,
    total_matches: matchedPolicies.length,
  }, null, 2);
}
