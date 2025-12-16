"""Prompt templates for Gemini AI operations."""

SENTIMENT_ANALYSIS_PROMPT = """
Analyze the sentiment of the following customer support messages.
For each message, determine:
1. Sentiment score (-1.0 to 1.0, where -1 is very negative, 0 is neutral, 1 is very positive)
2. Sentiment label (positive, negative, neutral)
3. Sentiment magnitude (0.0 to 1.0, indicating intensity)

Messages:
{messages}

Return a JSON object with this structure:
{{
    "messages": [
        {{
            "index": 0,
            "sentiment_score": 0.5,
            "sentiment_label": "positive",
            "sentiment_magnitude": 0.7,
            "key_phrases": ["helpful", "appreciate"]
        }}
    ],
    "summary": {{
        "average_score": 0.3,
        "trend": "improving",
        "dominant_sentiment": "positive",
        "key_themes": ["support quality", "response time"]
    }}
}}

Important:
- Be objective and accurate in your assessment
- Consider context and tone, not just keywords
- Identify key phrases that drive the sentiment
- The trend should be "improving", "declining", or "stable"
"""

HEALTH_SCORE_PROMPT = """
Calculate a customer health score for the following customer based on their communication patterns and sentiment.

Customer: {customer_name}
Company: {company}
Messages Analyzed: {message_count}
Average Sentiment: {avg_sentiment}
Sentiment Trend: {sentiment_trend}

Recent Messages:
{recent_messages}

Calculate a health score from 1-10 based on:
- Overall sentiment (weight: 30%)
- Engagement level (weight: 20%)
- Issue resolution indicators (weight: 25%)
- Communication tone consistency (weight: 15%)
- Response patterns (weight: 10%)

Return a JSON object:
{{
    "score": 7,
    "components": {{
        "sentiment_score": 7,
        "engagement_score": 8,
        "issue_resolution_score": 6,
        "tone_consistency_score": 7,
        "response_pattern_score": 8
    }},
    "reasoning": "Brief explanation of the score...",
    "positive_signals": ["Regular engagement", "Constructive feedback"],
    "warning_signals": ["Recent complaints about X"],
    "confidence": 0.85
}}

Important:
- Score should reflect true customer satisfaction and relationship health
- Be specific in your reasoning
- Consider both explicit feedback and implicit signals
- A score of 1-3 indicates high risk, 4-6 moderate, 7-10 healthy
"""

CHURN_PREDICTION_PROMPT = """
Predict the churn probability for the following customer based on their health score patterns.

Customer: {customer_name}
Current Health Score: {current_score}/10
Score History:
{score_history}
Account Tenure: {tenure_days} days

Analyze patterns and predict churn risk:

Return a JSON object:
{{
    "churn_probability": 0.25,
    "risk_level": "low",
    "contributing_factors": [
        "Declining health score trend",
        "Reduced engagement frequency"
    ],
    "protective_factors": [
        "Long account tenure",
        "Recent positive interactions"
    ],
    "predicted_timeframe": "30-60 days",
    "confidence": 0.75
}}

Important:
- risk_level must be one of: "low", "medium", "high", "critical"
- churn_probability should be between 0.0 and 1.0
- Consider both recent trends and historical patterns
- Account tenure is a significant protective factor
- Be realistic - not every unhappy moment leads to churn
"""

ACTION_ITEMS_PROMPT = """
Generate actionable suggestions to improve the customer health score.

Customer: {customer_name}
Current Health Score: {health_score}/10
Weak Areas: {weak_areas}
Recent Issues:
{recent_issues}

Generate 3-5 specific, actionable items that the customer success team can take to improve this customer's health score and reduce churn risk.

Return a JSON object:
{{
    "action_items": [
        {{
            "title": "Schedule a check-in call",
            "description": "Detailed description of the action and why it's important...",
            "priority": "high",
            "category": "engagement",
            "impact_score": 8,
            "effort_score": 3,
            "suggested_timeline": "Within 1 week",
            "success_metrics": ["Improved sentiment", "Issue resolution"]
        }}
    ],
    "overall_strategy": "Brief strategic recommendation..."
}}

Important:
- priority must be one of: "critical", "high", "medium", "low"
- category must be one of: "engagement", "support", "relationship", "technical", "billing"
- impact_score (1-10): how much this action could improve the health score
- effort_score (1-10): how much effort/resources required (1=easy, 10=very difficult)
- Be specific and actionable - avoid vague suggestions
- Prioritize high-impact, low-effort actions
- Consider the customer's specific situation
"""
