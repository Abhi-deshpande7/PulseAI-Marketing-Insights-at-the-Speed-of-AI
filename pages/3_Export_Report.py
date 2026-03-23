import streamlit as st
import pandas as pd
from fpdf import FPDF
from data_generator import generate_campaigns
from pipeline import compute_metrics, detect_anomalies, channel_summary, compute_health_score
import tempfile
import os

st.set_page_config(page_title="Export Report", layout="wide")
st.title("Export PDF Report")
st.markdown("Generate and download a full campaign performance report.")
st.divider()

@st.cache_data
def load_data():
    df = generate_campaigns(100)
    df = compute_metrics(df)
    df = detect_anomalies(df)
    df = compute_health_score(df)
    return df

df = load_data()

st.subheader("Report Preview")
st.dataframe(df[["campaign_name", "channel", "segment",
                  "open_rate", "ctr", "cvr",
                  "health_score", "health_label", "is_anomaly"]
               ].head(20), use_container_width=True)

st.divider()

if st.button("Generate PDF Report"):
    with st.spinner("Generating report..."):

        pdf = FPDF()
        pdf.add_page()
        pdf.set_font("Helvetica", "B", 16)
        pdf.cell(0, 10, "AI-Powered Marketing Insight Generator", ln=True, align="C")
        pdf.set_font("Helvetica", "", 11)
        pdf.cell(0, 8, "Campaign Performance Report", ln=True, align="C")
        pdf.ln(6)

        # Summary stats
        pdf.set_font("Helvetica", "B", 13)
        pdf.cell(0, 9, "Overall Performance Summary", ln=True)
        pdf.set_font("Helvetica", "", 11)
        pdf.cell(0, 7, f"Total Campaigns Analysed : {len(df)}", ln=True)
        pdf.cell(0, 7, f"Average Open Rate        : {df['open_rate'].mean():.1%}", ln=True)
        pdf.cell(0, 7, f"Average CTR              : {df['ctr'].mean():.1%}", ln=True)
        pdf.cell(0, 7, f"Average CVR              : {df['cvr'].mean():.1%}", ln=True)
        pdf.cell(0, 7, f"Anomalies Detected       : {int(df['is_anomaly'].sum())}", ln=True)
        pdf.ln(5)

        # Channel summary
        pdf.set_font("Helvetica", "B", 13)
        pdf.cell(0, 9, "Performance by Channel", ln=True)
        pdf.set_font("Helvetica", "B", 10)
        pdf.cell(50, 7, "Channel", border=1)
        pdf.cell(40, 7, "Open Rate", border=1)
        pdf.cell(40, 7, "CTR", border=1)
        pdf.cell(40, 7, "CVR", border=1, ln=True)
        pdf.set_font("Helvetica", "", 10)
        ch = channel_summary(df)
        for _, row in ch.iterrows():
            pdf.cell(50, 7, str(row["channel"]), border=1)
            pdf.cell(40, 7, f"{row['avg_open_rate']:.1%}", border=1)
            pdf.cell(40, 7, f"{row['avg_ctr']:.1%}", border=1)
            pdf.cell(40, 7, f"{row['avg_cvr']:.1%}", border=1, ln=True)
        pdf.ln(5)

        # Anomaly campaigns
        pdf.set_font("Helvetica", "B", 13)
        pdf.cell(0, 9, "Flagged Anomaly Campaigns", ln=True)
        pdf.set_font("Helvetica", "B", 10)
        pdf.cell(80, 7, "Campaign Name", border=1)
        pdf.cell(35, 7, "Channel", border=1)
        pdf.cell(35, 7, "Open Rate", border=1)
        pdf.cell(30, 7, "Health", border=1, ln=True)
        pdf.set_font("Helvetica", "", 10)
        anomalies = df[df["is_anomaly"]].head(10)
        for _, row in anomalies.iterrows():
            pdf.cell(80, 7, str(row["campaign_name"])[:40], border=1)
            pdf.cell(35, 7, str(row["channel"]), border=1)
            pdf.cell(35, 7, f"{row['open_rate']:.1%}", border=1)
            pdf.cell(30, 7, str(row["health_label"]), border=1, ln=True)

        # Save and download
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
            pdf.output(tmp.name)
            tmp_path = tmp.name

        with open(tmp_path, "rb") as f:
            st.download_button(
                label="Download PDF Report",
                data=f,
                file_name="marketing_insight_report.pdf",
                mime="application/pdf"
            )
        os.unlink(tmp_path)