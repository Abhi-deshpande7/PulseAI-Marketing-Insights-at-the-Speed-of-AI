import pandas as pd
import numpy as np
try:
    try:
    from prophet import Prophet
    PROPHET_AVAILABLE = True
except ImportError:
    PROPHET_AVAILABLE = False
    PROPHET_AVAILABLE = True
except ImportError:
    PROPHET_AVAILABLE = False
import warnings
warnings.filterwarnings("ignore")


METRICS = {
    "open_rate":  "Avg Open Rate",
    "ctr":        "Avg CTR",
    "cvr":        "Avg CVR",
    "roas":       "Avg ROAS",
    "conversions": "Total Conversions",
}


def _prepare_daily(df: pd.DataFrame, metric: str, channel: str = "All") -> pd.DataFrame:
    """Aggregate campaign data to daily level for a given metric."""
    tmp = df.copy()
    if channel != "All":
        tmp = tmp[tmp["channel"] == channel]

    if metric == "conversions":
        daily = tmp.groupby("date")["conversions"].sum().reset_index()
        daily.columns = ["ds", "y"]
    else:
        daily = tmp.groupby("date")[metric].mean().reset_index()
        daily.columns = ["ds", "y"]

    daily["ds"] = pd.to_datetime(daily["ds"])
    daily = daily.dropna().sort_values("ds")
    return daily


def run_forecast(
    df: pd.DataFrame,
    metric: str = "open_rate",
    channel: str = "All",
    horizon_days: int = 30,
    changepoint_scale: float = 0.05,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """
    Run Prophet forecast.
    Returns (historical_df, forecast_df) both with columns:
      ds, y (actual), yhat, yhat_lower, yhat_upper
    """
    daily = _prepare_daily(df, metric, channel)

    if len(daily) < 7:
        raise ValueError("Not enough data points to forecast. Need at least 7 days.")

    m = Prophet(
        changepoint_prior_scale=changepoint_scale,
        seasonality_mode="multiplicative",
        weekly_seasonality=True,
        daily_seasonality=False,
        interval_width=0.80,
    )
    m.fit(daily)

    future = m.make_future_dataframe(periods=horizon_days, freq="D")
    forecast = m.predict(future)

    # Clip negatives for rate metrics
    if metric in ("open_rate", "ctr", "cvr"):
        for col in ("yhat", "yhat_lower", "yhat_upper"):
            forecast[col] = forecast[col].clip(lower=0, upper=1)

    # Merge actuals back
    merged = forecast[["ds", "yhat", "yhat_lower", "yhat_upper"]].merge(
        daily, on="ds", how="left"
    )

    historical = merged[merged["y"].notna()].copy()
    future_only = merged[merged["y"].isna()].copy()

    return historical, future_only


def forecast_all_channels(
    df: pd.DataFrame,
    metric: str = "open_rate",
    horizon_days: int = 30,
) -> dict[str, tuple[pd.DataFrame, pd.DataFrame]]:
    """Run forecast for each channel separately."""
    results = {}
    channels = ["All"] + sorted(df["channel"].unique().tolist())
    for ch in channels:
        try:
            hist, fut = run_forecast(df, metric=metric, channel=ch, horizon_days=horizon_days)
            results[ch] = (hist, fut)
        except Exception:
            pass
    return results


def forecast_summary_stats(future_df: pd.DataFrame, metric: str) -> dict:
    """Return summary stats for the forecast period."""
    is_rate = metric in ("open_rate", "ctr", "cvr")
    fmt = lambda v: f"{v:.1%}" if is_rate else f"{v:,.1f}"

    return {
        "predicted_avg":  fmt(future_df["yhat"].mean()),
        "predicted_high": fmt(future_df["yhat_upper"].max()),
        "predicted_low":  fmt(future_df["yhat_lower"].min()),
        "trend": "📈 Upward" if future_df["yhat"].iloc[-1] > future_df["yhat"].iloc[0] else "📉 Downward",
    }


def generate_forecast_insight(api_key: str, stats: dict, metric_label: str,
                               channel: str, horizon: int) -> str:
    """Ask Claude to interpret the forecast."""
    import anthropic
    client = anthropic.Anthropic(api_key=api_key)

    prompt = f"""You are a marketing analyst. Interpret this {horizon}-day forecast for a marketing campaign metric.

Metric: {metric_label}
Channel: {channel}
Forecast trend: {stats['trend']}
Predicted average: {stats['predicted_avg']}
Predicted range: {stats['predicted_low']} – {stats['predicted_high']}

Provide:
1. **What this forecast means** for the marketing team (1-2 sentences)
2. **One proactive action** they should take based on this trend
3. **One risk** to watch out for

Be concise and specific. No generic advice."""

    response = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=350,
        messages=[{"role": "user", "content": prompt}]
    )
    return response.content[0].text
