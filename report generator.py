import io
from datetime import datetime

import pandas as pd
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.gridspec import GridSpec

from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import mm
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.enums import TA_LEFT, TA_CENTER
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    Image, HRFlowable, PageBreak,
)

# ── Brand colours ──────────────────────────────────────────────────────────────
C_BG     = colors.HexColor("#080a0f")
C_CARD   = colors.HexColor("#10131c")
C_BORDER = colors.HexColor("#1e2230")
C_GREEN  = colors.HexColor("#00e5a0")
C_TEXT   = colors.HexColor("#c8cdd8")
C_MUTED  = colors.HexColor("#555e70")
C_WHITE  = colors.white

MPL_BG      = "#10131c"
MPL_GRID    = "#1e2230"
MPL_TEXT    = "#8892a4"
CHART_COLS  = ["#00e5a0", "#00b8d4", "#4a90d9", "#a78bfa"]

W, H   = A4
MARGIN = 18 * mm
AW     = W - 2 * MARGIN


# ── Styles ─────────────────────────────────────────────────────────────────────
def _styles():
    return {
        "title":   ParagraphStyle("title",   fontName="Helvetica-Bold", fontSize=26,
                                  textColor=C_WHITE,  leading=32),
        "subtitle":ParagraphStyle("subtitle",fontName="Helvetica",      fontSize=10,
                                  textColor=C_MUTED,  leading=14),
        "section": ParagraphStyle("section", fontName="Helvetica-Bold", fontSize=8,
                                  textColor=C_GREEN,  leading=12, spaceBefore=12, spaceAfter=5),
        "body":    ParagraphStyle("body",    fontName="Helvetica",      fontSize=9,
                                  textColor=C_TEXT,   leading=14),
        "kpi_val": ParagraphStyle("kpi_val", fontName="Helvetica-Bold", fontSize=18,
                                  textColor=C_WHITE,  leading=22, alignment=TA_CENTER),
        "kpi_lbl": ParagraphStyle("kpi_lbl", fontName="Helvetica-Bold", fontSize=7,
                                  textColor=C_MUTED,  leading=10, alignment=TA_CENTER),
        "kpi_dlt": ParagraphStyle("kpi_dlt", fontName="Helvetica",      fontSize=7,
                                  textColor=C_GREEN,  leading=10, alignment=TA_CENTER),
        "footer":  ParagraphStyle("footer",  fontName="Helvetica",      fontSize=7,
                                  textColor=C_MUTED,  leading=10, alignment=TA_CENTER),
        "insight": ParagraphStyle("insight", fontName="Helvetica",      fontSize=9,
                                  textColor=C_TEXT,   leading=15,
                                  leftIndent=8, rightIndent=8),
        "th":      ParagraphStyle("th",      fontName="Helvetica-Bold", fontSize=7,
                                  textColor=C_GREEN,  leading=10, alignment=TA_CENTER),
        "td":      ParagraphStyle("td",      fontName="Helvetica",      fontSize=8,
                                  textColor=C_TEXT,   leading=11, alignment=TA_CENTER),
    }


# ── Matplotlib helpers ─────────────────────────────────────────────────────────
def _mpl_setup(fig):
    fig.patch.set_facecolor(MPL_BG)
    for ax in fig.axes:
        ax.set_facecolor(MPL_BG)
        ax.tick_params(colors=MPL_TEXT, labelsize=7)
        ax.xaxis.label.set_color(MPL_TEXT)
        ax.yaxis.label.set_color(MPL_TEXT)
        ax.title.set_color(MPL_TEXT)
        for spine in ax.spines.values():
            spine.set_edgecolor(MPL_GRID)
        ax.grid(color=MPL_GRID, linewidth=0.5, alpha=0.7)
        ax.set_axisbelow(True)


def _fig_to_rl_image(fig, width_rl, height_mm=60):
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=150, bbox_inches="tight",
                facecolor=MPL_BG)
    plt.close(fig)
    buf.seek(0)
    return Image(buf, width=width_rl, height=height_mm * mm)


