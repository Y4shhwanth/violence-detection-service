"""
Enriched policy documents for RAG-based policy matching.
Expanded from utils/policy_engine.py with richer text for better semantic retrieval.
"""

POLICY_DOCUMENTS = [
    {
        'id': 'violence-policy',
        'title': 'Platform Violence Policy',
        'sections': [
            {
                'section': '1.1 - Prohibited Violent Content',
                'text': (
                    'Content that depicts, promotes, or glorifies acts of physical '
                    'violence against individuals or groups is strictly prohibited. '
                    'This includes but is not limited to: assault, battery, fighting, '
                    'torture, and any form of physical harm. Real-world violence footage, '
                    'including street fights, domestic violence, and organized violence, '
                    'falls under this policy. Content showing injuries, bruises, or wounds '
                    'resulting from violence is also covered.'
                ),
            },
            {
                'section': '1.2 - Graphic Violence Exceptions',
                'text': (
                    'Educational, documentary, or newsworthy content depicting violence '
                    'may be permitted with appropriate content warnings and age-gating. '
                    'Such content must not glorify or promote the violent acts depicted. '
                    'Examples include: historical documentaries about war, news coverage '
                    'of conflicts, educational material about self-defense, and medical '
                    'training content showing injuries for educational purposes.'
                ),
            },
            {
                'section': '1.3 - Enforcement Actions',
                'text': (
                    'Violations result in content removal and escalating account actions: '
                    'first offense receives a warning, second offense results in temporary '
                    'suspension (7-30 days), third offense leads to permanent account '
                    'termination. Severe violations (e.g., content depicting murder, '
                    'torture, or terrorism) result in immediate permanent ban and referral '
                    'to law enforcement.'
                ),
            },
        ],
    },
    {
        'id': 'community-safety',
        'title': 'Community Safety Policy',
        'sections': [
            {
                'section': '2.1 - Safe Environment Standards',
                'text': (
                    'All users are expected to maintain a respectful and safe environment. '
                    'Content that creates a hostile, intimidating, or threatening atmosphere '
                    'is subject to moderation and removal. This includes content depicting '
                    'real-world violence, dangerous activities, self-harm, or harmful behavior. '
                    'Bullying, harassment, and cyberstalking through violent content are '
                    'strictly prohibited.'
                ),
            },
            {
                'section': '2.2 - User Reporting and Response',
                'text': (
                    'Reports of violent or threatening content are reviewed within 24 hours. '
                    'Content posing imminent danger to individuals is escalated immediately '
                    'to the Trust & Safety team and, where appropriate, law enforcement. '
                    'Users who report content in good faith are protected from retaliation. '
                    'Repeated false reports may result in reporting privileges being restricted.'
                ),
            },
        ],
    },
    {
        'id': 'hate-speech',
        'title': 'Hate Speech Policy',
        'sections': [
            {
                'section': '3.1 - Prohibited Hate Content',
                'text': (
                    'Content that attacks, demeans, or incites violence against individuals '
                    'or groups based on protected characteristics is strictly prohibited. '
                    'Protected characteristics include: race, ethnicity, national origin, '
                    'religion, gender identity, sexual orientation, disability, age, and '
                    'veteran status. This includes slurs, dehumanizing language, stereotypes, '
                    'and conspiracy theories targeting protected groups.'
                ),
            },
            {
                'section': '3.2 - Hate-Motivated Violence',
                'text': (
                    'Content depicting or promoting violence motivated by hatred toward '
                    'protected groups is treated with maximum severity. Such content is '
                    'immediately removed and the account is permanently suspended. '
                    'Cases may be referred to law enforcement. This includes content '
                    'promoting genocide, ethnic cleansing, mass shootings targeting specific '
                    'groups, and supremacist violence.'
                ),
            },
        ],
    },
    {
        'id': 'threat-escalation',
        'title': 'Threat Escalation Policy',
        'sections': [
            {
                'section': '4.1 - Direct Threats',
                'text': (
                    'Any content containing direct, credible threats of violence against '
                    'specific individuals or groups is immediately escalated to the highest '
                    'priority review queue. This includes threats to kill, harm, injure, '
                    'or physically attack someone. Threats made in any format (text, audio, '
                    'video, or symbolic gestures) are covered under this policy.'
                ),
            },
            {
                'section': '4.2 - Escalation Protocol',
                'text': (
                    'Severity levels for threats: Level 1 (vague/indirect) — content review '
                    'within 4 hours. Level 2 (specific target named) — immediate review and '
                    'potential law enforcement notification. Level 3 (imminent danger with '
                    'means and timeline specified) — immediate law enforcement contact, '
                    'account suspension, and content preservation for evidence.'
                ),
            },
        ],
    },
    {
        'id': 'graphic-content',
        'title': 'Graphic Content Policy',
        'sections': [
            {
                'section': '5.1 - Graphic Visual Content',
                'text': (
                    'Content depicting graphic violence, gore, severe injuries, or death '
                    'is prohibited unless it serves a clearly educational or newsworthy '
                    'purpose. Gratuitous depictions of blood, wounds, corpses, or '
                    'dismemberment are always removed. This includes real and realistic '
                    'CGI/AI-generated graphic violence.'
                ),
            },
            {
                'section': '5.2 - Disturbing Audio Content',
                'text': (
                    'Audio content capturing real violence — including screams of pain, '
                    'gunshots, explosions, sounds of physical assault, or distress calls — '
                    'is subject to the same restrictions as visual content. Such audio must '
                    'be flagged for review. This includes audio from real incidents as well '
                    'as realistic synthetic audio depicting violence.'
                ),
            },
            {
                'section': '5.3 - Content Warning Requirements',
                'text': (
                    'Permitted graphic content (educational/news) must include prominent '
                    'content warnings, be age-gated to 18+, and must not appear in '
                    'recommendation feeds or public listings without explicit user opt-in. '
                    'Content warnings must describe the nature of the graphic content '
                    '(e.g., "Contains footage of real violence" or "Graphic injury images").'
                ),
            },
        ],
    },
    {
        'id': 'weapons-policy',
        'title': 'Weapons Policy',
        'sections': [
            {
                'section': '6.1 - Weapons Display and Promotion',
                'text': (
                    'Content promoting illegal weapons, showing weapons being used to '
                    'threaten or harm others, or providing instructions for creating '
                    'weapons or explosives is prohibited. This includes firearms, bladed '
                    'weapons, explosives, and improvised weapons. Legal weapons content '
                    '(hunting, sport shooting, historical) requires context and safety '
                    'messaging.'
                ),
            },
            {
                'section': '6.2 - Weapons in Context',
                'text': (
                    'Weapons shown in educational, historical, sporting, or artistic '
                    'contexts may be permitted if they do not promote violence, include '
                    'appropriate safety messaging, and are not used to threaten others. '
                    'Law enforcement and military training content is generally permitted '
                    'with appropriate context.'
                ),
            },
        ],
    },
]
