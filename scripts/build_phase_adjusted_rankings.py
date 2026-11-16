
from pathlib import Path
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data" / "processed" / "rr_official"

states = pd.read_csv(
    DATA / "match_states_preliminary.csv",
    low_memory=False
)

# Load IPL 2026 squad mapping
roster = pd.read_csv(
    DATA / "ipl_2026_roster_proxy.csv",
    low_memory=False
)

# Load official player identity registry
players = pd.read_csv(
    DATA / "players_clean.csv",
    low_memory=False
)

# Validate required fields
required = {"player_id", "ipl_2026_team"}
missing = required - set(roster.columns)

if missing:
    raise ValueError(f"Missing roster columns: {missing}")

# Prevent duplicate player_name columns if the
# roster already contains a different name field.
roster = roster.drop(
    columns=["player_name"],
    errors="ignore"
)

# Attach player names using official player IDs
roster = roster.merge(
    players[["player_id", "player_name"]].drop_duplicates("player_id"),
    on="player_id",
    how="left",
    validate="many_to_one"
)

roster["player_name"] = roster["player_name"].fillna(
    "Unknown Player"
)

roster = roster[
    ["player_id", "player_name", "ipl_2026_team"]
].drop_duplicates("player_id")

print("IPL roster loaded:", len(roster))
print(
    "Missing player names:",
    roster["player_name"].eq(" Player").sum()
)

states = states[
    states["pressure_eligible"].astype(str).str.lower().eq("true")
].copy()

states["high"] = states["structural_pressure_level"].isin(
    ["High", "Extreme"]
)

states["extra"] = (
    states["extras_type"].fillna("").astype(str).str.lower()
)

states["batting_ball"] = ~states["extra"].eq("wide")
states["legal"] = ~states["extra"].isin(
    ["wide", "overstep", "other"]
)

kind = (
    states["dismissal_type"].fillna("")
    .astype(str).str.lower()
    .str.replace(" ", "", regex=False)
)

states["bowler_wicket"] = (
    kind.ne("")
    & ~kind.isin([
        "runout", "retiredout", "retireout",
        "retiredhurt", "obstructingthefield"
    ])
)

# Phase-specific league expectation.
# Uses the same pressure definition for every player.
bat_ref = states[
    states["high"] & states["batting_ball"]
].groupby("pressure_phase").agg(
    runs=("runs", "sum"),
    balls=("batting_ball", "sum")
)

bat_ref["expected_runs_per_ball"] = (
    bat_ref["runs"] / bat_ref["balls"]
)

bowl_ref = states[
    states["high"] & states["legal"]
].groupby("pressure_phase").agg(
    runs=("runs", "sum"),
    balls=("legal", "sum"),
    wickets=("bowler_wicket", "sum")
)

bowl_ref["expected_runs_per_ball"] = (
    bowl_ref["runs"] / bowl_ref["balls"]
)
bowl_ref["expected_wickets_per_ball"] = (
    bowl_ref["wickets"] / bowl_ref["balls"]
)

# -----------------------------------------
# Batting: actual minus expected runs
# -----------------------------------------
bat = states[
    states["high"] & states["batting_ball"]
].copy()

bat["expected_rate"] = bat["pressure_phase"].map(
    bat_ref["expected_runs_per_ball"]
)

bat["runs_above_expected"] = (
    bat["runs"] - bat["expected_rate"]
)

bat = bat.groupby("striker_id").agg(
    matches=("match_id", "nunique"),
    balls=("batting_ball", "sum"),
    runs=("runs", "sum"),
    runs_above_expected=("runs_above_expected", "sum")
).reset_index().rename(columns={"striker_id": "player_id"})

bat["strike_rate"] = 100 * bat["runs"] / bat["balls"]
bat["impact_per_100_balls"] = (
    100 * bat["runs_above_expected"] / bat["balls"]
)

# -----------------------------------------
# Bowling: runs prevented and wickets gained
# -----------------------------------------
bowl = states[
    states["high"] & states["legal"]
].copy()

bowl["expected_run_rate"] = bowl["pressure_phase"].map(
    bowl_ref["expected_runs_per_ball"]
)

bowl["expected_wicket_rate"] = bowl["pressure_phase"].map(
    bowl_ref["expected_wickets_per_ball"]
)