def _bar_chart(categories, series_dict, title="", height_mm=60, ylabel="Rate"):
    x  = np.arange(len(categories))
    n  = len(series_dict)
    bw = 0.7 / n
    fig, ax = plt.subplots(figsize=(7, 2.8))
    for i, (label, vals) in enumerate(series_dict.items()):
        ax.bar(x + i * bw - (n-1)*bw/2, vals,
               width=bw, label=label, color=CHART_COLS[i % len(CHART_COLS)],
               alpha=0.9, edgecolor="none")
    ax.set_xticks(x)
    ax.set_xticklabels(categories, fontsize=7)
    ax.set_ylabel(ylabel, fontsize=7)
    ax.legend(fontsize=6, facecolor=MPL_BG, edgecolor=MPL_GRID,
              labelcolor=MPL_TEXT, loc="upper right")
    _mpl_setup(fig)
    fig.tight_layout(pad=0.5)
    return _fig_to_rl_image(fig, AW, height_mm)


def _line_chart(df_grouped, x_col, y_col, color_col, title="", height_mm=65):
    fig, ax = plt.subplots(figsize=(7, 3))
    for i, (grp, gdf) in enumerate(df_grouped.groupby(color_col)):
        ax.plot(gdf[x_col], gdf[y_col], label=grp,
                color=CHART_COLS[i % len(CHART_COLS)], linewidth=1.5)
    ax.set_xlabel(x_col, fontsize=7)
    ax.set_ylabel(y_col, fontsize=7)
    ax.legend(fontsize=6, facecolor=MPL_BG, edgecolor=MPL_GRID,
              labelcolor=MPL_TEXT)
    _mpl_setup(fig)
    fig.tight_layout(pad=0.5)
    return _fig_to_rl_image(fig, AW, height_mm)


# ── ReportLab helpers ──────────────────────────────────────────────────────────
def _kpi_row(kpis, S):
    n  = len(kpis)
    cw = AW / n
    t  = Table(
        [[Paragraph(k["label"].upper(),  S["kpi_lbl"]) for k in kpis],
         [Paragraph(k["value"],          S["kpi_val"]) for k in kpis],
         [Paragraph(k.get("delta", ""), S["kpi_dlt"]) for k in kpis]],
        colWidths=[cw]*n, rowHeights=[9*mm, 13*mm, 7*mm],
    )
    t.setStyle(TableStyle([
        ("BACKGROUND",    (0,0),(-1,-1), C_CARD),
        ("BOX",           (0,0),(-1,-1), 0.5, C_BORDER),
        ("INNERGRID",     (0,0),(-1,-1), 0.3, C_BORDER),
        ("LINEABOVE",     (0,0),(-1, 0), 1.5, C_GREEN),
        ("TOPPADDING",    (0,0),(-1,-1), 5),
        ("BOTTOMPADDING", (0,0),(-1,-1), 5),
        ("VALIGN",        (0,0),(-1,-1), "MIDDLE"),
    ]))
    return t


def _data_tbl(df, S, col_map=None, max_rows=12):
    col_map = col_map or {}
    df   = df.head(max_rows)
    cols = list(df.columns)
    cw   = AW / len(cols)
    rows = [[Paragraph(col_map.get(c, c), S["th"]) for c in cols]]
    for _, r in df.iterrows():
        rows.append([Paragraph(str(r[c]), S["td"]) for c in cols])
    t = Table(rows, colWidths=[cw]*len(cols))
    t.setStyle(TableStyle([
        ("BACKGROUND",     (0,0),(-1, 0), C_CARD),
        ("ROWBACKGROUNDS", (0,1),(-1,-1), [C_BG, C_CARD]),
        ("BOX",            (0,0),(-1,-1), 0.4, C_BORDER),
        ("INNERGRID",      (0,0),(-1,-1), 0.2, C_BORDER),
        ("LINEBELOW",      (0,0),(-1, 0), 1,   C_GREEN),
        ("TOPPADDING",     (0,0),(-1,-1), 4),
        ("BOTTOMPADDING",  (0,0),(-1,-1), 4),
        ("VALIGN",         (0,0),(-1,-1), "MIDDLE"),
    ]))
    return t


