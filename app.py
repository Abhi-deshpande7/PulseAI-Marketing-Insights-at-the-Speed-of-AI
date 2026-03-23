import streamlit as st
import plotly.express as px
from data_generator import generate_campaigns
from pipeline import compute_metrics, detect_anomalies, segment_summary, channel_summary
from insights import generate_insight

st.set_page_config(page_title="Marketing Insight Generator", layout="wide")

st.title("AI-Powered Marketing Insight Generator")
st.markdown("Automated campaign analysis with anomaly detection and AI-generated insights.")
st.divider()

# Sidebar
st.sidebar.header("Filters")
api_key = st.sidebar.text_input("Anthropic API Key", type="password")
channels = st.sidebar.multiselect("Channel", ["Email", "Push", "SMS", "In-App"],
                                   default=["Email", "Push", "SMS", "In-App"])
segments = st.sidebar.multiselect("Segment", ["New Users", "Power Users", "Dormant", "High Value"],
                                   default=["New Users", "Power Users", "Dormant", "High Value"])

if st.sidebar.button("Regenerate Data"):
    st.cache_data.clear()

@st.cache_data
def load_data():
    df = generate_campaigns(100)
    df = compute_metrics(df)
    df = detect_anomalies(df)
    return df

df = load_data()
df_filtered = df[df["channel"].isin(channels) & df["segment"].isin(segments)]

# KPI Row
st.subheader("Overall Performance")
k1, k2, k3, k4 = st.columns(4)
k1.metric("Avg Open Rate", f"{df_filtered['open_rate'].mean():.1%}")
k2.metric("Avg CTR",       f"{df_filtered['ctr'].mean():.1%}")
k3.metric("Avg CVR",       f"{df_filtered['cvr'].mean():.1%}")
k4.metric("Anomalies Detected", int(df_filtered["is_anomaly"].sum()))

st.divider()

# Charts
col1, col2 = st.columns(2)

with col1:
    st.subheader("Performance by Channel")
    ch = channel_summary(df_filtered)
    fig = px.bar(ch, x="channel",
                 y=["avg_open_rate", "avg_ctr", "avg_cvr"],
                 barmode="group",
                 labels={"value": "Rate", "channel": "Channel"},
                 color_discrete_sequence=["#1a9e75", "#5bc4a0", "#aee8d2"])
    st.plotly_chart(fig, use_container_width=True)

with col2:
    st.subheader("Performance by Segment")
    seg = segment_summary(df_filtered)
    fig2 = px.bar(seg, x="segment",
                  y=["avg_open_rate", "avg_ctr", "avg_cvr"],
                  barmode="group",
                  labels={"value": "Rate", "segment": "Segment"},
                  color_discrete_sequence=["#1a9e75", "#5bc4a0", "#aee8d2"])
    st.plotly_chart(fig2, use_container_width=True)

st.subheader("Open Rate Trend Over Time")
trend = df_filtered.groupby(["date", "channel"])["open_rate"].mean().reset_index()
fig3 = px.line(trend, x="date", y="open_rate", color="channel",
               labels={"open_rate": "Avg Open Rate", "date": "Date"})
st.plotly_chart(fig3, use_container_width=True)

st.divider()

# Anomaly Table
st.subheader("Flagged Anomaly Campaigns")
anomalies = df_filtered[df_filtered["is_anomaly"]][
    ["campaign_name", "channel", "segment", "open_rate", "ctr", "cvr"]
].copy()
anomalies["open_rate"] = anomalies["open_rate"].map("{:.1%}".format)
anomalies["ctr"]       = anomalies["ctr"].map("{:.1%}".format)
anomalies["cvr"]       = anomalies["cvr"].map("{:.1%}".format)
st.dataframe(anomalies, use_container_width=True)

st.divider()

# AI Insight
st.subheader("AI-Generated Insight")
if not api_key:
    st.info("Enter your Anthropic API key in the sidebar to generate insights.")
else:
    if st.button("Generate Insight"):
        with st.spinner("Analyzing campaign data..."):
            ch_summary_str = channel_summary(df_filtered)[
                ["channel", "avg_open_rate", "avg_ctr", "avg_cvr"]
            ].to_string(index=False)
            anomaly_list = df_filtered[df_filtered["is_anomaly"]]["campaign_name"].tolist()[:5]
            insight = generate_insight(api_key, ch_summary_str, anomaly_list)
            st.success(insight)