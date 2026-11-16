
from pathlib import Path
import json
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
EXT = ROOT / "data/processed/external"
SMAT = ROOT / "data/processed/smat_all_deliveries.csv"
OUT = ROOT / "data/processed/scoring"
OUT.mkdir(parents=True, exist_ok=True)

EXTERNAL_IDS = {
    "eade4650": "Daryl Mitchell",
    "972f217b": "Bevon Jacobs",
    "7068c81e": "Matthew Fisher",
    "4175d211": "Shamar Springer",
}

SMAT_NAMES = {
    "Karan Lal": "Karan Lal",
    "Anmolpreet Singh": "Anmolpreet Singh",
    "Tanush Kotian": "Tanush Kotian",
    "Simarjeet Singh": "Simarjeet Singh",
}

ROLES = {
    "Daryl Mitchell": "batting",
    "Bevon Jacobs": "batting",
    "Matthew Fisher": "bowling",
    "Shamar Springer": "bowling",
    "Karan Lal": "batting",
    "Anmolpreet Singh": "batting",
    "Tanush Kotian": "bowling",
    "Simarjeet Singh": "bowling",
}

BOWLER_WICKETS = {
    "bowled", "caught", "caught and bowled",
    "lbw", "stumped", "hit wicket",
}

PHASE_WEIGHT = {
    "powerplay": 1.0,
    "middle": 1.15,
    "death": 1.40,
}

def phase_from_over(over):
    if over < 6:
        return "powerplay"
    if over < 15:
        return "middle"
    return "death"

def standardize_external(league):
    df = pd.read_csv(
        EXT / f"{league}_deliveries.csv",
        low_memory=False,
        dtype={"striker_id": str, "bowler_id": str},
    )

    df["striker_key"] = df["striker_id"]
    df["bowler_key"] = df["bowler_id"]
    df["source"] = league

    for c in ["runs_off_bat", "total_runs", "wides",
              "noballs", "wicket_count"]:
        df[c] = pd.to_numeric(df[c], errors="coerce").fillna(0)

    df["bowler_wicket"] = df["dismissal_types"].fillna("").apply(
        lambda s: sum(
            kind.strip().lower() in BOWLER_WICKETS
            for kind in str(s).split("|")
        )
    )

    return df

def standardize_smat():
    df = pd.read_csv(SMAT, low_memory=False)

    df["striker_key"] = df["striker"].astype(str).str.strip()
    df["bowler_key"] = df["bowler"].astype(str).str.strip()
    df["source"] = "smat"

    for c in ["runs_off_bat", "extras", "wides",
              "noballs"]:
        df[c] = pd.to_numeric(df[c], errors="coerce").fillna(0)

    df["total_runs"] = df["runs_off_bat"] + df["extras"]

    df["wicket_count"] = (
        df["wicket_type"].notna().astype(int)
        + df["other_wicket_type"].notna().astype(int)
    )

    df["bowler_wicket"] = (
        df["wicket_type"].fillna("")
        .astype(str).str.lower().isin(BOWLER_WICKETS).astype(int)
        + df["other_wicket_type"].fillna("")
        .astype(str).str.lower().isin(BOWLER_WICKETS).astype(int)
    )

    # Cricsheet uses zero-based over notation.
    df["over"] = np.floor(
        pd.to_numeric(df["ball"], errors="coerce")
    )

    df["delivery_index"] = df.groupby(
        ["match_id", "innings"], sort=False
    ).cumcount()

    df["match_date"] = df["start_date"]
    return df

frames = [
    standardize_external(league)
    for league in ["super_smash", "cpl", "bbl", "t20_blast"]
]
frames.append(standardize_smat())

df = pd.concat(frames, ignore_index=True)

df["bat_ball"] = df["wides"].eq(0).astype(int)
df["bowl_ball"] = (
    df["wides"].eq(0) & df["noballs"].eq(0)
).astype(int)

df["bowler_runs"] = (
    df["runs_off_bat"] + df["wides"] + df["noballs"]
)

df["phase"] = df["over"].apply(phase_from_over)

df = df.sort_values(
    ["source", "match_id", "innings", "delivery_index"]
).reset_index(drop=True)

groups = df.groupby(
    ["source", "match_id", "innings"], sort=False
)

df["wickets_before"] = (
    groups["wicket_count"].cumsum() - df["wicket_count"]
)

# Phase + wickets-down contextual proxy.
df["pressure_weight"] = df["phase"].map(PHASE_WEIGHT)
df["pressure_weight"] *= np.where(
    df["wickets_before"] >= 5, 1.25,
    np.where(df["wickets_before"] >= 3, 1.10, 1.0)
)

