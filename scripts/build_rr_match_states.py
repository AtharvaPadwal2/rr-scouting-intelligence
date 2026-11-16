
from pathlib import Path
import pandas as pd
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data" / "processed" / "rr_official"
DATA.mkdir(parents=True, exist_ok=True)

df = pd.read_csv(
    DATA / "deliveries_with_quality_flags.csv",
    low_memory=False
)

# Preserve only innings with reliable ordering.
required = [
    "match_id", "innings", "innings_ball_num",
    "overid", "striker_id", "bowler_id",
    "runs", "dismissal_type"
]

missing = [c for c in required if c not in df.columns]
if missing:
    raise ValueError(f"Missing columns: {missing}")

df = df.sort_values(
    ["match_id", "innings", "innings_ball_num"],
    kind="stable"
).reset_index(drop=True)

# ------------------------------------------
# 1. Identify dismissal events.
# ------------------------------------------
kind = (
    df["dismissal_type"]
    .fillna("")
    .astype(str)
    .str.lower()
    .str.replace(" ", "", regex=False)
    .str.strip()
)

df["team_wicket"] = (
    kind.ne("")
    & ~kind.isin(["retiredhurt"])
).astype(int)

# ------------------------------------------
# 2. Wickets BEFORE every delivery.
# ------------------------------------------
group_cols = ["match_id", "innings"]

groups = df.groupby(group_cols, sort=False)

df["wickets_before"] = (
    groups["team_wicket"].cumsum()
    - df["team_wicket"]
)

df["wickets_remaining"] = (
    10 - df["wickets_before"]
).clip(lower=0)

# ------------------------------------------
# 3. Phase and innings-stage pressure.
# ------------------------------------------
def innings_phase(over):
    if pd.isna(over):
        return "unknown"
    if over <= 6:
        return "powerplay"
    if over <= 15:
        return "middle"
    if over <= 20:
        return "death"
    return "other"

df["pressure_phase"] = df["overid"].apply(
    innings_phase
)

# Higher weight for later innings stages.
phase_weights = {
    "powerplay": 0.15,
    "middle": 0.45,
    "death": 0.85,
    "other": 0.50,
    "unknown": 0.00,
}

df["stage_pressure"] = (
    df["pressure_phase"].map(phase_weights)
)

# Wicket pressure increases as resources decline.
df["wicket_pressure"] = (
    df["wickets_before"] / 10
).clip(0, 1)

# ------------------------------------------
# 4. Provisional structural pressure index.
# ------------------------------------------
# This is an analyst-defined proxy, NOT
# verified required-run-rate pressure.
df["structural_pressure_score"] = (
    100 * (
        0.45 * df["stage_pressure"]
        + 0.55 * df["wicket_pressure"]
    )
).round(2)

df["structural_pressure_level"] = pd.cut(
    df["structural_pressure_score"],
    bins=[-0.01, 30, 55, 75, 100],
    labels=["Low", "Moderate", "High", "Extreme"],
    include_lowest=True
)

# ------------------------------------------
# 5. Data-quality safeguards.
# ------------------------------------------
df["flag_sequence_issue"] = (
    df["match_id"].isin([14130, 14164, 41509])
)

df["flag_ambiguous_extra"] = (
    df["extras_type"]
    .fillna("")
    .astype(str)
    .str.lower()
    .eq("other")
)

df["flag_invalid_wicket_state"] = (
    df["wickets_before"] > 10
)

df["pressure_eligible"] = ~(
    df["flag_sequence_issue"]
    | df["flag_ambiguous_extra"]
    | df["flag_invalid_wicket_state"]
)

# ------------------------------------------
# 6. Export match states.
# ------------------------------------------
output = DATA / "match_states_preliminary.csv"
df.to_csv(output, index=False)

# Aggregate safely for an initial audit.
summary = (
    df.groupby(
        "structural_pressure_level",
        observed=True
    )
    .agg(
        deliveries=("match_id", "size"),
        unique_matches=("match_id", "nunique"),
        eligible_deliveries=("pressure_eligible", "sum")
    )
    .reset_index()
)

print("\n=== PRESSURE LEVEL DISTRIBUTION ===")
print(summary.to_string(index=False))

print("\n=== MATCH STATE VALIDATION ===")
print("Total deliveries:", len(df))
print(
    "Eligible deliveries:",
    int(df["pressure_eligible"].sum())
)
print(
    "Wicket-state anomalies:",
    int(df["flag_invalid_wicket_state"].sum())
)
print(
    "Ambiguous other extras:",
    int(df["flag_ambiguous_extra"].sum())
)

print("\nSaved:", output)
print("\nThis is a preliminary structural-pressure proxy.")
print("Exact match-score pressure is not yet available.")
