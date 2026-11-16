
from pathlib import Path
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data" / "processed"

df = pd.read_csv(
    DATA / "rr_2026_deliveries.csv",
    low_memory=False
)

rr = df[
    (df["bowling_team"] == "Rajasthan Royals")
    & (df["phase"] == "middle")
].copy()

rr["legal"] = ~(
    rr["extras_detail"].notna() | rr["c1"].notna()
)

kind = rr["wicket_kind"].fillna("").str.lower().str.strip()
rr["bowler_wicket"] = (
    kind.ne("")
    & ~kind.isin([
        "run out", "retired out",
        "retired hurt", "obstructing the field"
    ])
)

rr["boundary"] = rr["runs_batter"].isin([4, 6])
rr["dot"] = rr["legal"] & rr["runs_total"].eq(0)

stats = (
    rr.groupby("bowler")
    .agg(
        matches=("match_id", "nunique"),
        balls=("legal", "sum"),
        runs=("runs_total", "sum"),
        wickets=("bowler_wicket", "sum"),
        boundaries=("boundary", "sum"),
        dots=("dot", "sum")
    )
    .reset_index()
)

stats["run_rate"] = (
    6 * stats["runs"] / stats["balls"]
).round(2)

stats["bowling_sr"] = (
    stats["balls"]
    / stats["wickets"].replace(0, float("nan"))
).round(2)

stats["dot_pct"] = (
    100 * stats["dots"] / stats["balls"]
).round(2)

stats["boundary_pct"] = (
    100 * stats["boundaries"] / stats["balls"]
).round(2)

# Minimum 60 legal deliveries for an initial
# comparison; retain everyone in the CSV.
stats["sample_qualified"] = stats["balls"] >= 60

stats = stats.sort_values(
    ["sample_qualified", "run_rate"],
    ascending=[False, True]
)

stats.to_csv(
    DATA / "rr_2026_middle_bowlers.csv",
    index=False
)

print("\n=== MIDDLE-OVER BOWLERS ===")
print(stats.to_string(index=False))

print("\n=== QUALIFIED BOWLERS (60+ LEGAL BALLS) ===")
print(
    stats[stats["sample_qualified"]]
    .to_string(index=False)
)
