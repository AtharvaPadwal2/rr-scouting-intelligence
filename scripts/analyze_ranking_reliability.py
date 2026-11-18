"""RR SupeRR Selector — match consistency and ranking-sensitivity audit.

Run from any directory:
    python scripts/analyze_ranking_reliability.py

Input: data/processed/rr_official/match_states_preliminary.csv,
       data/processed/rr_official/ipl_2026_roster_proxy.csv,
       data/processed/rr_official/players_clean.csv

All rankings remain provisional: structural pressure, unverified extras,
combined competitions, historical IPL 2026 squad mapping.
"""
from pathlib import Path
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data" / "processed" / "rr_official"
DATA.mkdir(parents=True, exist_ok=True)

states = pd.read_csv(DATA / "match_states_preliminary.csv", low_memory=False)
roster = pd.read_csv(DATA / "ipl_2026_roster_proxy.csv", low_memory=False)
players = pd.read_csv(DATA / "players_clean.csv", low_memory=False)

required_states = {
    "match_id", "striker_id", "bowler_id", "runs", "extras_type",
    "dismissal_type", "pressure_eligible", "structural_pressure_level", "pressure_phase"
}
if missing := (required_states - set(states.columns)):
    raise ValueError(f"Missing match state columns: {sorted(missing)}")
if missing := ({"player_id", "ipl_2026_team"} - set(roster.columns)):
    raise ValueError(f"Missing roster columns: {sorted(missing)}")

# Use the official player registry to avoid duplicate/missing name fields.
roster = roster.drop(columns=["player_name"], errors="ignore")
roster = roster[["player_id", "ipl_2026_team"]].drop_duplicates("player_id")
roster = roster.merge(
    players[["player_id", "player_name"]].drop_duplicates("player_id"),
    on="player_id", how="left", validate="many_to_one"
)
roster["player_name"] = roster["player_name"].fillna("Unknown Player")


# FULL_OFFICIAL_PLAYER_POOL
# All official players are eligible, regardless of IPL contract.
all_players = (
    players[["player_id", "player_name"]]
    .dropna(subset=["player_id"])
    .drop_duplicates("player_id")
)

roster = all_players.merge(
    roster[["player_id", "ipl_2026_team"]],
    on="player_id",
    how="left",
    validate="one_to_one"
)

roster["ipl_2026_team"] = (
    roster["ipl_2026_team"]
    .fillna("Not roster-mapped")
)

states = states.loc[
    states["pressure_eligible"].astype(str).str.lower().eq("true")
].copy()
states = states.loc[
    states["structural_pressure_level"].isin(["High", "Extreme"])
].copy()
states["extra"] = states["extras_type"].fillna("").astype(str).str.lower().str.strip()
states["runs"] = pd.to_numeric(states["runs"], errors="coerce")
kind = (states["dismissal_type"].fillna("").astype(str).str.lower()
        .str.replace(" ", "", regex=False).str.strip())
states["bowler_wicket"] = kind.ne("") & ~kind.isin({
    "runout", "retiredout", "retireout", "retiredhurt", "obstructingthefield"
})
states["batting_ball"] = states["extra"].ne("wide")
states["legal_ball"] = ~states["extra"].isin({"wide", "overstep", "other"})

# Reference rates from all players, matching the previous phase-adjusted script.
# This is explicitly not competition-adjusted or score-verified.
bat_eligible = states.loc[states["batting_ball"] & states["runs"].notna()].copy()
bat_reference = (bat_eligible.groupby("pressure_phase")["runs"].mean())
bat_eligible["expected_runs"] = bat_eligible["pressure_phase"].map(bat_reference)
bat_eligible["run_impact"] = bat_eligible["runs"] - bat_eligible["expected_runs"]