# League-specific, phase-specific baselines.
baselines = df.groupby(
    ["source", "phase"], as_index=False
).agg(
    bat_runs=("runs_off_bat", "sum"),
    bat_balls=("bat_ball", "sum"),
    bowl_runs=("bowler_runs", "sum"),
    bowl_balls=("bowl_ball", "sum"),
    wickets=("bowler_wicket", "sum"),
)

baselines["bat_expected"] = (
    baselines["bat_runs"] / baselines["bat_balls"].clip(lower=1)
)
baselines["bowl_expected"] = (
    baselines["bowl_runs"] / baselines["bowl_balls"].clip(lower=1)
)
baselines["wicket_expected"] = (
    baselines["wickets"] / baselines["bowl_balls"].clip(lower=1)
)

df = df.merge(
    baselines[[
        "source", "phase", "bat_expected",
        "bowl_expected", "wicket_expected"
    ]],
    on=["source", "phase"],
    how="left",
    validate="many_to_one",
)

player_results = []
match_results = []

for name, role in ROLES.items():
    if name in EXTERNAL_IDS.values():
        ids = [
            pid for pid, player in EXTERNAL_IDS.items()
            if player == name
        ]
        p = df[
            df["source"].ne("smat")
            & df[
                "striker_key" if role == "batting" else "bowler_key"
            ].isin(ids)
        ].copy()
    else:
        p = df[
            df["source"].eq("smat")
            & df[
                "striker_key" if role == "batting" else "bowler_key"
            ].eq(name)
        ].copy()

    if p.empty:
        continue

    if role == "batting":
        p["balls"] = p["bat_ball"]
        p["impact"] = (
            p["runs_off_bat"] - p["bat_expected"] * p["balls"]
        )
    else:
        p["balls"] = p["bowl_ball"]
        p["impact"] = (
            p["bowl_expected"] * p["balls"]
            - p["bowler_runs"]
            + 15 * (
                p["bowler_wicket"]
                - p["wicket_expected"] * p["balls"]
            )
        )

    p["weighted_impact"] = (
        p["impact"] * p["pressure_weight"]
    )

    matches = p.groupby(
        ["source", "match_id"], as_index=False
    ).agg(
        balls=("balls", "sum"),
        impact=("impact", "sum"),
        pressure_impact=("weighted_impact", "sum"),
    )

    matches = matches[matches["balls"] > 0].copy()

    if matches.empty:
        continue

    matches["player"] = name
    matches["role"] = role
    matches["impact_per_ball"] = (
        matches["impact"] / matches["balls"]
    )

    match_results.append(matches)

    balls = int(matches["balls"].sum())
    n = len(matches)

    pressure_impact = (
        matches["pressure_impact"].sum() / balls
    )

    sample_weight = balls / (balls + 120)
    adjusted = pressure_impact * sample_weight

    # Preliminary, bounded score normalization.
    pressure = float(np.clip(
        3 + 1.5 * np.tanh(adjusted / 0.45),
        0, 5
    ))

    values = matches["impact_per_ball"].to_numpy()
    median = np.median(values)
    mad = float(np.median(np.abs(values - median)))

    positive = int((matches["impact"] > 0).sum())
    positive_rate = (positive + 2) / (n + 4)
    stability = 1 / (1 + mad / 0.30)
    n_weight = n / (n + 8)

    reliability = float(np.clip(
        5 * (
            0.55 * positive_rate
            + 0.45 * stability
        ) * n_weight
        + 2.5 * (1 - n_weight),
        0, 5
    ))

    player_results.append({
        "player": name,
        "role": role,
        "matches": n,
        "balls": balls,
        "positive_matches": positive,
        "positive_match_rate": round(positive_rate, 3),
        "sample_weight": round(sample_weight, 3),
        "adjusted_pressure_impact": round(adjusted, 4),
        "match_impact_mad": round(mad, 4),
        "model_pressure": round(pressure, 2),
        "model_reliability": round(reliability, 2),
        "model_overall": round(pressure + reliability, 2),
    })

scores = pd.DataFrame(player_results)
scores.to_csv(
    OUT / "unified_statistical_pri.csv", index=False
)

pd.concat(match_results, ignore_index=True).to_csv(
    OUT / "unified_match_impacts.csv", index=False
)

print("\n=== UNIFIED STATISTICAL PRI ===")
print(scores.to_string(index=False))
print("\nPlayers with statistical scores:", len(scores))
print("Saved: unified_statistical_pri.csv")
print("Saved: unified_match_impacts.csv")