bowl["runs_prevented"] = (
    bowl["expected_run_rate"] - bowl["runs"]
)

bowl["wickets_above_expected"] = (
    bowl["bowler_wicket"].astype(int)
    - bowl["expected_wicket_rate"]
)

bowl = bowl.groupby("bowler_id").agg(
    matches=("match_id", "nunique"),
    balls=("legal", "sum"),
    wickets=("bowler_wicket", "sum"),
    runs_prevented=("runs_prevented", "sum"),
    wickets_above_expected=("wickets_above_expected", "sum")
).reset_index().rename(columns={"bowler_id": "player_id"})

bowl["runs_prevented_per_over"] = (
    6 * bowl["runs_prevented"] / bowl["balls"]
)

bowl["extra_wickets_per_100_balls"] = (
    100 * bowl["wickets_above_expected"] / bowl["balls"]
)

# -----------------------------------------
# Reliability adjustment
# -----------------------------------------
def reliability(n, matches, k=120):
    ball_weight = n / (n + k)
    match_weight = np.minimum(matches / 10, 1)
    return ball_weight * match_weight

bat["reliability"] = reliability(
    bat["balls"], bat["matches"]
)

bowl["reliability"] = reliability(
    bowl["balls"], bowl["matches"]
)

bat["adjusted_score"] = (
    bat["impact_per_100_balls"] * bat["reliability"]
)

# Heuristic combined bowling index.
# 10 points per extra wicket per 100 balls;
# weights are provisional and need sensitivity tests.
bowl["raw_impact"] = (
    bowl["runs_prevented_per_over"]
    + 0.10 * bowl["extra_wickets_per_100_balls"]
)

bowl["adjusted_score"] = (
    bowl["raw_impact"] * bowl["reliability"]
)


# -----------------------------------------
# Provisional non-IPL squad candidate pool
# -----------------------------------------
players = pd.read_csv(
    DATA / "players_clean.csv",
    low_memory=False
)

names = (
    players[["player_id", "player_name"]]
    .dropna(subset=["player_id"])
    .drop_duplicates(subset=["player_id"])
)

# The roster is an EXCLUSION list.
# Players absent from the 2026 roster may still
# require independent current-contract checks.
ipl_ids = set(
    pd.to_numeric(
        roster["player_id"], errors="coerce"
    ).dropna().astype("int64")
)

def build_candidate_pool(df):
    df = df.copy()

    df["player_id"] = pd.to_numeric(
        df["player_id"], errors="coerce"
    )

    df = df[
        df["player_id"].notna()
        & ~df["player_id"].isin(ipl_ids)
    ].copy()

    df = df.merge(
        names,
        on="player_id",
        how="left",
        validate="many_to_one"
    )

    df = df[
        (df["balls"] >= 30)
        & (df["matches"] >= 3)
    ].copy()

    return df.sort_values(
        ["adjusted_score", "balls"],
        ascending=[False, False]
    ).reset_index(drop=True)

bat = build_candidate_pool(bat)
bowl = build_candidate_pool(bowl)

bat.insert(0, "rank", range(1, len(bat) + 1))
bowl.insert(0, "rank", range(1, len(bowl) + 1))

bat["eligibility_status"] = (
    "NOT_IN_IPL_2026_MAPPING_UNVERIFIED"
)
bowl["eligibility_status"] = (
    "NOT_IN_IPL_2026_MAPPING_UNVERIFIED"
)

bat.to_csv(
    DATA / "unattached_batting_candidates.csv",
    index=False
)

bowl.to_csv(
    DATA / "unattached_bowling_candidates.csv",
    index=False
)

print("\n=== TOP 25 BATTING CANDIDATES ===")
print(
    bat[[
        "rank", "player_name", "matches",
        "balls", "strike_rate",
        "impact_per_100_balls", "adjusted_score"
    ]].head(25).round(2).to_string(index=False)
)

print("\n=== TOP 25 BOWLING CANDIDATES ===")
print(
    bowl[[
        "rank", "player_name", "matches",
        "balls", "wickets",
        "runs_prevented_per_over",
        "adjusted_score"
    ]].head(25).round(2).to_string(index=False)
)

print("\nBatting candidates:", len(bat))
print("Bowling candidates:", len(bowl))
print(
    "\nWARNING: Absence from 2026 roster mapping "
    "does not confirm current free-agent status."
)
