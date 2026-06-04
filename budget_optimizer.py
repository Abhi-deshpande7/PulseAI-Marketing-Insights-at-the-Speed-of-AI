import pandas as pd
import numpy as np


def compute_channel_efficiency(df):
    ch = (
        df.groupby("channel")
        .agg(
            avg_roas=("roas", "mean"),
            avg_cvr=("cvr", "mean"),
            avg_ctr=("ctr", "mean"),
            avg_open_rate=("open_rate", "mean"),
            total_conversions=("conversions", "sum"),
            total_spend=("spend", "sum"),
        )
        .reset_index()
    )
    ch["cost_per_conv"] = ch["total_spend"] / ch["total_conversions"].replace(0, float("nan"))

    def norm(series):
        mn, mx = series.min(), series.max()
        if mx == mn:
            return pd.Series([1.0] * len(series), index=series.index)
        return (series - mn) / (mx - mn)

    ch["score_roas"]      = norm(ch["avg_roas"])
    ch["score_cvr"]       = norm(ch["avg_cvr"])
    ch["score_ctr"]       = norm(ch["avg_ctr"])
    ch["score_efficiency"] = norm(1 / ch["cost_per_conv"].replace(0, float("nan")).fillna(0.001))
    ch["composite_score"] = (
        ch["score_roas"]       * 0.45 +
        ch["score_cvr"]        * 0.25 +
        ch["score_ctr"]        * 0.15 +
        ch["score_efficiency"] * 0.15
    )
    total = ch["composite_score"].sum()
    ch["raw_allocation_pct"] = ch["composite_score"] / total
    return ch.sort_values("composite_score", ascending=False).reset_index(drop=True)


def allocate_budget(df, total_budget, min_pct=0.05, strategy="balanced"):
    eff = compute_channel_efficiency(df)
    if strategy == "aggressive":
        eff["adj_score"] = eff["composite_score"] ** 2
    elif strategy == "conservative":
        eff["adj_score"] = eff["composite_score"] ** 0.5
    else:
        eff["adj_score"] = eff["composite_score"]

    n = len(eff)
    floor = min_pct
    remaining_pct = 1.0 - floor * n
    total_adj = eff["adj_score"].sum()
    eff["allocation_pct"] = floor + (eff["adj_score"] / total_adj) * remaining_pct
    eff["allocation_pct"] = eff["allocation_pct"] / eff["allocation_pct"].sum()
    eff["recommended_spend"] = (eff["allocation_pct"] * total_budget).round(2)
    eff["projected_conversions"] = (
        eff["recommended_spend"] / eff["cost_per_conv"].replace(0, float("nan"))
    ).fillna(0).round(0).astype(int)

    return eff[["channel", "composite_score", "avg_roas", "avg_cvr",
                "cost_per_conv", "allocation_pct", "recommended_spend", "projected_conversions"]]


def generate_budget_insight(api_key, allocation_df, total_budget, strategy):
    import anthropic
    client = anthropic.Anthropic(api_key=api_key)
    alloc_str = allocation_df[["channel", "allocation_pct", "recommended_spend",
                                "avg_roas", "projected_conversions"]].to_string(index=False)
    prompt = f"""You are a senior media buyer. A brand has a total budget of ${total_budget:,.0f}.
Strategy: {strategy.upper()}

Allocation recommendation:
{alloc_str}

Provide:
1. **Why this allocation makes sense** (2-3 sentences referencing specific ROAS numbers)
2. **The biggest opportunity** - which channel to watch and why
3. **The biggest risk** - which channel might underperform and what to do
4. **One tactical tip** to maximise ROI

Be direct and specific. No generic advice."""

    response = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=450,
        messages=[{"role": "user", "content": prompt}]
    )
    return response.content[0].text
