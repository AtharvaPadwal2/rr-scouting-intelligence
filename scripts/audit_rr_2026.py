
from pathlib import Path
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data" / "processed"
REPORT = ROOT / "data" / "reports"
REPORT.mkdir(parents=True, exist_ok=True)

df = pd.read_csv(
    DATA / "rr_2026_deliveries.csv",
    low_memory=False
)

print("\n=== RR DATASET ===")
print("Rows:", len(df))
print("Matches:", df["match_id"].nunique())
print("Innings:", df.groupby(
    ["match_id", "inning"]
).ngroups)

# 1. Check extra / unknown columns.
inspect_cols = [
    "extras_detail", "c1", "c2", "c3", "c4",
    "c5", "c8", "c9", "c10", "c11", "c12",
    "wicket_kind", "player_dismissed"
]

print("\n=== NON-NULL COLUMN COUNTS ===")
print(df[inspect_cols].notna().sum().to_string())

for col in inspect_cols:
    non_null = df[df[col].notna()]
    if non_null.empty:
        continue

    print(f"\n=== EXAMPLES: {col} ===")
    print(
        non_null[
            ["match_id", "inning", "over_ball",
             "runs_extras", "runs_total", col]
        ].head(8).to_string(index=False)
    )

# 2. Check extras and dismissal distributions.
print("\n=== EXTRAS DISTRIBUTION ===")
print(
    df["runs_extras"]
    .value_counts(dropna=False)
    .sort_index()
)

print("\n=== WICKET TYPES ===")
print(
    df["wicket_kind"]
    .value_counts(dropna=False)
)

# 3. Check ball numbering per over.
over_summary = (
    df.groupby(
        ["match_id", "inning", "over"],
        dropna=False
    )
    .agg(
        events=("match_id", "size"),
        min_ball=("ball_num", "min"),
        max_ball=("ball_num", "max"),
        distinct_ball_numbers=("ball_num", "nunique"),
        extra_runs=("runs_extras", "sum")
    )
    .reset_index()
)

print("\n=== OVERS WITH MORE THAN 6 EVENTS ===")
long_overs = over_summary[
    over_summary["events"] > 6
]
print("Count:", len(long_overs))
print(long_overs.head(15).to_string(index=False))

print("\n=== BALL NUMBER DISTRIBUTION ===")
print(
    df["ball_num"]
    .value_counts()
    .sort_index()
)

# 4. Check innings lengths and totals.
innings = (
    df.groupby(
        ["match_id", "inning", "batting_team"],
        dropna=False
    )
    .agg(
        recorded_events=("match_id", "size"),
        total_runs=("runs_total", "sum"),
        wicket_events=("is_wicket", "sum"),
        extras=("runs_extras", "sum")
    )
    .reset_index()
)

print("\n=== INNINGS SUMMARY ===")
print(innings.to_string(index=False))

# 5. Identify unusual wicket records.
df["wicket_flag"] = (
    df["is_wicket"]
    .astype(str)
    .str.lower()
    .eq("true")
)

mismatch = df[
    df["wicket_flag"] != df["wicket_kind"].notna()
]

print("\n=== WICKET FLAG MISMATCHES ===")
print("Count:", len(mismatch))
print(mismatch.head(10).to_string(index=False))

# 6. Export reports.
over_summary.to_csv(
    REPORT / "rr_2026_over_audit.csv", index=False
)
innings.to_csv(
    REPORT / "rr_2026_innings_audit.csv", index=False
)
long_overs.to_csv(
    REPORT / "rr_2026_long_overs.csv", index=False
)

print("\nAudit reports saved.")
