import pandas as pd
import numpy as np


def compute_metrics(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df["open_rate"] = df["opens"] / df["sent"].replace(0, np.nan)
    df["ctr"] = df["clicks"] / df["opens"].replace(0, np.nan)
    df["cvr"] = df["conversions"] / df["clicks"].replace(0, np.nan)
    df["roas"] = (df["conversions"] * 50) / df["spend"].replace(0, np.nan)
    df[["open_rate", "ctr", "cvr", "roas"]] = df[["open_rate", "ctr", "cvr", "roas"]].fillna(0)
    return df


def detect_anomalies(df: pd.DataFrame, z_thresh: float = 2.5) -> pd.DataFrame:
    df = df.copy()
    df["is_anomaly"] = False
    df["anomaly_reason"] = ""
    for col, label in [("open_rate", "open rate"), ("ctr", "CTR"), ("cvr", "CVR")]:
        mean = df[col].mean()
        std = df[col].std()
        if std == 0:
            continue
        z = (df[col] - mean) / std
        mask = z.abs() > z_thresh
        df.loc[mask, "is_anomaly"] = True
        df.loc[mask, "anomaly_reason"] += f"Unusual {label} (z={z[mask].round(1).astype(str)}); "
    df["anomaly_reason"] = df["anomaly_reason"].str.rstrip("; ")
    return df


def channel_summary(df: pd.DataFrame) -> pd.DataFrame:
    # Use campaign_id if present, otherwise fall back to campaign_name or first column
    if "campaign_id" in df.columns:
        count_col = "campaign_id"
    elif "campaign_name" in df.columns:
        count_col = "campaign_name"
    else:
        count_col = df.columns[0]

    return (
        df.groupby("channel")
        .agg(
            avg_open_rate=("open_rate", "mean"),
            avg_ctr=("ctr", "mean"),
            avg_cvr=("cvr", "mean"),
            avg_roas=("roas", "mean"),
            total_conversions=("conversions", "sum"),
            total_spend=("spend", "sum"),
            campaign_count=(count_col, "count"),
        )
        .reset_index()
    )


def segment_summary(df: pd.DataFrame) -> pd.DataFrame:
    return (
        df.groupby("segment")
        .agg(
            avg_open_rate=("open_rate", "mean"),
            avg_ctr=("ctr", "mean"),
            avg_cvr=("cvr", "mean"),
            avg_roas=("roas", "mean"),
            total_conversions=("conversions", "sum"),
        )
        .reset_index()
    )


def build_context_summary(df: pd.DataFrame) -> str:
    ch  = channel_summary(df)
    seg = segment_summary(df)

    # Use campaign_name or campaign_id for anomaly display
    name_col = "campaign_name" if "campaign_name" in df.columns else df.columns[0]
    anomalies = df[df["is_anomaly"]][[name_col, "channel", "segment",
                                      "open_rate", "ctr", "cvr", "anomaly_reason"]]

    lines = [
        "=== CAMPAIGN DATASET OVERVIEW ===",
        f"Total campaigns: {len(df)}",
        f"Date range: {df['date'].min().date()} to {df['date'].max().date()}",
        f"Total spend: ${df['spend'].sum():,.0f}",
        f"Total conversions: {df['conversions'].sum():,}",
        f"Anomalies flagged: {df['is_anomaly'].sum()}",
        "",
        "=== CHANNEL PERFORMANCE ===",
        ch[["channel","avg_open_rate","avg_ctr","avg_cvr","avg_roas",
            "total_conversions","total_spend"]].to_string(index=False),
        "",
        "=== SEGMENT PERFORMANCE ===",
        seg[["segment","avg_open_rate","avg_ctr","avg_cvr","avg_roas",
             "total_conversions"]].to_string(index=False),
    ]

    if not anomalies.empty:
        lines += ["", "=== FLAGGED ANOMALY CAMPAIGNS (top 10) ===",
                  anomalies.head(10).to_string(index=False)]

    return "\n".join(lines)