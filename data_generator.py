import pandas as pd
import numpy as np
from faker import Faker

fake = Faker()

def generate_campaigns(n=100):
    data = []
    for _ in range(n):
        sent = np.random.randint(5000, 100000)
        open_rate = np.random.beta(2, 8)
        ctr = open_rate * np.random.uniform(0.1, 0.4)
        cvr = ctr * np.random.uniform(0.05, 0.3)
        data.append({
            "campaign_id": fake.uuid4()[:8].upper(),
            "campaign_name": fake.catch_phrase(),
            "channel": np.random.choice(["Email", "Push", "SMS", "In-App"]),
            "segment": np.random.choice(["New Users", "Power Users", "Dormant", "High Value"]),
            "date": fake.date_between(start_date="-90d", end_date="today"),
            "sent": sent,
            "opens": int(sent * open_rate),
            "clicks": int(sent * ctr),
            "conversions": int(sent * cvr)
        })
    return pd.DataFrame(data)