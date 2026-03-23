import pandas as pd
import numpy as np

def compute_metrics(df):
    df = df.copy()
    df["open_rate"] = df["opens"] / df["sent"]
    df["ctr"] = df["clicks"] / df["sent"]
    df["cvr"] = df["conversions"] / df["clicks"].replace(0, np.nan)
    df["date"] = pd.to_datetime(df["date"])
    df = df.fillna(0)
    return df

def detect_anomalies(df):
    df = df.copy()
    for metric in ["open_rate", "ctr", "cvr"]:
        mean = df[metric].mean()
        std = df[metric].std()
        df[f"{metric}_zscore"] = (df[metric] - mean) / std
        df[f"{metric}_flag"] = df[f"{metric}_zscore"].abs() > 2
    df["is_anomaly"] = df[["open_rate_flag", "ctr_flag", "cvr_flag"]].any(axis=1)
    return df

def segment_summary(df):
    return df.groupby("segment").agg(
        avg_open_rate=("open_rate", "mean"),
        avg_ctr=("ctr", "mean"),
        avg_cvr=("cvr", "mean"),
        total_conversions=("conversions", "sum"),
        campaigns=("campaign_id", "count")
    ).reset_index()

def channel_summary(df):
    return df.groupby("channel").agg(
        avg_open_rate=("open_rate", "mean"),
        avg_ctr=("ctr", "mean"),
        avg_cvr=("cvr", "mean"),
        total_conversions=("conversions", "sum")
    ).reset_index()

def compute_health_score(df):
    df = df.copy()
    open_score  = (df["open_rate"] / df["open_rate"].max()) * 40
    ctr_score   = (df["ctr"] / df["ctr"].max()) * 35
    cvr_score   = (df["cvr"] / df["cvr"].max()) * 25
    df["health_score"] = (open_score + ctr_score + cvr_score).round(1)
    df["health_label"] = pd.cut(
        df["health_score"],
        bins=[0, 40, 70, 100],
        labels=["Poor", "Average", "Good"]
    )
    return df

