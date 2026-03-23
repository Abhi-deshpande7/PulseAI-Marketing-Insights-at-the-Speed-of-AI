import streamlit as st
import anthropic
from data_generator import generate_campaigns
from pipeline import compute_metrics, detect_anomalies

st.set_page_config(page_title="Ask Your Data", layout="wide")
st.title("Ask Your Data")
st.markdown("Type any question about your campaign data and get an instant AI answer.")
st.divider()

@st.cache_data
def load_data():
    df = generate_campaigns(100)
    df = compute_metrics(df)
    df = detect_anomalies(df)
    return df

df = load_data()

api_key = st.sidebar.text_input("Anthropic API Key", type="password")

st.subheader("Example Questions")
c1, c2, c3 = st.columns(3)
with c1:
    if st.button("Which channel performed best?"):
        st.session_state.query = "Which channel performed best overall?"
with c2:
    if st.button("Why are there anomalies?"):
        st.session_state.query = "Why are there anomaly campaigns and what caused them?"
with c3:
    if st.button("Best segment to target?"):
        st.session_state.query = "Which customer segment should I target for maximum conversions?"

query = st.text_input(
    "Or type your own question:",
    value=st.session_state.get("query", ""),
    placeholder="e.g. Which channel had the highest CTR last month?"
)

if st.button("Get Answer") and query:
    if not api_key:
        st.warning("Please enter your Anthropic API key in the sidebar.")
    else:
        with st.spinner("Analysing your data..."):
            data_summary = df.groupby("channel").agg(
                avg_open_rate=("open_rate", "mean"),
                avg_ctr=("ctr", "mean"),
                avg_cvr=("cvr", "mean"),
                total_conversions=("conversions", "sum"),
                anomaly_count=("is_anomaly", "sum")
            ).reset_index().to_string(index=False)

            segment_summary = df.groupby("segment").agg(
                avg_open_rate=("open_rate", "mean"),
                avg_ctr=("ctr", "mean"),
                avg_cvr=("cvr", "mean"),
                total_conversions=("conversions", "sum")
            ).reset_index().to_string(index=False)

            prompt = f"""
You are a senior marketing data analyst. Answer the following question 
based on this campaign performance data. Be specific, data-driven, and concise.

Channel Performance:
{data_summary}

Segment Performance:
{segment_summary}

Question: {query}

Give a direct answer in 3-5 sentences with specific numbers from the data.
"""
            client = anthropic.Anthropic(api_key=api_key)
            response = client.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=300,
                messages=[{"role": "user", "content": prompt}]
            )
            st.success(response.content[0].text)