
from pathlib import Path
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data" / "processed"

df = pd.read_csv(
    DATA / "ipl_2026_clean.csv",
    low_memory=False
)

# Apply the extras classification established by our audit.
df["is_legal"] = ~(
    df["extras_detail"].notna()
    | df["c1"].notna()
)

df["team_wicket"] = (
    df["wicket_kind"].notna()
    & df["wicket_kind"].ne("retired hurt")
)

df["boundary"] = df["runs_batter"].isin([4, 6])
df["dot_ball"] = (
    df["is_legal"] & df["runs_total"].eq(0)
)

# Team batting and bowling performances.
batting = df.rename(columns={
    "batting_team": "team"
}).copy()

batting["discipline"] = "batting"

bowling = df.rename(columns={
    "bowling_team": "team"
}).copy()

bowling["discipline"] = "bowling"

combined = pd.concat(
    [batting, bowling],
    ignore_index=True
)

summary = (
    combined.groupby(
        ["team", "discipline", "phase"]
    )
    .agg(
        runs=("runs_total", "sum"),
        balls=("is_legal", "sum"),
        wickets=("team_wicket", "sum"),
        boundaries=("boundary", "sum"),
        dots=("dot_ball", "sum")
    )
    .reset_index()
)

summary["run_rate"] = (
    6 * summary["runs"] / summary["balls"]
)

summary["boundary_pct"] = (
    100 * summary["boundaries"] / summary["balls"]
)

summary["dot_pct"] = (
    100 * summary["dots"] / summary["balls"]
)

# Batting: higher run rate is better.
# Bowling: lower conceded rate is better.
summary["league_rank"] = (
    summary.groupby(["discipline", "phase"])["run_rate"]
    .rank(
        ascending=False,
        method="min"
    )
)

bowling_mask = summary["discipline"].eq("bowling")

summary.loc[bowling_mask, "league_rank"] = (
    summary[bowling_mask]
    .groupby("phase")["run_rate"]
    .rank(ascending=True, method="min")
)

# Weighted league benchmark, not an average of team rates.
benchmarks = (
    summary.groupby(["discipline", "phase"])
    [["runs", "balls"]]
    .sum()
    .reset_index()
)

benchmarks["league_run_rate"] = (
    6 * benchmarks["runs"] / benchmarks["balls"]
)

summary = summary.merge(
    benchmarks[
        ["discipline", "phase", "league_run_rate"]
    ],
    on=["discipline", "phase"],
    how="left"
)

summary["vs_league"] = (
    summary["run_rate"] - summary["league_run_rate"]
)

summary.to_csv(
    DATA / "ipl_2026_team_phase_comparison.csv",
    index=False
)

rr = summary[
    summary["team"].eq("Rajasthan Royals")
].copy()

rr = rr.sort_values(["discipline", "phase"])

print("\n=== RR VS IPL 2026 LEAGUE ===")
print(
    rr[
        ["discipline", "phase", "run_rate",
         "league_run_rate", "vs_league",
         "league_rank", "boundary_pct",
         "dot_pct", "wickets"]
    ].round(2).to_string(index=False)
)

print("\n=== ALL TEAMS: DEATH BOWLING ===")
death = summary[
    (summary["discipline"] == "bowling")
    & (summary["phase"] == "death")
].sort_values("league_rank")

print(
    death[
        ["team", "run_rate", "league_rank"]
    ].round(2).to_string(index=False)
)
