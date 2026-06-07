from groq import Groq

SYSTEM_PROMPT = """You are PulseAI, a senior marketing analytics assistant.
You have been given a structured summary of the user campaign data.
Use ONLY this data to answer questions. Be concise and always cite numbers.
Use **bold** for key metrics. Use short bullet points for lists."""


def generate_insight(api_key, channel_data, anomaly_campaigns):
    client = Groq(api_key=api_key)
    prompt = f"""Based on the following campaign data, provide a brief analysis in 3 parts:

1. **Overall Performance Summary** (2 sentences)
2. **Key Concern** (1 specific pattern or anomaly and its likely cause)
3. **One Recommendation** for the next campaign

Channel Performance Data:
{channel_data}

Flagged Anomaly Campaigns:
{anomaly_campaigns}

Keep the response concise and business-friendly."""

    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        max_tokens=500,
        messages=[{"role": "user", "content": prompt}]
    )
    return response.choices[0].message.content


def chat_with_data(api_key, data_context, conversation_history, user_message):
    client = Groq(api_key=api_key)
    system_with_data = SYSTEM_PROMPT + f"\n\n--- LIVE DATA CONTEXT ---\n{data_context}\n--- END DATA CONTEXT ---"
    messages = [{"role": "system", "content": system_with_data}]
    messages += conversation_history
    messages.append({"role": "user", "content": user_message})
    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        max_tokens=800,
        messages=messages,
    )
    return response.choices[0].message.content


def explain_anomaly(api_key, data_context, campaign_row):
    client = Groq(api_key=api_key)
    prompt = f"""You are a marketing data analyst. Explain the anomaly for this campaign:

Campaign: {campaign_row.get("campaign_name")}
Channel: {campaign_row.get("channel")} | Segment: {campaign_row.get("segment")}
Open Rate: {campaign_row.get("open_rate", 0):.1%} | CTR: {campaign_row.get("ctr", 0):.1%} | CVR: {campaign_row.get("cvr", 0):.1%}
Anomaly Reason: {campaign_row.get("anomaly_reason", "Unknown")}

Overall dataset context:
{data_context}

Provide:
1. **Root cause hypothesis**
2. **Impact assessment**
3. **Immediate action**

Be specific. 3-4 sentences total."""

    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        max_tokens=400,
        messages=[{"role": "user", "content": prompt}]
    )
    return response.choices[0].message.content


def generate_forecast_insight(api_key, stats, metric_label, channel, horizon):
    client = Groq(api_key=api_key)
    prompt = f"""You are a marketing analyst. Interpret this {horizon}-day forecast.

Metric: {metric_label}
Channel: {channel}
Trend: {stats["trend"]}
Predicted average: {stats["predicted_avg"]}
Range: {stats["predicted_low"]} to {stats["predicted_high"]}

Provide:
1. **What this forecast means** (1-2 sentences)
2. **One proactive action** to take
3. **One risk** to watch out for"""

    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        max_tokens=350,
        messages=[{"role": "user", "content": prompt}]
    )
    return response.choices[0].message.content
