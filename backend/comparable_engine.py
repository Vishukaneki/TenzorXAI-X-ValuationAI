"""
comparable_engine.py
--------------------
Queries synthetic dataset for nearest comparable transactions.
Matching logic: same city + property_type + size ±25% → top 5 by size proximity.
"""

import pandas as pd
import numpy as np
from typing import List, Dict


class ComparableEngine:
    def __init__(self, df: pd.DataFrame):
        self.df = df

    def find_comps(self, locality_row: dict, property_type: str,
                   size_sqft: float, n: int = 5) -> dict:
        city = locality_row["city"]
        tier = int(locality_row["tier"])

        # Filter: same city, same type, same tier, size within ±25%
        mask = (
            (self.df["city"] == city) &
            (self.df["property_type"] == property_type) &
            (self.df["tier"] == tier) &
            (self.df["size_sqft"] >= size_sqft * 0.75) &
            (self.df["size_sqft"] <= size_sqft * 1.25)
        )
        subset = self.df[mask].copy()

        if len(subset) == 0:
            # Widen to any tier in city
            subset = self.df[
                (self.df["city"] == city) &
                (self.df["property_type"] == property_type)
            ].copy()

        subset["size_diff"] = abs(subset["size_sqft"] - size_sqft)
        top = subset.nsmallest(n, "size_diff")

        comps = []
        for _, row in top.iterrows():
            comps.append({
                "locality":      row["locality"],
                "subtype":       row["subtype"],
                "size_sqft":     round(row["size_sqft"], 0),
                "age_years":     int(row["age_years"]),
                "market_value":  round(row["market_value"], 0),
                "price_per_sqft": round(row["price_per_sqft"], 0),
            })

        density_score = float(np.clip(len(subset) / 500, 0.1, 1.0))
        return {"comps": comps, "density_score": round(density_score, 3)}