bowl_eligible = states.loc[states["legal_ball"] & states["runs"].notna()].copy()
bowl_reference = bowl_eligible.groupby("pressure_phase").agg(
    mean_runs=("runs", "mean"), mean_wickets=("bowler_wicket", "mean")
)
bowl_eligible["expected_runs"] = bowl_eligible["pressure_phase"].map(bowl_reference["mean_runs"])
bowl_eligible["expected_wickets"] = bowl_eligible["pressure_phase"].map(bowl_reference["mean_wickets"])
bowl_eligible["run_impact"] = bowl_eligible["expected_runs"] - bowl_eligible["runs"]
bowl_eligible["wicket_impact"] = (
    bowl_eligible["bowler_wicket"].astype(int) - bowl_eligible["expected_wickets"]
)

# Match-level aggregates allow us to measure repeatability, not just overall averages.
bat_match = bat_eligible.groupby(["striker_id", "match_id"], as_index=False).agg(
    balls=("batting_ball", "size"), runs=("runs", "sum"),
    raw_impact=("run_impact", "sum")
).rename(columns={"striker_id": "player_id"})
bowl_match = bowl_eligible.groupby(["bowler_id", "match_id"], as_index=False).agg(
    balls=("legal_ball", "size"), wickets=("bowler_wicket", "sum"),
    raw_impact=("run_impact", "sum"), wicket_impact=("wicket_impact", "sum")
).rename(columns={"bowler_id": "player_id"})


def calculate(match_table, discipline):
    match_table = match_table.merge(
        roster, on="player_id", how="inner", validate="many_to_one"
    )
    # Single-match impacts are volatile for very short appearances: flag them.
    match_table["meaningful_match"] = match_table["balls"] >= 6
    if discipline == "batting":
        match_table["match_impact"] = 100 * match_table["raw_impact"] / match_table["balls"]
    else:
        # Same units and wicket weight as the existing exploratory ranking script.
        match_table["match_impact"] = (
            6 * match_table["raw_impact"] / match_table["balls"]
            + 0.10 * 100 * match_table["wicket_impact"] / match_table["balls"]
        )
    match_table["positive_match"] = (
        (match_table["match_impact"] > 0) & match_table["meaningful_match"]
    )

    agg = match_table.groupby("player_id", as_index=False).agg(
        matches=("match_id", "nunique"),
        balls=("balls", "sum"),
        impact_sum=("raw_impact", "sum"),
        meaningful_matches=("meaningful_match", "sum"),
        positive_matches=("positive_match", "sum"),
    )
    if discipline == "batting":
        agg["raw_score"] = 100 * agg["impact_sum"] / agg["balls"]
    else:
        wickets = match_table.groupby("player_id")["wicket_impact"].sum().rename("wicket_impact_sum")
        agg = agg.merge(wickets, on="player_id")
        agg["raw_score"] = (
            6 * agg["impact_sum"] / agg["balls"]
            + 0.10 * 100 * agg["wicket_impact_sum"] / agg["balls"]
        )
    agg["positive_match_pct"] = np.where(
        agg["meaningful_matches"] > 0,
        100 * agg["positive_matches"] / agg["meaningful_matches"], np.nan
    )
    agg = agg.merge(roster, on="player_id", validate="one_to_one")
    agg["discipline"] = discipline
    return match_table, agg

bat_match, batting = calculate(bat_match, "batting")
bowl_match, bowling = calculate(bowl_match, "bowling")


def ranked_scenario(table, minimum_balls, k, wicket_weight=0.10):
    qualified = table.loc[
        (table["balls"] >= minimum_balls) & (table["matches"] >= 3)
    ].copy()
    qualified["reliability"] = (
        qualified["balls"] / (qualified["balls"] + k)
        * np.minimum(qualified["matches"] / 10, 1)
    )
    if "wicket_impact_sum" in qualified.columns:
        qualified["raw_scenario"] = (
            6 * qualified["impact_sum"] / qualified["balls"]
            + wicket_weight * 100 * qualified["wicket_impact_sum"] / qualified["balls"]
        )
    else:
        qualified["raw_scenario"] = qualified["raw_score"]
    qualified["adjusted_score"] = qualified["raw_scenario"] * qualified["reliability"]
    qualified = qualified.sort_values(
        ["adjusted_score", "balls", "player_id"], ascending=[False, False, True]
    ).reset_index(drop=True)
    qualified["rank"] = np.arange(1, len(qualified) + 1)
    return qualified

