
from pathlib import Path
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data" / "processed"

balls = pd.read_csv(
    DATA / "rr_2026_deliveries.csv",
    low_memory=False
)

matches = pd.read_csv(
    DATA / "rr_2026_matches.csv",
    low_memory=False
)

RR = "Rajasthan Royals"
PHASES = ["powerplay", "middle", "death"]

# Legal-ball classification from our previous audit.
balls["is_legal"] = ~(
    balls["extras_detail"].notna()
    | balls["c1"].notna()
)

balls["is_team_wicket"] = (
    balls["wicket_kind"].notna()
    & ~balls["wicket_kind"].fillna("").str.lower()
      .isin(["retired hurt"])
)

balls["is_boundary"] = balls["runs_batter"].isin([4, 6])

balls["rr_role"] = balls["batting_team"].apply(
    lambda team: "Batting" if team == RR else "Bowling"
)

# Match result classification.
matches["result"] = matches["winner"].apply(
    lambda winner:
        "No result" if pd.isna(winner)
        else "Win" if winner == RR
        else "Loss"
)

# The cleaned delivery dataset already has match metadata.
# Only merge the new result classification.

balls = balls.merge(
    matches[["match_id", "result"]],
    on="match_id",
    how="left",
    validate="many_to_one"
)

balls["opponent"] = balls.apply(
    lambda row:
        row["team2"] if row["team1"] == RR
        else row["team1"],
    axis=1
)

# Per-match, per-phase performance.
summary = (
    balls.groupby(
        ["match_id", "date", "opponent",
         "result", "rr_role", "phase"],
        as_index=False
    )
    .agg(
        runs=("runs_total", "sum"),
        balls=("is_legal", "sum"),
        wickets=("is_team_wicket", "sum"),
        boundaries=("is_boundary", "sum")
    )
)

summary["run_rate"] = (
    6 * summary["runs"]
    / summary["balls"].replace(0, float("nan"))
)

summary.to_csv(
    DATA / "rr_2026_match_phase_analysis.csv",
    index=False
)

# Win / loss summaries, weighted by legal deliveries.
result_summary = (
    summary.groupby(
        ["result", "rr_role", "phase"],
        as_index=False
    )[["runs", "balls", "wickets", "boundaries"]]
    .sum()
)

result_summary["run_rate"] = (
    6 * result_summary["runs"]
    / result_summary["balls"].replace(0, float("nan"))
).round(2)

print("\n=== WINS VS LOSSES ===")
print(
    result_summary[
        ["result", "rr_role", "phase",
         "runs", "balls", "wickets", "run_rate"]
    ].to_string(index=False)
)

# Reshape for match-level net phase analysis.
pivot = summary.pivot_table(
    index=["match_id", "date", "opponent", "result", "phase"],
    columns="rr_role",
    values=["runs", "balls", "wickets"],
    aggfunc="sum"
)

pivot.columns = [
    f"{metric}_{role.lower()}"
    for metric, role in pivot.columns
]
pivot = pivot.reset_index()

pivot["batting_rate"] = (
    6 * pivot["runs_batting"]
    / pivot["balls_batting"].replace(0, float("nan"))
)

pivot["conceded_rate"] = (
    6 * pivot["runs_bowling"]
    / pivot["balls_bowling"].replace(0, float("nan"))
)

pivot["net_rate"] = (
    pivot["batting_rate"] - pivot["conceded_rate"]
).round(2)

pivot["net_runs"] = (
    pivot["runs_batting"] - pivot["runs_bowling"]
)

pivot.to_csv(
    DATA / "rr_2026_match_phase_net.csv",
    index=False
)

# Identify phase with the lowest net run rate per match.
weakest = (
    pivot.dropna(subset=["net_rate"])
    .sort_values("net_rate")
    .groupby("match_id")
    .first()
    .reset_index()
)

print("\n=== WEAKEST PHASE PER MATCH ===")
print(
    weakest[
        ["date", "opponent", "result",
         "phase", "net_rate", "net_runs"]
    ].to_string(index=False)
)

# Count recurring weaknesses in losses.
losses = weakest[weakest["result"] == "Loss"]

print("\n=== RECURRING WEAK PHASES IN DEFEATS ===")
print(losses["phase"].value_counts())

print("\n=== MATCH RESULT COUNTS ===")
print(matches["result"].value_counts(dropna=False))

print("\nAnalysis saved successfully.")
