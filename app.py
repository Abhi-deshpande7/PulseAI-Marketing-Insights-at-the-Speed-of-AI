import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
import io
from datetime import datetime

from data_generator import generate_campaigns
from pipeline import compute_metrics, detect_anomalies, segment_summary, channel_summary, build_context_summary
from insights import generate_insight, chat_with_data, explain_anomaly
from forecasting import (run_forecast, forecast_all_channels,
                         forecast_summary_stats, generate_forecast_insight, METRICS)
from budget_optimizer import allocate_budget, compute_channel_efficiency, generate_budget_insight
from report_generator import build_pdf_report
from report_generator import build_pdf_report

# ─── Page config ────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="PulseAI · Marketing Intelligence",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ─── Custom CSS ─────────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@300;400;500;600;700&family=Space+Mono:wght@400;700&display=swap');

html, body, [class*="css"] {
    font-family: 'DM Sans', sans-serif;
}

/* Dark sidebar */
[data-testid="stSidebar"] {
    background: #0d0f14;
    border-right: 1px solid #1e2230;
}
[data-testid="stSidebar"] * { color: #c8cdd8 !important; }
[data-testid="stSidebar"] .stMarkdown h2 {
    color: #00e5a0 !important;
    font-family: 'Space Mono', monospace;
    font-size: 0.75rem;
    letter-spacing: 0.15em;
    text-transform: uppercase;
}

/* Main bg */
[data-testid="stAppViewContainer"] { background: #080a0f; }
[data-testid="stMainBlockContainer"] { padding-top: 1.5rem; }

/* Header */
.pulse-header {
    display: flex;
    align-items: baseline;
    gap: 0.6rem;
    margin-bottom: 0.2rem;
}
.pulse-logo {
    font-family: 'Space Mono', monospace;
    font-size: 2rem;
    font-weight: 700;
    color: #00e5a0;
    letter-spacing: -0.02em;
}
.pulse-sub {
    font-size: 0.9rem;
    color: #555e70;
    letter-spacing: 0.04em;
}

/* Metric cards */
.metric-card {
    background: #10131c;
    border: 1px solid #1e2230;
    border-radius: 12px;
    padding: 1.1rem 1.4rem;
    position: relative;
    overflow: hidden;
}
.metric-card::before {
    content: '';
    position: absolute;
    top: 0; left: 0; right: 0;
    height: 2px;
    background: linear-gradient(90deg, #00e5a0, #00b8d4);
}
.metric-label {
    font-size: 0.7rem;
    font-family: 'Space Mono', monospace;
    color: #555e70;
    text-transform: uppercase;
    letter-spacing: 0.12em;
}
.metric-value {
    font-size: 2rem;
    font-weight: 700;
    color: #eef0f5;
    line-height: 1.2;
    margin: 0.2rem 0;
}
.metric-delta {
    font-size: 0.75rem;
    color: #00e5a0;
}

/* Section headers */
.section-title {
    font-family: 'Space Mono', monospace;
    font-size: 0.72rem;
    color: #00e5a0;
    letter-spacing: 0.14em;
    text-transform: uppercase;
    margin-bottom: 0.8rem;
    padding-bottom: 0.4rem;
    border-bottom: 1px solid #1e2230;
}

/* Chat bubbles */
.chat-user {
    background: #1a2540;
    border: 1px solid #2a3554;
    border-radius: 12px 12px 2px 12px;
    padding: 0.8rem 1.1rem;
    margin: 0.5rem 0 0.5rem 3rem;
    color: #c8cdd8;
    font-size: 0.9rem;
}
.chat-ai {
    background: #0f1a14;
    border: 1px solid #1a3028;
    border-radius: 2px 12px 12px 12px;
    padding: 0.8rem 1.1rem;
    margin: 0.5rem 3rem 0.5rem 0;
    color: #c8cdd8;
    font-size: 0.9rem;
}
.chat-label {
    font-family: 'Space Mono', monospace;
    font-size: 0.6rem;
    letter-spacing: 0.1em;
    text-transform: uppercase;
    margin-bottom: 0.3rem;
}
.chat-label.user { color: #4a90d9; }
.chat-label.ai   { color: #00e5a0; }

/* Anomaly badge */
.anomaly-badge {
    display: inline-block;
    background: #3a1010;
    color: #ff6b6b;
    border: 1px solid #5a2020;
    border-radius: 6px;
    padding: 0.1rem 0.5rem;
    font-family: 'Space Mono', monospace;
    font-size: 0.65rem;
    letter-spacing: 0.05em;
}

/* Stale tab nav fix */
button[data-baseweb="tab"] {
    font-family: 'DM Sans', sans-serif !important;
    font-size: 0.85rem !important;
}
</style>
""", unsafe_allow_html=True)

# ─── Header ──────────────────────────────────────────────────────────────────
st.markdown("""
<div class="pulse-header">
  <span class="pulse-logo">⚡ PulseAI</span>
  <span class="pulse-sub">Marketing Intelligence Platform</span>
</div>
<p style="color:#555e70;font-size:0.82rem;margin-top:0;">
  Automated campaign analysis · Anomaly detection · AI-powered insights
</p>
""", unsafe_allow_html=True)

# ─── Sidebar ──────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("## ⚡ PulseAI")
    st.markdown("---")

    st.markdown("## 🔑 API Key")
    import os
    api_key = os.environ.get("GROQ_API_KEY", "")
    if not api_key:
        api_key = st.text_input("Groq API Key", type="password", placeholder="gsk_...")
    st.markdown("---")

    st.markdown("## 📂 Data Source")
    data_source = st.radio("", ["Use synthetic data", "Upload CSV"], label_visibility="collapsed")

    uploaded_file = None
    if data_source == "Upload CSV":
        uploaded_file = st.file_uploader(
            "Upload campaign CSV",
            type=["csv"],
            help="Columns needed: campaign_name, channel, segment, date, sent, opens, clicks, conversions, spend"
        )

    st.markdown("---")
    st.markdown("## 🎛️ Filters")

    channels_sel = st.multiselect(
        "Channel", ["Email", "Push", "SMS", "In-App"],
        default=["Email", "Push", "SMS", "In-App"]
    )
    segments_sel = st.multiselect(
        "Segment", ["New Users", "Power Users", "Dormant", "High Value"],
        default=["New Users", "Power Users", "Dormant", "High Value"]
    )

    if st.button("🔄 Regenerate Synthetic Data"):
        st.cache_data.clear()
        if "chat_history" in st.session_state:
            del st.session_state["chat_history"]
        st.rerun()

    st.markdown("---")
    st.markdown(
        "<p style='font-size:0.7rem;color:#333b4d;text-align:center;'>PulseAI v2.0 · AI Chat Layer</p>",
        unsafe_allow_html=True
    )

# ─── Data loading ────────────────────────────────────────────────────────────
@st.cache_data
def load_synthetic():
    df = generate_campaigns(100)
    df = compute_metrics(df)
    df = detect_anomalies(df)
    return df

def load_uploaded(file):
    df = pd.read_csv(file)
    df["date"] = pd.to_datetime(df["date"])
    # Auto-add campaign_id if not present
    if "campaign_id" not in df.columns:
        df.insert(0, "campaign_id", [f"C{i+1:04d}" for i in range(len(df))])
    # Auto-add campaign_name if not present
    if "campaign_name" not in df.columns:
        df.insert(1, "campaign_name", df["campaign_id"])
    df = compute_metrics(df)
    df = detect_anomalies(df)
    return df

if data_source == "Upload CSV" and uploaded_file:
    try:
        df_raw = load_uploaded(uploaded_file)
        st.sidebar.success(f"✅ Loaded {len(df_raw)} campaigns")
    except Exception as e:
        st.sidebar.error(f"Error loading CSV: {e}")
        df_raw = load_synthetic()
else:
    df_raw = load_synthetic()

df = df_raw[df_raw["channel"].isin(channels_sel) & df_raw["segment"].isin(segments_sel)].copy()

# Build AI context once (cached in session)
if "data_context" not in st.session_state or st.session_state.get("context_len") != len(df):
    st.session_state["data_context"] = build_context_summary(df)
    st.session_state["context_len"] = len(df)

data_context = st.session_state["data_context"]

# ─── Tabs ────────────────────────────────────────────────────────────────────
tab1, tab2, tab3, tab4, tab5, tab6, tab7 = st.tabs([
    "📊  Overview",
    "🚨  Anomalies",
    "🧠  AI Chat",
    "📈  Campaign Explorer",
    "🔮  Forecast",
    "💰  Budget Optimizer",
    "📄  Export Report",
])

# ═══════════════════════════════════════════════════════════════════════════════
# TAB 1 — OVERVIEW
# ═══════════════════════════════════════════════════════════════════════════════
with tab1:
    st.markdown('<p class="section-title">Overall KPIs</p>', unsafe_allow_html=True)

    avg_or = df["open_rate"].mean()
    avg_ctr = df["ctr"].mean()
    avg_cvr = df["cvr"].mean()
    avg_roas = df["roas"].mean()
    anomaly_count = int(df["is_anomaly"].sum())
    total_spend = df["spend"].sum()
    total_conv = df["conversions"].sum()

    c1, c2, c3, c4, c5 = st.columns(5)
    cards = [
        (c1, "AVG OPEN RATE",   f"{avg_or:.1%}",      ""),
        (c2, "AVG CTR",         f"{avg_ctr:.1%}",     ""),
        (c3, "AVG CVR",         f"{avg_cvr:.1%}",     ""),
        (c4, "AVG ROAS",        f"{avg_roas:.1f}x",   ""),
        (c5, "ANOMALIES",       str(anomaly_count),   ""),
    ]
    for col, label, val, delta in cards:
        col.markdown(f"""
        <div class="metric-card">
          <div class="metric-label">{label}</div>
          <div class="metric-value">{val}</div>
          <div class="metric-delta">{delta}&nbsp;</div>
        </div>""", unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    col_a, col_b = st.columns(2)
    COLORS = ["#00e5a0", "#00b8d4", "#4a90d9", "#a78bfa"]

    with col_a:
        st.markdown('<p class="section-title">Performance by Channel</p>', unsafe_allow_html=True)
        ch = channel_summary(df)
        fig = px.bar(
            ch, x="channel", y=["avg_open_rate", "avg_ctr", "avg_cvr"],
            barmode="group",
            labels={"value": "Rate", "channel": "Channel", "variable": "Metric"},
            color_discrete_sequence=COLORS,
        )
        fig.update_layout(
            paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
            font_color="#8892a4", legend_title_text="",
            margin=dict(l=0, r=0, t=10, b=0),
            xaxis=dict(gridcolor="#1e2230"), yaxis=dict(gridcolor="#1e2230"),
        )
        st.plotly_chart(fig, use_container_width=True)

    with col_b:
        st.markdown('<p class="section-title">Performance by Segment</p>', unsafe_allow_html=True)
        seg = segment_summary(df)
        fig2 = px.bar(
            seg, x="segment", y=["avg_open_rate", "avg_ctr", "avg_cvr"],
            barmode="group",
            labels={"value": "Rate", "segment": "Segment", "variable": "Metric"},
            color_discrete_sequence=COLORS,
        )
        fig2.update_layout(
            paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
            font_color="#8892a4", legend_title_text="",
            margin=dict(l=0, r=0, t=10, b=0),
            xaxis=dict(gridcolor="#1e2230"), yaxis=dict(gridcolor="#1e2230"),
        )
        st.plotly_chart(fig2, use_container_width=True)

    st.markdown('<p class="section-title">Open Rate Trend Over Time</p>', unsafe_allow_html=True)
    trend = df.groupby(["date", "channel"])["open_rate"].mean().reset_index()
    fig3 = px.line(
        trend, x="date", y="open_rate", color="channel",
        labels={"open_rate": "Avg Open Rate", "date": "Date"},
        color_discrete_sequence=COLORS,
    )
    fig3.update_layout(
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        font_color="#8892a4", legend_title_text="",
        margin=dict(l=0, r=0, t=10, b=0),
        xaxis=dict(gridcolor="#1e2230"), yaxis=dict(gridcolor="#1e2230"),
    )
    st.plotly_chart(fig3, use_container_width=True)

    # ROAS scatter
    st.markdown('<p class="section-title">Spend vs. ROAS by Channel</p>', unsafe_allow_html=True)
    fig4 = px.scatter(
        df, x="spend", y="roas", color="channel", size="conversions",
        hover_data=["campaign_name", "segment"],
        color_discrete_sequence=COLORS,
        labels={"spend": "Spend ($)", "roas": "ROAS"},
    )
    fig4.update_layout(
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        font_color="#8892a4", legend_title_text="",
        margin=dict(l=0, r=0, t=10, b=0),
        xaxis=dict(gridcolor="#1e2230"), yaxis=dict(gridcolor="#1e2230"),
    )
    st.plotly_chart(fig4, use_container_width=True)

    # One-shot AI insight
    st.markdown('<p class="section-title">AI-Generated Snapshot Insight</p>', unsafe_allow_html=True)
    if not api_key:
        st.info("🔑 Enter your Groq API Key in the sidebar to enable AI insights.")
    else:
        if st.button("⚡ Generate Snapshot Insight"):
            with st.spinner("Analysing campaign data…"):
                ch_str = channel_summary(df)[["channel","avg_open_rate","avg_ctr","avg_cvr"]].to_string(index=False)
                anomaly_list = df[df["is_anomaly"]]["campaign_name"].tolist()[:5]
                insight = generate_insight(api_key, ch_str, anomaly_list)
            st.markdown(
                f'<div style="background:#0f1a14;border:1px solid #1a3028;border-radius:10px;padding:1rem 1.2rem;color:#c8cdd8;font-size:0.88rem;line-height:1.7;">{insight}</div>',
                unsafe_allow_html=True
            )

# ═══════════════════════════════════════════════════════════════════════════════
# TAB 2 — ANOMALIES
# ═══════════════════════════════════════════════════════════════════════════════
with tab2:
    st.markdown('<p class="section-title">Flagged Anomaly Campaigns</p>', unsafe_allow_html=True)
    anomalies_df = df[df["is_anomaly"]].copy()

    if anomalies_df.empty:
        st.success("✅ No anomalies detected in the current filter set.")
    else:
        st.markdown(f"**{len(anomalies_df)} campaigns** flagged as statistical anomalies (Z-score > 2.5σ)")
        st.markdown("")

        for _, row in anomalies_df.iterrows():
            with st.expander(f"⚠️  {row['campaign_name']}  ·  {row['channel']}  ·  {row['segment']}"):
                mc1, mc2, mc3, mc4 = st.columns(4)
                mc1.metric("Open Rate", f"{row['open_rate']:.1%}")
                mc2.metric("CTR",       f"{row['ctr']:.1%}")
                mc3.metric("CVR",       f"{row['cvr']:.1%}")
                mc4.metric("ROAS",      f"{row['roas']:.1f}x")

                st.markdown(
                    f'<span class="anomaly-badge">ANOMALY · {row["anomaly_reason"]}</span>',
                    unsafe_allow_html=True
                )
                st.markdown("")

                if not api_key:
                    st.info("🔑 Add API key to enable AI root-cause analysis.")
                else:
                    btn_key = f"explain_{row.get('campaign_id', row.get('campaign_name', str(_)))}"
                    if st.button("🔍 Explain this anomaly with AI", key=btn_key):
                        with st.spinner("Diagnosing…"):
                            explanation = explain_anomaly(api_key, data_context, row.to_dict())
                        st.markdown(
                            f'<div style="background:#0f1a14;border:1px solid #1a3028;border-radius:8px;'
                            f'padding:0.8rem 1rem;color:#c8cdd8;font-size:0.85rem;line-height:1.7;">'
                            f'{explanation}</div>',
                            unsafe_allow_html=True
                        )

# ═══════════════════════════════════════════════════════════════════════════════
# TAB 3 — AI CHAT
# ═══════════════════════════════════════════════════════════════════════════════
with tab3:
    st.markdown('<p class="section-title">Chat with your campaign data</p>', unsafe_allow_html=True)

    if not api_key:
        st.warning("🔑 Enter your Groq API Key in the sidebar to start chatting.")
    else:
        # Init history
        if "chat_history" not in st.session_state:
            st.session_state["chat_history"] = []

        # Suggested starter questions
        if not st.session_state["chat_history"]:
            st.markdown("**Suggested questions to get started:**")
            starters = [
                "Which channel has the best ROAS?",
                "Why are there anomalies in Email campaigns?",
                "How do Power Users compare to Dormant users in CVR?",
                "What's my best performing segment and why?",
                "Where should I cut budget to improve efficiency?",
            ]
            cols = st.columns(3)
            for i, q in enumerate(starters):
                if cols[i % 3].button(q, key=f"starter_{i}"):
                    with st.spinner("Thinking…"):
                        reply = chat_with_data(api_key, data_context, [], q)
                    st.session_state["chat_history"].append({"role": "user", "content": q})
                    st.session_state["chat_history"].append({"role": "assistant", "content": reply})
                    st.rerun()

        # Render conversation
        for msg in st.session_state["chat_history"]:
            if msg["role"] == "user":
                st.markdown(
                    f'<div class="chat-user"><div class="chat-label user">You</div>{msg["content"]}</div>',
                    unsafe_allow_html=True
                )
            else:
                st.markdown(
                    f'<div class="chat-ai"><div class="chat-label ai">⚡ PulseAI</div>{msg["content"]}</div>',
                    unsafe_allow_html=True
                )

        # Input
        st.markdown("<br>", unsafe_allow_html=True)
        with st.form("chat_form", clear_on_submit=True):
            cols = st.columns([5, 1])
            user_input = cols[0].text_input(
                "Ask a question about your campaigns…",
                placeholder="e.g. Which channel should I increase budget for?",
                label_visibility="collapsed"
            )
            submitted = cols[1].form_submit_button("Send ➤")

        if submitted and user_input.strip():
            with st.spinner("PulseAI is thinking…"):
                reply = chat_with_data(
                    api_key,
                    data_context,
                    st.session_state["chat_history"],
                    user_input.strip(),
                )
            st.session_state["chat_history"].append({"role": "user", "content": user_input.strip()})
            st.session_state["chat_history"].append({"role": "assistant", "content": reply})
            st.rerun()

        # Clear chat button
        if st.session_state.get("chat_history"):
            if st.button("🗑️ Clear conversation"):
                st.session_state["chat_history"] = []
                st.rerun()

# ═══════════════════════════════════════════════════════════════════════════════
# TAB 4 — CAMPAIGN EXPLORER
# ═══════════════════════════════════════════════════════════════════════════════
with tab4:
    st.markdown('<p class="section-title">All Campaigns</p>', unsafe_allow_html=True)

    # Sortable table
    display_cols = ["campaign_name", "channel", "segment", "date",
                    "sent", "opens", "clicks", "conversions", "spend",
                    "open_rate", "ctr", "cvr", "roas", "is_anomaly"]
    explorer_df = df[display_cols].copy()
    explorer_df["date"] = explorer_df["date"].dt.strftime("%Y-%m-%d")
    explorer_df["open_rate"] = explorer_df["open_rate"].map("{:.1%}".format)
    explorer_df["ctr"]       = explorer_df["ctr"].map("{:.1%}".format)
    explorer_df["cvr"]       = explorer_df["cvr"].map("{:.1%}".format)
    explorer_df["roas"]      = explorer_df["roas"].map("{:.1f}x".format)
    explorer_df["spend"]     = explorer_df["spend"].map("${:,.0f}".format)

    search = st.text_input("🔍 Search campaigns", placeholder="Filter by name, channel, segment…")
    if search:
        mask = explorer_df.apply(lambda r: search.lower() in r.to_string().lower(), axis=1)
        explorer_df = explorer_df[mask]

    st.dataframe(
        explorer_df.rename(columns={
            "campaign_name": "Campaign", "channel": "Channel", "segment": "Segment",
            "date": "Date", "sent": "Sent", "opens": "Opens", "clicks": "Clicks",
            "conversions": "Conv.", "spend": "Spend", "open_rate": "Open Rate",
            "ctr": "CTR", "cvr": "CVR", "roas": "ROAS", "is_anomaly": "⚠️"
        }),
        use_container_width=True,
        height=500,
    )

    # CSV download
    csv_data = df[display_cols].to_csv(index=False).encode("utf-8")
    st.download_button(
        "⬇️ Download full dataset as CSV",
        data=csv_data,
        file_name="pulseai_campaigns.csv",
        mime="text/csv",
    )

# ═══════════════════════════════════════════════════════════════════════════════
# TAB 5 — FORECAST
# ═══════════════════════════════════════════════════════════════════════════════
with tab5:
    st.markdown('<p class="section-title">Performance Forecasting</p>', unsafe_allow_html=True)
    st.markdown("Predict future campaign performance using Prophet time-series forecasting.")
    st.markdown("")

    # ── Controls ──────────────────────────────────────────────────────────────
    fc1, fc2, fc3 = st.columns(3)
    with fc1:
        metric_choice = st.selectbox(
            "📐 Metric to forecast",
            options=list(METRICS.keys()),
            format_func=lambda k: METRICS[k],
        )
    with fc2:
        channel_choice = st.selectbox(
            "📡 Channel",
            options=["All"] + sorted(df["channel"].unique().tolist()),
        )
    with fc3:
        horizon = st.select_slider(
            "📅 Forecast horizon",
            options=[7, 14, 30, 60, 90],
            value=30,
        )

    run_btn = st.button("🔮 Run Forecast", type="primary")

    if run_btn:
        with st.spinner(f"Forecasting {METRICS[metric_choice]} for next {horizon} days…"):
            try:
                hist, fut = run_forecast(df, metric=metric_choice,
                                         channel=channel_choice, horizon_days=horizon)
                stats = forecast_summary_stats(fut, metric_choice)

                # ── KPI strip ─────────────────────────────────────────────────
                st.markdown("<br>", unsafe_allow_html=True)
                st.markdown('<p class="section-title">Forecast Summary</p>', unsafe_allow_html=True)

                kf1, kf2, kf3, kf4 = st.columns(4)
                kf1.markdown(f"""<div class="metric-card">
                    <div class="metric-label">TREND</div>
                    <div class="metric-value" style="font-size:1.4rem">{stats['trend']}</div>
                    <div class="metric-delta">&nbsp;</div></div>""", unsafe_allow_html=True)
                kf2.markdown(f"""<div class="metric-card">
                    <div class="metric-label">PREDICTED AVG</div>
                    <div class="metric-value">{stats['predicted_avg']}</div>
                    <div class="metric-delta">next {horizon} days</div></div>""", unsafe_allow_html=True)
                kf3.markdown(f"""<div class="metric-card">
                    <div class="metric-label">UPPER BOUND</div>
                    <div class="metric-value">{stats['predicted_high']}</div>
                    <div class="metric-delta">80% confidence</div></div>""", unsafe_allow_html=True)
                kf4.markdown(f"""<div class="metric-card">
                    <div class="metric-label">LOWER BOUND</div>
                    <div class="metric-value">{stats['predicted_low']}</div>
                    <div class="metric-delta">80% confidence</div></div>""", unsafe_allow_html=True)

                st.markdown("<br>", unsafe_allow_html=True)

                # ── Main forecast chart ───────────────────────────────────────
                st.markdown('<p class="section-title">Forecast Chart with Confidence Intervals</p>',
                            unsafe_allow_html=True)

                import plotly.graph_objects as go
                fig = go.Figure()

                # Confidence band
                fig.add_trace(go.Scatter(
                    x=pd.concat([fut["ds"], fut["ds"][::-1]]),
                    y=pd.concat([fut["yhat_upper"], fut["yhat_lower"][::-1]]),
                    fill="toself",
                    fillcolor="rgba(0,229,160,0.10)",
                    line=dict(color="rgba(255,255,255,0)"),
                    name="80% Confidence",
                    hoverinfo="skip",
                ))

                # Historical actuals
                fig.add_trace(go.Scatter(
                    x=hist["ds"], y=hist["y"],
                    mode="lines+markers",
                    name="Historical",
                    line=dict(color="#4a90d9", width=2),
                    marker=dict(size=4),
                ))

                # Historical fitted
                fig.add_trace(go.Scatter(
                    x=hist["ds"], y=hist["yhat"],
                    mode="lines",
                    name="Model Fit",
                    line=dict(color="#4a90d9", width=1, dash="dot"),
                ))

                # Forecast line
                fig.add_trace(go.Scatter(
                    x=fut["ds"], y=fut["yhat"],
                    mode="lines",
                    name=f"{horizon}-day Forecast",
                    line=dict(color="#00e5a0", width=2.5),
                ))

                # Vertical divider
                split_date = hist["ds"].max()
                fig.add_vline(
                    x=split_date.timestamp() * 1000,
                    line_width=1, line_dash="dash",
                    line_color="#555e70",
                    annotation_text="  Forecast starts",
                    annotation_font_color="#555e70",
                )

                is_rate = metric_choice in ("open_rate", "ctr", "cvr")
                fig.update_layout(
                    paper_bgcolor="rgba(0,0,0,0)",
                    plot_bgcolor="rgba(0,0,0,0)",
                    font_color="#8892a4",
                    legend=dict(orientation="h", yanchor="bottom", y=1.02,
                                xanchor="right", x=1),
                    margin=dict(l=0, r=0, t=30, b=0),
                    xaxis=dict(gridcolor="#1e2230", title="Date"),
                    yaxis=dict(
                        gridcolor="#1e2230",
                        title=METRICS[metric_choice],
                        tickformat=".1%" if is_rate else ",.0f",
                    ),
                    hovermode="x unified",
                )
                st.plotly_chart(fig, use_container_width=True)

                # ── Per-channel comparison ────────────────────────────────────
                if channel_choice == "All":
                    st.markdown('<p class="section-title">Channel-by-Channel Forecast Comparison</p>',
                                unsafe_allow_html=True)

                    all_results = forecast_all_channels(df, metric=metric_choice, horizon_days=horizon)
                    COLORS = ["#00e5a0", "#00b8d4", "#4a90d9", "#a78bfa"]

                    fig2 = go.Figure()
                    for i, (ch_name, (ch_hist, ch_fut)) in enumerate(all_results.items()):
                        if ch_name == "All":
                            continue
                        color = COLORS[i % len(COLORS)]
                        fig2.add_trace(go.Scatter(
                            x=pd.concat([ch_hist["ds"], ch_fut["ds"]]),
                            y=pd.concat([ch_hist["y"], ch_fut["yhat"]]),
                            mode="lines",
                            name=ch_name,
                            line=dict(color=color, width=2),
                        ))
                        # Forecast portion dashed
                        fig2.add_trace(go.Scatter(
                            x=ch_fut["ds"], y=ch_fut["yhat"],
                            mode="lines",
                            showlegend=False,
                            line=dict(color=color, width=2, dash="dot"),
                        ))

                    fig2.add_vline(
                        x=split_date.timestamp() * 1000,
                        line_width=1, line_dash="dash", line_color="#555e70",
                    )
                    fig2.update_layout(
                        paper_bgcolor="rgba(0,0,0,0)",
                        plot_bgcolor="rgba(0,0,0,0)",
                        font_color="#8892a4",
                        margin=dict(l=0, r=0, t=10, b=0),
                        xaxis=dict(gridcolor="#1e2230"),
                        yaxis=dict(
                            gridcolor="#1e2230",
                            tickformat=".1%" if is_rate else ",.0f",
                        ),
                        hovermode="x unified",
                    )
                    st.plotly_chart(fig2, use_container_width=True)

                # ── AI Forecast Insight ───────────────────────────────────────
                st.markdown('<p class="section-title">AI Forecast Interpretation</p>',
                            unsafe_allow_html=True)

                if not api_key:
                    st.info("🔑 Enter your Groq API Key in the sidebar for AI forecast interpretation.")
                else:
                    with st.spinner("Interpreting forecast…"):
                        fi = generate_forecast_insight(
                            api_key, stats,
                            metric_label=METRICS[metric_choice],
                            channel=channel_choice,
                            horizon=horizon,
                        )
                    st.markdown(
                        f'<div style="background:#0f1a14;border:1px solid #1a3028;border-radius:10px;'
                        f'padding:1rem 1.2rem;color:#c8cdd8;font-size:0.88rem;line-height:1.7;">'
                        f'{fi}</div>',
                        unsafe_allow_html=True
                    )

                # ── Raw forecast table ────────────────────────────────────────
                with st.expander("📋 View raw forecast data"):
                    is_rate = metric_choice in ("open_rate", "ctr", "cvr")
                    fmt = lambda v: f"{v:.1%}" if is_rate else f"{v:,.2f}"
                    display_fut = fut[["ds", "yhat_lower", "yhat", "yhat_upper"]].copy()
                    display_fut["ds"] = display_fut["ds"].dt.strftime("%Y-%m-%d")
                    display_fut["yhat_lower"] = display_fut["yhat_lower"].map(fmt)
                    display_fut["yhat"]       = display_fut["yhat"].map(fmt)
                    display_fut["yhat_upper"] = display_fut["yhat_upper"].map(fmt)
                    display_fut.columns = ["Date", "Lower Bound", "Predicted", "Upper Bound"]
                    st.dataframe(display_fut, use_container_width=True, height=300)

            except ValueError as e:
                st.error(f"❌ {e}")
            except Exception as e:
                st.error(f"❌ Forecast error: {e}")
    else:
        # Placeholder when forecast hasn't been run yet
        st.markdown("""
        <div style="background:#10131c;border:1px solid #1e2230;border-radius:12px;
                    padding:3rem;text-align:center;color:#555e70;">
            <div style="font-size:3rem;margin-bottom:1rem">🔮</div>
            <div style="font-family:'Space Mono',monospace;font-size:0.8rem;
                        letter-spacing:0.1em;text-transform:uppercase;">
                Configure your forecast above and click Run Forecast
            </div>
            <div style="margin-top:0.8rem;font-size:0.82rem;">
                Powered by Meta Prophet · 80% confidence intervals · Per-channel breakdown
            </div>
        </div>
        """, unsafe_allow_html=True)
# ═══════════════════════════════════════════════════════════════════════════════
# TAB 6 — BUDGET OPTIMIZER
# ═══════════════════════════════════════════════════════════════════════════════
with tab6:
    st.markdown('<p class="section-title">AI-Powered Budget Optimizer</p>', unsafe_allow_html=True)
    st.markdown("Enter your total budget and get a data-driven allocation across channels — scored by ROAS, CVR, and cost efficiency.")
    st.markdown("")

    # ── Efficiency preview (always visible) ───────────────────────────────────
    eff_df = compute_channel_efficiency(df)

    st.markdown('<p class="section-title">Channel Efficiency Scores</p>', unsafe_allow_html=True)
    COLORS = ["#00e5a0", "#00b8d4", "#4a90d9", "#a78bfa"]

    score_cols = st.columns(len(eff_df))
    for i, row in eff_df.iterrows():
        score_pct = int(row["composite_score"] * 100)
        color = COLORS[i % len(COLORS)]
        score_cols[i].markdown(f"""
        <div class="metric-card">
          <div class="metric-label">{row['channel']}</div>
          <div class="metric-value" style="color:{color}">{score_pct}<span style="font-size:1rem">/100</span></div>
          <div class="metric-delta">ROAS {row['avg_roas']:.1f}x · CVR {row['avg_cvr']:.1%}</div>
        </div>""", unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # ── Controls ──────────────────────────────────────────────────────────────
    st.markdown('<p class="section-title">Configure Allocation</p>', unsafe_allow_html=True)
    bc1, bc2, bc3 = st.columns(3)

    with bc1:
        total_budget = st.number_input(
            "💵 Total Budget ($)",
            min_value=1000,
            max_value=10_000_000,
            value=50_000,
            step=1000,
            help="Your total marketing budget to allocate across channels",
        )
    with bc2:
        strategy = st.selectbox(
            "🎯 Allocation Strategy",
            options=["balanced", "aggressive", "conservative"],
            format_func=lambda s: {
                "balanced":     "⚖️  Balanced — follow the data",
                "aggressive":   "🚀 Aggressive — double down on winners",
                "conservative": "🛡️  Conservative — spread the risk",
            }[s],
        )
    with bc3:
        min_floor = st.slider(
            "📐 Minimum per channel (%)",
            min_value=0,
            max_value=20,
            value=5,
            help="No channel will receive less than this % of budget",
        )

    optimize_btn = st.button("💰 Optimise Budget", type="primary")

    if optimize_btn:
        with st.spinner("Crunching the numbers…"):
            alloc = allocate_budget(df, total_budget=total_budget,
                                    min_pct=min_floor / 100,
                                    strategy=strategy)

        st.markdown("<br>", unsafe_allow_html=True)
        st.markdown('<p class="section-title">Recommended Allocation</p>', unsafe_allow_html=True)

        # ── Allocation KPI cards ───────────────────────────────────────────────
        alloc_cols = st.columns(len(alloc))
        for i, row in alloc.iterrows():
            color = COLORS[i % len(COLORS)]
            alloc_cols[i].markdown(f"""
            <div class="metric-card">
              <div class="metric-label">{row['channel']}</div>
              <div class="metric-value" style="color:{color}">${row['recommended_spend']:,.0f}</div>
              <div class="metric-delta">{row['allocation_pct']:.1%} of budget</div>
            </div>""", unsafe_allow_html=True)

        st.markdown("<br>", unsafe_allow_html=True)

        # ── Charts side by side ────────────────────────────────────────────────
        ch_left, ch_right = st.columns(2)

        with ch_left:
            st.markdown('<p class="section-title">Budget Split</p>', unsafe_allow_html=True)
            fig_pie = px.pie(
                alloc,
                names="channel",
                values="recommended_spend",
                color_discrete_sequence=COLORS,
                hole=0.55,
            )
            fig_pie.update_layout(
                paper_bgcolor="rgba(0,0,0,0)",
                font_color="#8892a4",
                margin=dict(l=0, r=0, t=10, b=0),
                showlegend=True,
                legend=dict(orientation="h", yanchor="bottom", y=-0.15),
            )
            fig_pie.update_traces(textposition="outside", textinfo="percent+label")
            st.plotly_chart(fig_pie, use_container_width=True)

        with ch_right:
            st.markdown('<p class="section-title">Projected Conversions by Channel</p>',
                        unsafe_allow_html=True)
            fig_bar = px.bar(
                alloc,
                x="channel",
                y="projected_conversions",
                color="channel",
                color_discrete_sequence=COLORS,
                labels={"projected_conversions": "Projected Conversions", "channel": ""},
                text="projected_conversions",
            )
            fig_bar.update_traces(textposition="outside")
            fig_bar.update_layout(
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(0,0,0,0)",
                font_color="#8892a4",
                showlegend=False,
                margin=dict(l=0, r=0, t=10, b=0),
                xaxis=dict(gridcolor="#1e2230"),
                yaxis=dict(gridcolor="#1e2230"),
            )
            st.plotly_chart(fig_bar, use_container_width=True)

        # ── Detailed comparison table ──────────────────────────────────────────
        st.markdown('<p class="section-title">Full Breakdown</p>', unsafe_allow_html=True)
        display_alloc = alloc.copy()
        display_alloc["allocation_pct"]    = display_alloc["allocation_pct"].map("{:.1%}".format)
        display_alloc["recommended_spend"] = display_alloc["recommended_spend"].map("${:,.0f}".format)
        display_alloc["avg_roas"]          = display_alloc["avg_roas"].map("{:.2f}x".format)
        display_alloc["avg_cvr"]           = display_alloc["avg_cvr"].map("{:.1%}".format)
        display_alloc["cost_per_conv"]     = display_alloc["cost_per_conv"].map("${:.2f}".format)
        display_alloc["composite_score"]   = (display_alloc["composite_score"] * 100).map("{:.0f}/100".format)

        st.dataframe(
            display_alloc.rename(columns={
                "channel": "Channel",
                "composite_score": "Efficiency Score",
                "avg_roas": "Avg ROAS",
                "avg_cvr": "Avg CVR",
                "cost_per_conv": "Cost/Conv",
                "allocation_pct": "Allocation %",
                "recommended_spend": "Budget",
                "projected_conversions": "Projected Conv.",
            }),
            use_container_width=True,
            hide_index=True,
        )

        # ── Total projected ROI summary ────────────────────────────────────────
        total_proj_conv = alloc["projected_conversions"].sum()
        assumed_rev_per_conv = 50
        projected_revenue = total_proj_conv * assumed_rev_per_conv
        projected_roas = projected_revenue / total_budget if total_budget > 0 else 0

        st.markdown("<br>", unsafe_allow_html=True)
        rs1, rs2, rs3 = st.columns(3)
        rs1.markdown(f"""<div class="metric-card">
          <div class="metric-label">TOTAL BUDGET</div>
          <div class="metric-value">${total_budget:,.0f}</div>
          <div class="metric-delta">&nbsp;</div></div>""", unsafe_allow_html=True)
        rs2.markdown(f"""<div class="metric-card">
          <div class="metric-label">PROJECTED CONVERSIONS</div>
          <div class="metric-value">{total_proj_conv:,}</div>
          <div class="metric-delta">based on historical CPC</div></div>""", unsafe_allow_html=True)
        rs3.markdown(f"""<div class="metric-card">
          <div class="metric-label">PROJECTED ROAS</div>
          <div class="metric-value">{projected_roas:.1f}x</div>
          <div class="metric-delta">at $50 revenue/conversion</div></div>""", unsafe_allow_html=True)

        # ── AI Budget Insight ──────────────────────────────────────────────────
        st.markdown("<br>", unsafe_allow_html=True)
        st.markdown('<p class="section-title">AI Budget Recommendation</p>', unsafe_allow_html=True)

        if not api_key:
            st.info("🔑 Enter your Groq API Key in the sidebar for AI-powered budget advice.")
        else:
            with st.spinner("Claude is analysing your allocation…"):
                budget_insight = generate_budget_insight(
                    api_key, alloc, total_budget, strategy
                )
            st.markdown(
                f'<div style="background:#0f1a14;border:1px solid #1a3028;border-radius:10px;'
                f'padding:1rem 1.2rem;color:#c8cdd8;font-size:0.88rem;line-height:1.7;">'
                f'{budget_insight}</div>',
                unsafe_allow_html=True
            )

        # ── CSV export ────────────────────────────────────────────────────────
        st.markdown("<br>", unsafe_allow_html=True)
        csv_budget = alloc.to_csv(index=False).encode("utf-8")
        st.download_button(
            "⬇️ Download allocation as CSV",
            data=csv_budget,
            file_name=f"pulseai_budget_allocation_${int(total_budget):,}.csv",
            mime="text/csv",
        )

    else:
        st.markdown("""
        <div style="background:#10131c;border:1px solid #1e2230;border-radius:12px;
                    padding:3rem;text-align:center;color:#555e70;">
            <div style="font-size:3rem;margin-bottom:1rem">💰</div>
            <div style="font-family:'Space Mono',monospace;font-size:0.8rem;
                        letter-spacing:0.1em;text-transform:uppercase;">
                Enter your budget above and click Optimise Budget
            </div>
            <div style="margin-top:0.8rem;font-size:0.82rem;">
                Scored by ROAS · CVR · CTR · Cost per Conversion · 3 allocation strategies
            </div>
        </div>
        """, unsafe_allow_html=True)

# ═══════════════════════════════════════════════════════════════════════════════
# TAB 7 — PDF EXPORT REPORT
# ═══════════════════════════════════════════════════════════════════════════════
with tab7:
    st.markdown('<p class="section-title">Export Branded PDF Report</p>', unsafe_allow_html=True)
    st.markdown("Generate a professional, branded PDF report with all charts, KPIs, anomaly data, and AI insights — ready to share with stakeholders.")
    st.markdown("")

    # ── Report config ─────────────────────────────────────────────────────────
    st.markdown('<p class="section-title">Report Settings</p>', unsafe_allow_html=True)

    rc1, rc2 = st.columns(2)
    with rc1:
        author_name = st.text_input(
            "👤 Author / Prepared by",
            value="Marketing Team",
            placeholder="Your name or team name",
        )
    with rc2:
        include_ai = st.toggle(
            "🧠 Include AI Executive Summary",
            value=True if api_key else False,
            disabled=not api_key,
            help="Requires Groq API Key in sidebar",
        )

    # What's included preview
    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown('<p class="section-title">What\'s Included in the Report</p>', unsafe_allow_html=True)

    inc1, inc2, inc3 = st.columns(3)
    with inc1:
        st.markdown("""
        <div class="metric-card">
          <div class="metric-label">PAGE 1</div>
          <div style="color:#c8cdd8;font-size:0.85rem;margin-top:0.5rem;line-height:1.8;">
            ✅ Cover page with branding<br>
            ✅ Overall KPI strip<br>
            ✅ AI Executive Summary
          </div>
        </div>""", unsafe_allow_html=True)
    with inc2:
        st.markdown("""
        <div class="metric-card">
          <div class="metric-label">PAGES 2–3</div>
          <div style="color:#c8cdd8;font-size:0.85rem;margin-top:0.5rem;line-height:1.8;">
            ✅ Channel performance chart<br>
            ✅ Segment performance chart<br>
            ✅ Open rate trend chart
          </div>
        </div>""", unsafe_allow_html=True)
    with inc3:
        st.markdown("""
        <div class="metric-card">
          <div class="metric-label">PAGES 4–5</div>
          <div style="color:#c8cdd8;font-size:0.85rem;margin-top:0.5rem;line-height:1.8;">
            ✅ Flagged anomaly table<br>
            ✅ Full campaign data (top 30)<br>
            ✅ Branded back cover
          </div>
        </div>""", unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # ── Generate button ───────────────────────────────────────────────────────
    gen_col, _ = st.columns([1, 2])
    with gen_col:
        generate_pdf_btn = st.button("📄 Generate PDF Report", type="primary", use_container_width=True)

    if generate_pdf_btn:
        with st.spinner("Building your report — rendering charts and compiling pages…"):
            try:
                # Optionally get AI insight text
                insight_text = ""
                if include_ai and api_key:
                    from insights import generate_insight
                    ch_str = channel_summary(df)[["channel","avg_open_rate","avg_ctr","avg_cvr"]].to_string(index=False)
                    anomaly_list = df[df["is_anomaly"]]["campaign_name"].tolist()[:5]
                    insight_text = generate_insight(api_key, ch_str, anomaly_list)

                pdf_bytes = generate_report(
                    df=df,
                    channel_df=channel_summary(df),
                    segment_df=segment_summary(df),
                    anomalies_df=df[df["is_anomaly"]].copy(),
                    insight_text=insight_text,
                    author_name=author_name,
                )

                filename = f"PulseAI_Report_{datetime.now().strftime('%Y%m%d_%H%M')}.pdf"

                st.success(f"✅ Report generated successfully! **{len(pdf_bytes) // 1024} KB**")
                st.markdown("<br>", unsafe_allow_html=True)

                st.download_button(
                    label="⬇️ Download PDF Report",
                    data=pdf_bytes,
                    file_name=filename,
                    mime="application/pdf",
                    use_container_width=True,
                )

                st.markdown(
                    f'<p style="color:#555e70;font-size:0.78rem;text-align:center;margin-top:0.5rem;">'
                    f'File: {filename} · {len(pdf_bytes)//1024} KB · '
                    f'Generated {datetime.now().strftime("%d %b %Y %H:%M")}</p>',
                    unsafe_allow_html=True
                )

            except Exception as e:
                st.error(f"❌ PDF generation failed: {e}")
                st.info("Make sure `reportlab` and `kaleido` are installed: `pip install reportlab kaleido`")
    else:
        st.markdown("""
        <div style="background:#10131c;border:1px solid #1e2230;border-radius:12px;
                    padding:3rem;text-align:center;color:#555e70;">
            <div style="font-size:3rem;margin-bottom:1rem">📄</div>
            <div style="font-family:'Space Mono',monospace;font-size:0.8rem;
                        letter-spacing:0.1em;text-transform:uppercase;">
                Configure settings above and click Generate PDF Report
            </div>
            <div style="margin-top:0.8rem;font-size:0.82rem;">
                Multi-page · Branded · Charts embedded · AI insights included
            </div>
        </div>
        """, unsafe_allow_html=True)

# ═══════════════════════════════════════════════════════════════════════════════
# TAB 7 — PDF EXPORT REPORT
# ═══════════════════════════════════════════════════════════════════════════════
with tab7:
    st.markdown('<p class="section-title">Export Branded PDF Report</p>', unsafe_allow_html=True)
    st.markdown("Generate a complete, branded PDF with all charts, KPIs, anomaly table, and AI insight — ready to share with your team.")
    st.markdown("")

    # Options
    ep1, ep2 = st.columns(2)
    with ep1:
        author_name = st.text_input("👤 Your name (appears in report)", placeholder="e.g. Abhishek Deshpande")
    with ep2:
        include_ai  = st.checkbox("Include AI-generated insight in PDF", value=True)

    st.markdown("")

    # AI insight for PDF (generate fresh or use cached)
    pdf_insight = ""
    if include_ai and api_key:
        if st.button("⚡ Pre-generate AI Insight for PDF"):
            with st.spinner("Generating AI insight…"):
                from insights import generate_insight
                ch_str = channel_summary(df)[["channel","avg_open_rate","avg_ctr","avg_cvr"]].to_string(index=False)
                anomaly_list = df[df["is_anomaly"]]["campaign_name"].tolist()[:5]
                pdf_insight = generate_insight(api_key, ch_str, anomaly_list)
                st.session_state["pdf_insight"] = pdf_insight
            st.success("AI insight ready — it will be embedded in the PDF.")
        elif "pdf_insight" in st.session_state:
            pdf_insight = st.session_state["pdf_insight"]
            st.info("Using previously generated AI insight.")
    elif include_ai and not api_key:
        st.info("🔑 Add API key in the sidebar to include AI insight in the PDF.")

    st.markdown("")

    # Generate button
    gen_col, _ = st.columns([1, 3])
    generate_pdf = gen_col.button("📄 Generate PDF Report", type="primary")

    if generate_pdf:
        with st.spinner("Building your branded PDF report…"):
            try:
                pdf_bytes = build_pdf_report(
                    df=df,
                    channel_df=channel_summary(df),
                    segment_df=segment_summary(df),
                    anomalies_df=df[df["is_anomaly"]].copy(),
                    ai_insight=pdf_insight,
                    author_name=author_name or "PulseAI",
                )
                filename = f"PulseAI_Report_{datetime.now().strftime('%Y%m%d_%H%M')}.pdf"
                st.success(f"✅ Report generated! Click below to download.")
                st.download_button(
                    label="⬇️ Download PDF Report",
                    data=pdf_bytes,
                    file_name=filename,
                    mime="application/pdf",
                )
            except Exception as e:
                st.error(f"❌ PDF generation failed: {e}")
                st.info("Make sure `reportlab` and `kaleido` are installed:\n```\npip install reportlab kaleido\n```")
    else:
        # Preview of what will be in the report
        st.markdown('<p class="section-title">Report will include</p>', unsafe_allow_html=True)
        items = [
            ("📊", "Overall KPI summary", "Open Rate, CTR, CVR, ROAS, Total Spend, Conversions, Anomaly count"),
            ("📈", "Channel performance chart + table", "Bar chart and data table for all channels"),
            ("👥", "Segment performance chart", "Bar chart comparing all user segments"),
            ("📉", "Open Rate trend chart", "Time-series line chart by channel"),
            ("🚨", "Anomaly campaigns table", "Up to 10 flagged campaigns with reasons"),
            ("🧠", "AI-generated insight", "Claude's analysis embedded in the report (if API key provided)"),
        ]
        for icon, title, desc in items:
            st.markdown(
                f'<div style="background:#10131c;border:1px solid #1e2230;border-radius:8px;'
                f'padding:0.6rem 1rem;margin-bottom:0.4rem;display:flex;gap:0.8rem;">'
                f'<span style="font-size:1.2rem">{icon}</span>'
                f'<div><div style="color:#eef0f5;font-size:0.85rem;font-weight:600">{title}</div>'
                f'<div style="color:#555e70;font-size:0.78rem">{desc}</div></div></div>',
                unsafe_allow_html=True
            )
