"""
train_model.py
--------------
Trains LightGBM on synthetic_100k.parquet.
Saves model.pkl to backend/data/.
Run once: python scripts/train_model.py
"""

import os
import pickle
import numpy as np
import pandas as pd
import lightgbm as lgb
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_absolute_percentage_error

DATA_DIR  = os.path.join(os.path.dirname(__file__), "..", "data")
MODEL_OUT = os.path.join(DATA_DIR, "model.pkl")

# Features the model sees — must match feature_engineer.py output exactly
FEATURES = [
    "circle_rate",
    "tier",
    "market_multiplier",
    "infra_score",
    "market_activity",
    "subtype_premium",
    "age_depreciation",
    "floor_adjustment",
    "size_sqft",
    "size_vs_norm",
    "age_years",
    "has_lift",
    "listing_density",
]

TARGET = "price_per_sqft"   # predict ₹/sqft, multiply by size for total value


def train():
    print("Loading synthetic dataset...")
    df = pd.read_parquet(os.path.join(DATA_DIR, "synthetic_100k.parquet"))
    print(f"  Shape: {df.shape}")

    df["has_lift"] = df["has_lift"].astype(int)

    X = df[FEATURES]
    y = df[TARGET]

    X_train, X_val, y_train, y_val = train_test_split(
        X, y, test_size=0.15, random_state=42
    )

    print(f"  Train: {len(X_train):,}  Val: {len(X_val):,}")

    params = {
        "objective":        "regression",
        "metric":           "mape",
        "learning_rate":    0.05,
        "num_leaves":       127,
        "max_depth":        -1,
        "min_child_samples": 30,
        "feature_fraction": 0.85,
        "bagging_fraction": 0.85,
        "bagging_freq":     5,
        "reg_alpha":        0.1,
        "reg_lambda":       0.1,
        "verbose":          -1,
        "n_jobs":           -1,
    }

    dtrain = lgb.Dataset(X_train, label=y_train)
    dval   = lgb.Dataset(X_val,   label=y_val, reference=dtrain)

    print("\nTraining LightGBM...")
    model = lgb.train(
        params,
        dtrain,
        num_boost_round=800,
        valid_sets=[dval],
        callbacks=[
            lgb.early_stopping(stopping_rounds=50, verbose=False),
            lgb.log_evaluation(period=100),
        ],
    )

    preds = model.predict(X_val)
    mape  = mean_absolute_percentage_error(y_val, preds)
    print(f"\nValidation MAPE: {mape:.4f} ({mape*100:.2f}%)")

    # Feature importance — good for debugging, not used in production
    fi = pd.Series(
        model.feature_importance(importance_type="gain"),
        index=FEATURES
    ).sort_values(ascending=False)
    print("\nFeature Importance (gain):")
    print(fi.to_string())

    # Save
    artifact = {
        "model":    model,
        "features": FEATURES,
        "target":   TARGET,
        "val_mape": mape,
    }
    with open(MODEL_OUT, "wb") as f:
        pickle.dump(artifact, f)

    print(f"\nSaved model.pkl → {MODEL_OUT}")
    print("Done. Start FastAPI with: uvicorn main:app --reload")


if __name__ == "__main__":
    train()
