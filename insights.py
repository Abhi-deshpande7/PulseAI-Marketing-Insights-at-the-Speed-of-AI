import anthropic

def generate_insight(api_key, channel_data, anomaly_campaigns):
    client = anthropic.Anthropic(api_key=api_key)

    prompt = f"""
You are a senior marketing analyst. Based on the following campaign performance data,
provide a brief analysis in 3 parts:

1. Overall Performance Summary (2 sentences)
2. Key Concern (1 specific pattern or anomaly and its likely cause)
3. One Recommendation for the next campaign

Channel Performance Data:
{channel_data}

Flagged Anomaly Campaigns:
{anomaly_campaigns}

Keep the response concise and business-friendly.
"""

    response = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=400,
        messages=[{"role": "user", "content": prompt}]
    )
    return response.content[0].text