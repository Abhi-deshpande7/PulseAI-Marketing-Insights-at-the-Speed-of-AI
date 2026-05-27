import anthropic


SYSTEM_PROMPT = """You are PulseAI, a senior marketing analytics assistant embedded in a campaign intelligence platform.

You have been given a structured summary of the user's marketing campaign data (channels, segments, KPIs, anomalies, spend, and conversions). 
Use ONLY this data to answer questions. Be concise, specific, and always cite numbers from the data when relevant.

Formatting rules:
- Use **bold** for key metrics and campaign names.
- Use short bullet points for lists.
- Never make up data not present in the context.
- If a question cannot be answered from the data, say so clearly and suggest what data would be needed.

Your tone is confident, analytical, and helpful — like a sharp data scientist on the marketing team."""


def generate_insight(api_key: str, channel_data: str, anomaly_campaigns: list) -> str:
    """Legacy one-shot insight for the Overview tab."""
    client = anthropic.Anthropic(api_key=api_key)
    prompt = f"""Based on the following campaign performance data, provide a brief analysis in 3 parts:

1. **Overall Performance Summary** (2 sentences)
2. **Key Concern** (1 specific pattern or anomaly and its likely cause)
3. **One Recommendation** for the next campaign

Channel Performance Data:
{channel_data}

Flagged Anomaly Campaigns:
{anomaly_campaigns}

Keep the response concise and business-friendly."""

    response = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=500,
        messages=[{"role": "user", "content": prompt}]
    )
    return response.content[0].text


def chat_with_data(api_key: str, data_context: str, conversation_history: list, user_message: str) -> str:
    """
    Multi-turn chat. 
    conversation_history: list of {"role": "user"|"assistant", "content": str}
    Returns the assistant reply string.
    """
    client = anthropic.Anthropic(api_key=api_key)

    # Inject data context into the first user turn so it's always in scope
    system_with_data = SYSTEM_PROMPT + f"\n\n--- LIVE DATA CONTEXT ---\n{data_context}\n--- END DATA CONTEXT ---"

    messages = conversation_history + [{"role": "user", "content": user_message}]

    response = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=800,
        system=system_with_data,
        messages=messages,
    )
    return response.content[0].text


def explain_anomaly(api_key: str, data_context: str, campaign_row: dict) -> str:
    """Deep-dive explanation for a single flagged campaign."""
    client = anthropic.Anthropic(api_key=api_key)

    prompt = f"""You are a marketing data analyst. Explain the anomaly for the following campaign:

Campaign: {campaign_row.get('campaign_name')}
Channel: {campaign_row.get('channel')} | Segment: {campaign_row.get('segment')}
Open Rate: {campaign_row.get('open_rate', 0):.1%} | CTR: {campaign_row.get('ctr', 0):.1%} | CVR: {campaign_row.get('cvr', 0):.1%}
Anomaly Reason: {campaign_row.get('anomaly_reason', 'Unknown')}

Overall dataset context:
{data_context}

Provide:
1. **Root cause hypothesis** — what likely caused this anomaly
2. **Impact assessment** — how much does this affect overall performance
3. **Immediate action** — one specific thing to do about it

Be specific. 3-4 sentences total."""

    response = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=400,
        messages=[{"role": "user", "content": prompt}]
    )
    return response.content[0].text