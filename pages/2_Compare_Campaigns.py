import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from data_generator import generate_campaigns
from pipeline import compute_metrics, detect_anomalies

st.set_page_config(page_title="Compare Campaigns", layout="wide")
st.title("Multi-Campaign Comparison")
st.markdown("Select any two campaigns and compare their performance side by side.")

st.divider()

@st.cache_data
def load_data():
    df = generate_campaigns(100)
    df = compute_metrics(df)
    df = detect_anomalies(df)
    return df

df = load_data()

campaign_names = df["campaign_name"].tolist()

col1, col2 = st.columns(2)
with col1:
    camp1 = st.selectbox("Select Campaign 1", campaign_names, index=0)
with col2:
    camp2 = st.selectbox("Select Campaign 2", campaign_names, index=1)

if camp1 == camp2:
    st.warning("Please select two different campaigns.")
else:
    st.divider()

    c1 = df[df["campaign_name"] == camp1].iloc[0]
    c2 = df[df["campaign_name"] == camp2].iloc[0]

    # Side by side metric cards
    st.subheader("Head to Head Comparison")

    m1, m2, m3 = st.columns(3)

    with m1:
        st.markdown("**Open Rate**")
        st.metric(camp1[:30], f"{c1['open_rate']:.1%}")
        st.metric(camp2[:30], f"{c2['open_rate']:.1%}",
                  delta=f"{(c2['open_rate'] - c1['open_rate']):.1%}")

    with m2:
        st.markdown("**Click-Through Rate**")
        st.metric(camp1[:30], f"{c1['ctr']:.1%}")
        st.metric(camp2[:30], f"{c2['ctr']:.1%}",
                  delta=f"{(c2['ctr'] - c1['ctr']):.1%}")

    with m3:
        st.markdown("**Conversion Rate**")
        st.metric(camp1[:30], f"{c1['cvr']:.1%}")
        st.metric(camp2[:30], f"{c2['cvr']:.1%}",
                  delta=f"{(c2['cvr'] - c1['cvr']):.1%}")

    st.divider()

    # Bar chart comparison
    st.subheader("Performance Chart")
    compare_df = pd.DataFrame({
        "Metric": ["Open Rate", "CTR", "CVR", "Open Rate", "CTR", "CVR"],
        "Value":  [c1["open_rate"], c1["ctr"], c1["cvr"],
                   c2["open_rate"], c2["ctr"], c2["cvr"]],
        "Campaign": [camp1[:30]] * 3 + [camp2[:30]] * 3
    })
    fig = px.bar(compare_df, x="Metric", y="Value", color="Campaign",
                 barmode="group",
                 color_discrete_sequence=["#1a9e75", "#D85A30"])
    st.plotly_chart(fig, use_container_width=True)

    st.divider()

    # Campaign details table
    st.subheader("Campaign Details")
    details = pd.DataFrame({
        "Field": ["Channel", "Segment", "Sent", "Opens", "Clicks", "Conversions", "Anomaly Flagged"],
        camp1[:30]: [c1["channel"], c1["segment"],
                     f"{int(c1['sent']):,}", f"{int(c1['opens']):,}",
                     f"{int(c1['clicks']):,}", f"{int(c1['conversions']):,}",
                     "Yes" if c1["is_anomaly"] else "No"],
        camp2[:30]: [c2["channel"], c2["segment"],
                     f"{int(c2['sent']):,}", f"{int(c2['opens']):,}",
                     f"{int(c2['clicks']):,}", f"{int(c2['conversions']):,}",
                     "Yes" if c2["is_anomaly"] else "No"]
    })
    st.dataframe(details, use_container_width=True)

    st.divider()

    # Winner summary
    st.subheader("Performance Verdict")
    scores = {camp1: 0, camp2: 0}
    if c1["open_rate"] > c2["open_rate"]: scores[camp1] += 1
    else: scores[camp2] += 1
    if c1["ctr"] > c2["ctr"]: scores[camp1] += 1
    else: scores[camp2] += 1
    if c1["cvr"] > c2["cvr"]: scores[camp1] += 1
    else: scores[camp2] += 1

    winner = max(scores, key=scores.get)
    st.success(f"**{winner[:50]}** outperformed across {scores[winner]}/3 key metrics — Open Rate, CTR, and CVR.")