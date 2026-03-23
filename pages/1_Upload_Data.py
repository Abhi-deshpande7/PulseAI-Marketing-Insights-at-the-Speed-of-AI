import streamlit as st
import pandas as pd
from pipeline import compute_metrics, detect_anomalies, segment_summary, channel_summary
from insights import generate_insight
import plotly.express as px

st.set_page_config(page_title="Upload Data", layout="wide")
st.title("Upload Your Campaign Data")
st.markdown("Upload a CSV file with your own campaign metrics.")

st.divider()

# Show expected format
with st.expander("Expected CSV Format"):
    sample = pd.DataFrame({
        "campaign_name": ["Summer Sale", "New Launch"],
        "channel": ["Email", "Push"],
        "segment": ["New Users", "High Value"],
        "date": ["2026-01-01", "2026-01-05"],
        "sent": [50000, 30000],
        "opens": [11000, 7500],
        "clicks": [2500, 1800],
        "conversions": [300, 450]
    })
    st.dataframe(sample, use_container_width=True)
    st.caption("Your CSV must have these exact column names.")

uploaded_file = st.file_uploader("Upload CSV", type=["csv"])

if uploaded_file:
    try:
        df = pd.read_csv(uploaded_file)

        required_cols = ["campaign_name", "channel", "segment",
                         "date", "sent", "opens", "clicks", "conversions"]
        missing = [c for c in required_cols if c not in df.columns]

        if missing:
            st.error(f"Missing columns: {', '.join(missing)}")
        else:
            df = compute_metrics(df)
            df = detect_anomalies(df)

            st.success(f"Loaded {len(df)} campaigns successfully.")
            st.divider()

            # KPIs
            st.subheader("Overall Performance")
            k1, k2, k3, k4 = st.columns(4)
            k1.metric("Avg Open Rate", f"{df['open_rate'].mean():.1%}")
            k2.metric("Avg CTR",       f"{df['ctr'].mean():.1%}")
            k3.metric("Avg CVR",       f"{df['cvr'].mean():.1%}")
            k4.metric("Anomalies",     int(df["is_anomaly"].sum()))

            st.divider()

            col1, col2 = st.columns(2)
            with col1:
                st.subheader("Performance by Channel")
                ch = channel_summary(df)
                fig = px.bar(ch, x="channel",
                             y=["avg_open_rate", "avg_ctr", "avg_cvr"],
                             barmode="group",
                             color_discrete_sequence=["#1a9e75", "#5bc4a0", "#aee8d2"])
                st.plotly_chart(fig, use_container_width=True)

            with col2:
                st.subheader("Performance by Segment")
                seg = segment_summary(df)
                fig2 = px.bar(seg, x="segment",
                              y=["avg_open_rate", "avg_ctr", "avg_cvr"],
                              barmode="group",
                              color_discrete_sequence=["#1a9e75", "#5bc4a0", "#aee8d2"])
                st.plotly_chart(fig2, use_container_width=True)

            st.divider()

            # Anomaly table
            st.subheader("Flagged Anomalies")
            anomalies = df[df["is_anomaly"]][
                ["campaign_name", "channel", "segment", "open_rate", "ctr", "cvr"]
            ].copy()
            anomalies["open_rate"] = anomalies["open_rate"].map("{:.1%}".format)
            anomalies["ctr"]       = anomalies["ctr"].map("{:.1%}".format)
            anomalies["cvr"]       = anomalies["cvr"].map("{:.1%}".format)
            st.dataframe(anomalies, use_container_width=True)

            st.divider()

            # AI Insight
            st.subheader("AI-Generated Insight")
            api_key = st.text_input("Anthropic API Key", type="password")
            if api_key:
                if st.button("Generate Insight"):
                    with st.spinner("Analyzing..."):
                        ch_str = channel_summary(df)[
                            ["channel", "avg_open_rate", "avg_ctr", "avg_cvr"]
                        ].to_string(index=False)
                        anomaly_list = df[df["is_anomaly"]]["campaign_name"].tolist()[:5]
                        insight = generate_insight(api_key, ch_str, anomaly_list)
                        st.success(insight)
            else:
                st.info("Enter your Anthropic API key to generate insights.")

    except Exception as e:
        st.error(f"Error reading file: {e}")
else:
    st.info("Please upload a CSV file to get started.")