# Nine straightforward sensitivity scenarios: three sample cutoffs x three shrinkage strengths.
# Additional wicket-weight scenarios for bowlers are tested separately.
scenarios = [(f"min{minimum}_k{k}", minimum, k, 0.10)
             for minimum in (30, 60, 100) for k in (60, 120, 240)]


def stability(table, discipline):
    runs = []
    for label, minimum, k, weight in scenarios:
        run = ranked_scenario(table, minimum, k, weight)
        run["scenario"] = label
        runs.append(run[["player_id", "rank", "adjusted_score", "scenario"]])
    if discipline == "bowling":
        for weight in (0.05, 0.20):
            label = f"min30_k120_w{weight:.2f}"
            run = ranked_scenario(table, 30, 120, weight)
            run["scenario"] = label
            runs.append(run[["player_id", "rank", "adjusted_score", "scenario"]])
    combined = pd.concat(runs, ignore_index=True)
    summary = combined.groupby("player_id", as_index=False).agg(
        scenarios_qualified=("scenario", "nunique"),
        times_top_10=("rank", lambda s: int(s.le(10).sum())),
        best_rank=("rank", "min"),
        worst_rank_when_qualified=("rank", "max"),
        median_rank_when_qualified=("rank", "median"),
    )
    total_scenarios = len(runs)
    summary["top_10_scenario_pct"] = 100 * summary["times_top_10"] / total_scenarios
    summary["qualification_pct"] = 100 * summary["scenarios_qualified"] / total_scenarios
    base = ranked_scenario(table, 30, 120).rename(columns={
        "rank": "base_rank", "adjusted_score": "base_adjusted_score"
    })
    output = base.merge(summary, on="player_id", how="left", validate="one_to_one")
    output["total_scenarios"] = total_scenarios
    return combined, output

bat_scenarios, bat_stability = stability(batting, "batting")
bowl_scenarios, bowl_stability = stability(bowling, "bowling")

bat_match.to_csv(DATA / "pressure_batting_match_consistency.csv", index=False)
bowl_match.to_csv(DATA / "pressure_bowling_match_consistency.csv", index=False)
bat_stability.to_csv(DATA / "pressure_batting_reliability.csv", index=False)
bowl_stability.to_csv(DATA / "pressure_bowling_reliability.csv", index=False)
bat_scenarios.to_csv(DATA / "pressure_batting_sensitivity.csv", index=False)
bowl_scenarios.to_csv(DATA / "pressure_bowling_sensitivity.csv", index=False)

for title, table in (("BATTERS", bat_stability), ("BOWLERS", bowl_stability)):
    print(f"\n=== {title}: BASE TOP 20 + STABILITY ===")
    print(table[[
        "base_rank", "player_name", "ipl_2026_team", "balls", "matches",
        "base_adjusted_score", "positive_match_pct", "top_10_scenario_pct",
        "best_rank", "worst_rank_when_qualified"
    ]].head(20).round(2).to_string(index=False))

print("\n=== ANALYSIS COVERAGE ===")
print("Batters in base ranking:", len(bat_stability))
print("Bowlers in base ranking:", len(bowl_stability))
print("Batting scenarios:", bat_scenarios["scenario"].nunique())
print("Bowling scenarios:", bowl_scenarios["scenario"].nunique())
print("\nOutputs saved under:", DATA)
print("CAUTION: Structural-pressure proxy, unverified extras and IPL 2026 roster proxy.")
print("Positive-match percentage uses matches with at least 6 relevant balls.")
print("Scenarios that fail the sample cutoff count as NOT top 10.")
