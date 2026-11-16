
from pathlib import Path
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data" / "processed" / "rr_official"
REPORT = ROOT / "data" / "reports" / "rr_official"

REPORT.mkdir(parents=True, exist_ok=True)

df = pd.read_csv(
    DATA / "deliveries_clean.csv",
    low_memory=False
)

df["extra"] = (
    df["extras_type"]
    .astype("string")
    .str.lower()
    .str.strip()
    .fillna("none")
)

# Conservative lower-bound accounting.
# These are NOT verified scoreboard totals.
df["minimum_extra_runs"] = 0

# Each wide and overstep contributes at least 1 run.
df.loc[
    df["extra"].isin(["wide", "overstep"]),
    "minimum_extra_runs"
] = 1

# Byes / leg-byes normally contribute at least 1 run.
df.loc[
    df["extra"].isin(["byes", "legbyes"]),
    "minimum_extra_runs"
] = 1

# Include additional recorded runs, but keep
# the total provisional until source semantics
# are independently verified.
df["minimum_recorded_total"] = (
    df["runs"].fillna(0)
    + df["extras_2_runs"].fillna(0)
    + df["minimum_extra_runs"]
)

df["has_uncertain_extra"] = df["extra"].isin([
    "wide", "byes", "legbyes",
    "overstep", "other", "penalty"
])

df["has_ambiguous_extra"] = df["extra"].isin([
    "other", "penalty"
])

# Identify known structural sequence anomalies.
sequence_issues = {14130, 14164, 41509}

df["known_sequence_issue"] = (
    df["match_id"].isin(sequence_issues)
)

summary = (
    df.groupby(["match_id", "innings"])
    .agg(
        deliveries=("match_id", "size"),
        minimum_recorded_runs=("minimum_recorded_total", "sum"),
        batter_runs=("runs", "sum"),
        uncertain_events=("has_uncertain_extra", "sum"),
        ambiguous_events=("has_ambiguous_extra", "sum"),
        sequence_issue=("known_sequence_issue", "max")
    )
    .reset_index()
)

# Conservative screening tiers.
# Clean here means no identified extras ambiguity.
# It does NOT certify the innings against scorecards.
def classify(row):
    if row["sequence_issue"] or row["ambiguous_events"] > 0:
        return "REVIEW_REQUIRED"
    if row["uncertain_events"] > 0:
        return "EXTRAS_VERIFICATION_REQUIRED"
    return "STRUCTURALLY_CLEAN"

summary["quality_tier"] = summary.apply(
    classify, axis=1
)

summary.to_csv(
    REPORT / "innings_scoring_quality.csv",
    index=False
)

df = df.merge(
    summary[
        ["match_id", "innings", "quality_tier"]
    ],
    on=["match_id", "innings"],
    how="left",
    validate="many_to_one"
)

df.to_csv(
    DATA / "deliveries_with_quality_flags.csv",
    index=False
)

print("\n=== INNINGS QUALITY DISTRIBUTION ===")
print(summary["quality_tier"].value_counts())

print("\n=== DELIVERY QUALITY DISTRIBUTION ===")
print(df["quality_tier"].value_counts())

print("\n=== SCORING VALIDATION EXAMPLE ===")
print(
    summary[summary["match_id"] == 13511]
    .to_string(index=False)
)

print("\n=== OUTPUT FILES ===")
print("innings_scoring_quality.csv")
print("deliveries_with_quality_flags.csv")

print("\nIMPORTANT:")
print("No innings have been externally certified by this script.")
print("Do not use provisional totals for final pressure rankings.")
