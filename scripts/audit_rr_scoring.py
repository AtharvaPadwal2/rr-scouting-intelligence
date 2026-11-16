
from pathlib import Path
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data" / "processed" / "rr_official"
REPORT = ROOT / "data" / "reports" / "rr_official"
REPORT.mkdir(parents=True, exist_ok=True)

df = pd.read_csv(DATA / "deliveries_clean.csv", low_memory=False)
matches = pd.read_csv(DATA / "matches_clean.csv", low_memory=False)

df["extra_type"] = (
    df["extras_type"].astype("string")
    .str.lower().str.strip().fillna("none")
)

# Inspect possible run-accounting fields.
print("\n=== MATCH SCORE FIELDS ===")
print(matches.columns.tolist())

print("\n=== EXTRA TYPE RUN ACCOUNTING ===")

summary = (
    df.groupby("extra_type", dropna=False)
    .agg(
        events=("match_id", "size"),
        batter_runs=("runs", "sum"),
        additional_runs=("extras_2_runs", "sum"),
        code_values=("extras1_runs", "nunique")
    )
    .reset_index()
)

print(summary.to_string(index=False))

# Show how extra types interact with runs.
for extra in [
    "wide", "overstep", "legbyes",
    "byes", "other", "penalty"
]:
    subset = df[df["extra_type"] == extra]

    print(f"\n=== {extra.upper()} ===")
    print("Events:", len(subset))

    print(
        subset.groupby(
            ["runs", "extras_2_runs"],
            dropna=False
        )
        .size()
        .sort_values(ascending=False)
        .head(12)
        .to_string()
    )

    print("\nExample deliveries:")
    cols = [
        "match_id", "innings", "overid",
        "over_ball_num", "runs",
        "extras_type", "extras1_runs",
        "extras_2_runs"
    ]

    print(subset[cols].head(5).to_string(index=False))

# Produce alternative scoreboard totals.
# These are candidate interpretations, not
# validated or final match scores.
df["candidate_a"] = (
    df["runs"].fillna(0)
    + df["extras_2_runs"].fillna(0)
)

df["candidate_b"] = (
    df["candidate_a"]
    + df["extra_type"].isin(["wide", "overstep"]).astype(int)
)

candidate_scores = (
    df.groupby(["match_id", "innings"])
    .agg(
        candidate_a=("candidate_a", "sum"),
        candidate_b=("candidate_b", "sum"),
        deliveries=("match_id", "size")
    )
    .reset_index()
)

candidate_scores.to_csv(
    REPORT / "score_reconstruction_candidates.csv",
    index=False
)

print("\n=== SAMPLE SCORE RECONSTRUCTIONS ===")
print(candidate_scores.head(20).to_string(index=False))

# Identify matches with known delivery sequence issues.
problem_matches = [14130, 14164, 41509]

df["flag_sequence_problem"] = (
    df["match_id"].isin(problem_matches)
)

df["flag_ambiguous_extra"] = (
    df["extra_type"] == "other"
)

df["flag_pressure_review"] = (
    df["flag_sequence_problem"]
    | df["flag_ambiguous_extra"]
)

print("\n=== PRESSURE MODEL QUALITY FLAGS ===")
print(
    "Known sequence-problem deliveries:",
    int(df["flag_sequence_problem"].sum())
)
print(
    "Ambiguous-extra deliveries:",
    int(df["flag_ambiguous_extra"].sum())
)
print(
    "Total flagged delivery rows:",
    int(df["flag_pressure_review"].sum())
)

print("\nScoring audit complete.")
