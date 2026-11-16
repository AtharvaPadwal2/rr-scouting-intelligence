
from pathlib import Path
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data" / "processed"

df = pd.read_csv(
    DATA / "rr_2026_deliveries.csv",
    low_memory=False
)

RR = "Rajasthan Royals"

df["result"] = df["match_winner"].apply(
    lambda x: "Win" if x == RR
    else "Loss" if pd.notna(x)
    else "No result"
)

df["wide"] = df["extras_detail"].notna()
df["no_ball"] = df["c1"].notna()
df["legal"] = ~(df["wide"] | df["no_ball"])

kind = df["wicket_kind"].fillna("").str.lower().str.strip()
df["bowler_wicket"] = (
    kind.ne("")
    & ~kind.isin([
        "run out", "retired out",
        "retired hurt", "obstructing the field"
    ])
)

df["boundary"] = df["runs_batter"].isin([4, 6])

# 1. RR BOWLERS: powerplay and death phases.
bowl = df[
    (df["bowling_team"] == RR)
    & df["phase"].isin(["powerplay", "death"])
].copy()

bowler_stats = (
    bowl.groupby(["bowler", "phase", "result"])
    .agg(
        matches=("match_id", "nunique"),
        legal_balls=("legal", "sum"),
        team_runs_conceded=("runs_total", "sum"),
        wickets=("bowler_wicket", "sum"),
        boundaries_conceded=("boundary", "sum")
    )
    .reset_index()
)

# Team runs conceded while this bowler delivered,
# not official individual bowling economy.
bowler_stats["team_run_rate"] = (
    6 * bowler_stats["team_runs_conceded"]
    / bowler_stats["legal_balls"].replace(0, float("nan"))
).round(2)

bowler_stats = bowler_stats.sort_values(
    ["phase", "result", "legal_balls"],
    ascending=[True, True, False]
)

# 2. RR BATTERS: death overs.
bat = df[
    (df["batting_team"] == RR)
    & (df["phase"] == "death")
].copy()

# Wides do not count as balls faced; no-balls do.
bat["ball_faced"] = ~bat["wide"]

batter_stats = (
    bat.groupby(["batter", "result"])
    .agg(
        matches=("match_id", "nunique"),
        runs=("runs_batter", "sum"),
        balls=("ball_faced", "sum"),
        boundaries=("boundary", "sum")
    )
    .reset_index()
)

batter_stats["strike_rate"] = (
    100 * batter_stats["runs"]
    / batter_stats["balls"].replace(0, float("nan"))
).round(2)

batter_stats = batter_stats.sort_values(
    ["result", "runs"],
    ascending=[True, False]
)

# Save full results.
bowler_stats.to_csv(
    DATA / "rr_2026_bowler_phase_analysis.csv",
    index=False
)
batter_stats.to_csv(
    DATA / "rr_2026_death_batters.csv",
    index=False
)

print("\n=== RR POWERPLAY BOWLERS ===")
print(
    bowler_stats[bowler_stats["phase"] == "powerplay"]
    .to_string(index=False)
)

print("\n=== RR DEATH BOWLERS ===")
print(
    bowler_stats[bowler_stats["phase"] == "death"]
    .to_string(index=False)
)

print("\n=== RR DEATH-OVER BATTERS ===")
print(batter_stats.to_string(index=False))

print("\nPlayer analysis saved.")