def _dark_page(canvas, doc):
    canvas.saveState()
    canvas.setFillColor(C_BG)
    canvas.rect(0, 0, W, H, fill=1, stroke=0)
    canvas.setFillColor(C_GREEN)
    canvas.rect(0, H-3, W, 3, fill=1, stroke=0)
    canvas.setFillColor(C_MUTED)
    canvas.setFont("Helvetica", 7)
    canvas.drawCentredString(W/2, 10*mm,
        f"PulseAI Marketing Intelligence  |  "
        f"Generated {datetime.now().strftime('%d %b %Y %H:%M')}  |  Page {doc.page}")
    canvas.setStrokeColor(C_BORDER)
    canvas.line(MARGIN, 14*mm, W-MARGIN, 14*mm)
    canvas.restoreState()


# ── Main builder ───────────────────────────────────────────────────────────────
def build_pdf_report(df, channel_df, segment_df, anomalies_df,
                     ai_insight="", author_name="PulseAI"):
    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4,
                            leftMargin=MARGIN, rightMargin=MARGIN,
                            topMargin=22*mm, bottomMargin=22*mm,
                            title="PulseAI Campaign Report", author=author_name)
    S  = _styles()
    st = []

    # ── Header ────────────────────────────────────────────────────────────────
    st += [
        Spacer(1, 6*mm),
        Paragraph("PulseAI", S["title"]),
        Paragraph("Marketing Intelligence Report", S["subtitle"]),
        Spacer(1, 2*mm),
        Paragraph(
            f"Generated: {datetime.now().strftime('%d %B %Y, %H:%M')}  |  "
            f"Campaigns: {len(df)}  |  "
            f"Period: {df['date'].min().strftime('%d %b %Y')} - "
            f"{df['date'].max().strftime('%d %b %Y')}",
            S["subtitle"]),
        Spacer(1, 3*mm),
        HRFlowable(width=AW, thickness=1, color=C_GREEN, spaceAfter=5*mm),
    ]

    # ── KPIs ──────────────────────────────────────────────────────────────────
    st.append(Paragraph("OVERALL PERFORMANCE", S["section"]))
    st.append(_kpi_row([
        {"label":"Avg Open Rate",     "value": f"{df['open_rate'].mean():.1%}"},
        {"label":"Avg CTR",           "value": f"{df['ctr'].mean():.1%}"},
        {"label":"Avg CVR",           "value": f"{df['cvr'].mean():.1%}"},
        {"label":"Avg ROAS",          "value": f"{df['roas'].mean():.1f}x"},
        {"label":"Total Conversions", "value": f"{df['conversions'].sum():,}"},
        {"label":"Total Spend",       "value": f"${df['spend'].sum():,.0f}"},
        {"label":"Anomalies",         "value": str(int(df['is_anomaly'].sum())), "delta":"flagged"},
    ], S))
    st.append(Spacer(1, 5*mm))

    # ── Channel chart ──────────────────────────────────────────────────────────
    st.append(Paragraph("CHANNEL PERFORMANCE", S["section"]))
    st.append(_bar_chart(
        categories=channel_df["channel"].tolist(),
        series_dict={
            "Open Rate": channel_df["avg_open_rate"].tolist(),
            "CTR":       channel_df["avg_ctr"].tolist(),
            "CVR":       channel_df["avg_cvr"].tolist(),
        },
        height_mm=60,
    ))
    st.append(Spacer(1, 3*mm))

    ch_d = channel_df.copy()
    for c in ["avg_open_rate","avg_ctr","avg_cvr"]:
        ch_d[c] = ch_d[c].map("{:.1%}".format)
    ch_d["avg_roas"]    = ch_d["avg_roas"].map("{:.1f}x".format)
    ch_d["total_spend"] = ch_d["total_spend"].map("${:,.0f}".format)
    st.append(_data_tbl(
        ch_d[["channel","avg_open_rate","avg_ctr","avg_cvr","avg_roas","total_conversions","total_spend"]], S,
        col_map={"channel":"Channel","avg_open_rate":"Open Rate","avg_ctr":"CTR",
                 "avg_cvr":"CVR","avg_roas":"ROAS","total_conversions":"Conv.","total_spend":"Spend"}))
    st.append(Spacer(1, 5*mm))

    # ── Segment chart ──────────────────────────────────────────────────────────
    st.append(Paragraph("SEGMENT PERFORMANCE", S["section"]))
    st.append(_bar_chart(
        categories=segment_df["segment"].tolist(),
        series_dict={
            "Open Rate": segment_df["avg_open_rate"].tolist(),
            "CTR":       segment_df["avg_ctr"].tolist(),
            "CVR":       segment_df["avg_cvr"].tolist(),
        },
        height_mm=60,
    ))
    st.append(Spacer(1, 5*mm))

    # ── Page 2 ─────────────────────────────────────────────────────────────────
    st.append(PageBreak())

    # Trend chart
    st.append(Paragraph("OPEN RATE TREND OVER TIME", S["section"]))
    trend = df.groupby(["date","channel"])["open_rate"].mean().reset_index()
    st.append(_line_chart(trend, "date", "open_rate", "channel", height_mm=65))
    st.append(Spacer(1, 5*mm))

    # Anomalies
    st.append(Paragraph("FLAGGED ANOMALY CAMPAIGNS", S["section"]))
    if anomalies_df.empty:
        st.append(Paragraph("No anomalies detected in the current dataset.", S["body"]))
    else:
        ad = anomalies_df[["campaign_name","channel","segment",
                            "open_rate","ctr","cvr","anomaly_reason"]].copy()
        for c in ["open_rate","ctr","cvr"]:
            ad[c] = ad[c].map("{:.1%}".format)
        st.append(_data_tbl(ad.head(10), S,
            col_map={"campaign_name":"Campaign","channel":"Channel","segment":"Segment",
                     "open_rate":"Open Rate","ctr":"CTR","cvr":"CVR",
                     "anomaly_reason":"Reason"}))
    st.append(Spacer(1, 5*mm))

    # AI insight
    if ai_insight:
        st.append(Paragraph("AI-GENERATED INSIGHT", S["section"]))
        box = Table([[Paragraph(ai_insight, S["insight"])]], colWidths=[AW])
        box.setStyle(TableStyle([
            ("BACKGROUND",    (0,0),(-1,-1), C_CARD),
            ("BOX",           (0,0),(-1,-1), 0.5, C_BORDER),
            ("LINEABOVE",     (0,0),(-1, 0), 1.5, C_GREEN),
            ("TOPPADDING",    (0,0),(-1,-1), 8),
            ("BOTTOMPADDING", (0,0),(-1,-1), 8),
            ("LEFTPADDING",   (0,0),(-1,-1), 10),
            ("RIGHTPADDING",  (0,0),(-1,-1), 10),
        ]))
        st.append(box)
        st.append(Spacer(1, 5*mm))

    # Footer
    st += [
        HRFlowable(width=AW, thickness=0.5, color=C_BORDER, spaceBefore=3*mm),
        Spacer(1, 2*mm),
        Paragraph(
            "Generated automatically by PulseAI  |  Powered by Claude AI  |  "
            "All metrics based on campaign data provided to the platform.",
            S["footer"]),
    ]

    doc.build(st, onFirstPage=_dark_page, onLaterPages=_dark_page)
    return buf.getvalue()