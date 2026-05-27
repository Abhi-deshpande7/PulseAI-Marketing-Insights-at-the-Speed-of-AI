import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import random

def generate_campaigns(n=100, seed=42):
    np.random.seed(seed)
    random.seed(seed)

    channels = ["Email", "Push", "SMS", "In-App"]
    segments = ["New Users", "Power Users", "Dormant", "High Value"]

    base_rates = {
        "Email":  {"open": 0.22, "ctr": 0.035, "cvr": 0.018},
        "Push":   {"open": 0.15, "ctr": 0.028, "cvr": 0.012},
        "SMS":    {"open": 0.38, "ctr": 0.055, "cvr": 0.025},
        "In-App": {"open": 0.60, "ctr": 0.090, "cvr": 0.040},
    }

    start = datetime(2024, 1, 1)
    rows = []
    for i in range(n):
        ch = random.choice(channels)
        seg = random.choice(segments)
        br = base_rates[ch]
        date = start + timedelta(days=random.randint(0, 89))

        sent = random.randint(5000, 50000)
        opens = int(sent * np.random.normal(br["open"], br["open"] * 0.2))
        clicks = int(opens * np.random.normal(br["ctr"] / br["open"], 0.05))
        conversions = int(clicks * np.random.normal(br["cvr"] / br["ctr"], 0.04))

        if random.random() < 0.08:
            opens = int(opens * random.choice([0.2, 3.5]))

        opens = max(0, min(opens, sent))
        clicks = max(0, min(clicks, opens))
        conversions = max(0, min(conversions, clicks))

        rows.append({
            "campaign_id": f"C{i+1:04d}",
            "campaign_name": f"{ch} {seg} #{i+1}",
            "channel": ch,
            "segment": seg,
            "date": date,
            "sent": sent,
            "opens": opens,
            "clicks": clicks,
            "conversions": conversions,
            "spend": round(random.uniform(200, 5000), 2),
        })

    return pd.DataFrame(rows)
