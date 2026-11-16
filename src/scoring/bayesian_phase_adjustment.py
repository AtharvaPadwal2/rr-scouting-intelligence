
from pathlib import Path
import pandas as pd
import numpy as np

ROOT = Path(__file__).resolve().parents[2]

DATA = ROOT / "data" / "processed" / "scoring"
OUTPUT = DATA

PRIOR_BALLS = 120

df = pd.read_csv(
    DATA / "phase_pressure_features.csv"
)

# Raw impact (positive = better than league baseline)
df["raw_impact"] = np.where(
    df["role"].eq("batting"),
    df["batting_impact"],
    df["bowling_impact"]
)

# Sample-size reliability factor
df["sample_weight"] = (
    df["balls"] / (df["balls"] + PRIOR_BALLS)
)

# Apply shrinkage toward league baseline
df["adjusted_impact"] = (
    df["raw_impact"] * df["sample_weight"]
)

# Model-based sample confidence (not final reliability)
df["sample_confidence"] = (
    df["sample_weight"] * 100
)

# Preserve original impact units:
# Batting = strike-rate points above expected
# Bowling = runs prevented per over

df["impact_unit"] = np.where(
    df["role"].eq("batting"),
    "SR points",
    "Runs per over"
)

columns = [
    "player",
    "league",
    "role",
    "phase",
    "matches",
    "balls",
    "raw_impact",
    "sample_weight",
    "adjusted_impact",
    "sample_confidence",
    "impact_unit"
]

result = df[columns].copy()

result.to_csv(
    OUTPUT / "bayesian_phase_adjusted.csv",
    index=False
)

print("\n=== BAYESIAN PHASE ADJUSTMENT ===")
print(result.round(2).to_string(index=False))

print("\n=== SAMPLE CONFIDENCE SUMMARY ===")

summary = result.groupby(
    ["player", "role"]
).agg(
    total_balls=("balls", "sum"),
    average_sample_confidence=(
        "sample_confidence", "mean"
    )
).reset_index()

print(summary.round(2).to_string(index=False))

print("\nSaved: bayesian_phase_adjusted.csv")
