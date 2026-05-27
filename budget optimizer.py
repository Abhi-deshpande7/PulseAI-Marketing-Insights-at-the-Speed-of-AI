import pandas as pd
import numpy as np


def compute_channel_efficiency(df: pd.DataFrame) -> pd.DataFrame:
    """
    Score each channel on multiple efficiency dimensions.
    Returns a DataFrame with allocation scores.
    """
    ch = (
        df.groupby("channel")
        .agg(
            avg_roas=("roas", "mean"),
            avg_cvr=("cvr", "mean"),
            avg_ctr=("ctr", "mean"),
            avg_open_rate=("open_rate", "mean"),
            total_conversions=("conversions", "sum"),
            total_spend=("spend", "sum"),
            campaign_count=("campaign_id", "count"),
        )
        .reset_index()
    )

    # Cost per conversion
    ch["cost_per_conv"] = ch["total_spend"] / ch["total_conversions"].replace(0, np.nan)

    # Normalise each metric 0-1
    def norm(series):
        mn, mx = series.min(), series.max()
        if mx == mn:
            return pd.Series([1.0] * len(series), index=series.index)
        return (series - mn) / (mx - mn)

    ch["score_roas"]      = norm(ch["avg_roas"])
    ch["score_cvr"]       = norm(ch["avg_cvr"])
    ch["score_ctr"]       = norm(ch["avg_ctr"])
    ch["score_efficiency"] = norm(1 / ch["cost_per_conv"].replace(0, np.nan).fillna(0.001))

    # Weighted composite score  (ROAS heaviest)
    ch["composite_score"] = (
        ch["score_roas"]       * 0.45 +
        ch["score_cvr"]        * 0.25 +
        ch["score_ctr"]        * 0.15 +
        ch["score_efficiency"] * 0.15
    )

    # Normalize scores to sum to 1  → raw allocation %
    total = ch["composite_score"].sum()
    ch["raw_allocation_pct"] = ch["composite_score"] / total

    return ch.sort_values("composite_score", ascending=False).reset_index(drop=True)


def allocate_budget(
    df: pd.DataFrame,
    total_budget: float,
    min_pct: float = 0.05,       # no channel gets less than 5 %
    strategy: str = "balanced",  # "balanced" | "aggressive" | "conservative"
) -> pd.DataFrame:
    """
    Return a DataFrame with recommended budget per channel.
    strategy:
      balanced    – follow composite score
      aggressive  – double-down on top 2 channels
      conservative – flatten distribution (more equal)
    """
    eff = compute_channel_efficiency(df)

    if strategy == "aggressive":
        # Exaggerate scores for top performers
        eff["adj_score"] = eff["composite_score"] ** 2
    elif strategy == "conservative":
        # Dampen differences → more equal split
        eff["adj_score"] = np.sqrt(eff["composite_score"])
    else:
        eff["adj_score"] = eff["composite_score"]

    # Apply minimum floor
    n = len(eff)
    floor = min_pct
    remaining_pct = 1.0 - floor * n
    total_adj = eff["adj_score"].sum()
    eff["allocation_pct"] = floor + (eff["adj_score"] / total_adj) * remaining_pct

    # Re-normalise to exactly 100 %
    eff["allocation_pct"] = eff["allocation_pct"] / eff["allocation_pct"].sum()
    eff["recommended_spend"] = (eff["allocation_pct"] * total_budget).round(2)

    # Projected conversions based on historical cost-per-conv
    eff["projected_conversions"] = (
        eff["recommended_spend"] / eff["cost_per_conv"].replace(0, np.nan)
    ).fillna(0).round(0).astype(int)

    return eff[[
        "channel", "composite_score", "avg_roas", "avg_cvr",
        "cost_per_conv", "allocation_pct", "recommended_spend", "projected_conversions",
    ]]


def generate_budget_insight(
    api_key: str,
    allocation_df: pd.DataFrame,
    total_budget: float,
    strategy: str,
) -> str:
    """Ask Claude to explain the budget recommendation."""
    import anthropic
    client = anthropic.Anthropic(api_key=api_key)

    alloc_str = allocation_df[[
        "channel", "allocation_pct", "recommended_spend",
        "avg_roas", "projected_conversions"
    ]].to_string(index=False)

    prompt = f"""You are a senior media buyer and marketing strategist.

A brand has a total budget of ${total_budget:,.0f} and wants to allocate it across marketing channels.
Strategy selected: {strategy.upper()}

Here is the data-driven allocation recommendation:
{alloc_str}

Provide:
1. **Why this allocation makes sense** — reference specific ROAS or CVR numbers (2-3 sentences)
2. **The biggest opportunity** — which channel to watch and why
3. **The biggest risk** — which channel might underperform and what to do about it
4. **One tactical tip** — a specific action to maximise ROI from this allocation

Be direct, specific, and use the numbers provided. No generic advice."""

    response = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=450,
        messages=[{"role": "user", "content": prompt}]
    )
    return response.content[0].text