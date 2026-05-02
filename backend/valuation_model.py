"""
valuation_model.py
------------------
LightGBM wrapper. Predicts price_per_sqft, applies uncertainty band,
and extracts SHAP-based key drivers.
"""

import pickle
import numpy as np
import pandas as pd
import shap
from typing import Tuple, List, Dict


class ValuationModel:
    UNCERTAINTY_BAND = 0.08   # ±8% around point estimate → value range

    def __init__(self, model_path: str):
        with open(model_path, "rb") as f:
            artifact = pickle.load(f)
        self.model    = artifact["model"]
        self.features = artifact["features"]
        self._explainer = None   # lazy-loaded

    def predict(self, model_features: dict, size_sqft: float) -> dict:
        X = pd.DataFrame([model_features])[self.features]

        price_per_sqft = float(self.model.predict(X)[0])
        price_per_sqft = max(price_per_sqft, model_features["circle_rate"] * 0.95)

        point_value   = price_per_sqft * size_sqft
        lower_value   = point_value * (1 - self.UNCERTAINTY_BAND)
        upper_value   = point_value * (1 + self.UNCERTAINTY_BAND)

        drivers = self._shap_drivers(X, price_per_sqft)

        return {
            "price_per_sqft":     round(price_per_sqft, 2),
            "point_value":        round(point_value, 0),
            "market_value_range": [round(lower_value, 0), round(upper_value, 0)],
            "key_drivers":        drivers,
        }

    def _shap_drivers(self, X: pd.DataFrame, base_ppsf: float) -> List[Dict]:
        if self._explainer is None:
            self._explainer = shap.TreeExplainer(self.model)

        sv     = self._explainer.shap_values(X)[0]
        impact = {feat: val for feat, val in zip(self.features, sv)}

        # Convert to % impact on price_per_sqft
        drivers = []
        for feat, val in sorted(impact.items(), key=lambda x: abs(x[1]), reverse=True)[:5]:
            pct = (val / base_ppsf) * 100 if base_ppsf else 0
            drivers.append({
                "driver":      feat,
                "shap_impact": f"{pct:+.1f}%",
                "direction":   "positive" if val > 0 else "negative",
            })
        return drivers
