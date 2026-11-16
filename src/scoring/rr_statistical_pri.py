
from pathlib import Path
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
BASE = ROOT / "data/processed/rr_official"
OUT = ROOT / "data/processed/scoring"
OUT.mkdir(parents=True, exist_ok=True)

# Roles and IDs already established in our coverage audit.
PLAYERS = {
    6628: ("Gerald Coetzee", "bowling"),
    6196: ("Josh Tongue", "bowling"),
    6398: ("Aaron Hardie", "batting"),
    6772: ("Chetan Sakariya", "bowling"),
    26909: ("Yash Dhull", "batting"),
}

WICKET_VALUE = 15.0
PRIOR_BALLS = 120

PHASE_WEIGHTS = {
    "powerplay": 1.00,
    "middle": 1.15,
    "death": 1.40,
}

df = pd.read_csv(
    BASE / "deliveries_clean.csv",
    low_memory=False
)

def flag(series):
    return series.astype(str).str.lower().eq("true")

# Restrict to T20 formats.
df = df[
    df["match_format"].astype(str)
    .str.upper().str.startswith("T20")
].copy()

# Build wicket context before excluding uncertain extras.
df["match_id"] = pd.to_numeric(
    df["match_id"], errors="coerce"
)

df["wicket_event"] = flag(df["is_team_wicket"]).astype(int)

df = df.sort_values([
    "match_id", "innings",
    "innings_ball_num", "overid", "over_ball_num"
]).reset_index(drop=True)

groups = df.groupby(
    ["match_id", "innings"], sort=False
)

df["wickets_before"] = (
    groups["wicket_event"].cumsum()
    - df["wicket_event"]
)

# Conservative subset: ordinary legal deliveries only.
df = df[
    df["extras_category"].astype(str).str.lower().eq("none")
    & flag(df["legal_ball_candidate"])
    & ~flag(df["flag_unknown_match"])
    & ~flag(df["flag_team_mismatch"])
].copy()

df["runs"] = pd.to_numeric(
    df["runs"], errors="coerce"
)

df = df[
    df["runs"].notna()
    & df["runs"].between(0, 7)
].copy()

df["bowler_wicket"] = (
    flag(df["is_bowler_wicket"]).astype(int)
)

df["phase"] = (
    df["phase"].astype(str).str.lower()
)

df = df[
    df["phase"].isin(PHASE_WEIGHTS)
].copy()

df["pressure_weight"] = (
    df["phase"].map(PHASE_WEIGHTS)
    * np.where(
        df["wickets_before"] >= 5, 1.25,
        np.where(
            df["wickets_before"] >= 3, 1.10, 1.0
        )
    )
)

# Baselines are computed on the same delivery subset.
baselines = df.groupby("phase").agg(
    deliveries=("runs", "size"),
    runs=("runs", "sum"),
    wickets=("bowler_wicket", "sum")
).reset_index()

baselines["run_expected"] = (
    baselines["runs"] / baselines["deliveries"]
)

baselines["wicket_expected"] = (
    baselines["wickets"] / baselines["deliveries"]
)

df = df.merge(
    baselines[[
        "phase", "run_expected", "wicket_expected"
    ]],
    on="phase",
    validate="many_to_one"
)

results = []
match_rows = []

for pid, (name, role) in PLAYERS.items():

    column = (
        "striker_id" if role == "batting"
        else "bowler_id"
    )

    p = df[
        pd.to_numeric(df[column], errors="coerce").eq(pid)
    ].copy()

    if p.empty:
        print("No qualifying data:", name)
        continue

    if role == "batting":
        p["impact"] = (
            p["runs"] - p["run_expected"]
        )
    else:
        p["impact"] = (
            p["run_expected"] - p["runs"]
            + WICKET_VALUE * (
                p["bowler_wicket"]
                - p["wicket_expected"]
            )
        )

    p["weighted_impact"] = (
        p["impact"] * p["pressure_weight"]
    )

    matches = p.groupby("match_id").agg(
        balls=("runs", "size"),
        impact=("impact", "sum"),
        pressure_impact=("weighted_impact", "sum")
    ).reset_index()

    matches["player"] = name
    matches["role"] = role
    matches["source"] = "rr_official_filtered"

    matches["impact_per_ball"] = (
        matches["impact"] / matches["balls"]
    )

    match_rows.append(matches)

    n = len(matches)
    balls = int(matches["balls"].sum())

    raw_pressure = (
        matches["pressure_impact"].sum() / balls
    )

    shrinkage = balls / (balls + PRIOR_BALLS)
    adjusted = raw_pressure * shrinkage

    pressure = float(np.clip(
        3 + 1.5 * np.tanh(adjusted / 0.45),
        0, 5
    ))

    values = matches["impact_per_ball"].to_numpy()
    median = float(np.median(values))

    mad = float(
        np.median(np.abs(values - median))
    )

    positive = int((matches["impact"] > 0).sum())
    positive_rate = (positive + 2) / (n + 4)

    stability = 1 / (1 + mad / 0.30)
    match_weight = n / (n + 8)

    reliability = float(np.clip(
        5 * (
            0.55 * positive_rate
            + 0.45 * stability
        ) * match_weight
        + 2.5 * (1 - match_weight),
        0, 5
    ))

    results.append({
        "player": name,
        "role": role,
        "source": "rr_official_filtered",
        "matches": n,
        "balls": balls,
        "positive_matches": positive,
        "positive_match_rate": round(
            positive_rate, 3
        ),
        "sample_weight": round(shrinkage, 3),
        "adjusted_pressure_impact": round(
            adjusted, 4
        ),
        "match_impact_mad": round(mad, 4),
        "model_pressure": round(pressure, 2),
        "model_reliability": round(reliability, 2),
        "model_overall": round(
            pressure + reliability, 2
        ),
        "coverage_flag": (
            "LIMITED_SAMPLE"
            if n < 10 or balls < 120
            else "PROVISIONAL"
        )
    })

rr_scores = pd.DataFrame(results)

rr_scores.to_csv(
    OUT / "rr_statistical_pri.csv",
    index=False
)

if match_rows:
    pd.concat(
        match_rows, ignore_index=True
    ).to_csv(
        OUT / "rr_statistical_match_impacts.csv",
        index=False
    )

# Combine existing SMAT/external model scores with RR scores.
existing = pd.read_csv(
    OUT / "unified_statistical_pri.csv"
)

combined = pd.concat(
    [existing, rr_scores],
    ignore_index=True
)

# Preserve existing scores if a player appears twice.
combined = combined.drop_duplicates(
    subset=["player"], keep="first"
)

combined.to_csv(
    OUT / "combined_statistical_pri.csv",
    index=False
)

print("\n=== RR STATISTICAL PRI ===")
print(rr_scores.to_string(index=False))

print("\n=== COMBINED MODEL COVERAGE ===")
print("Players:", combined["player"].nunique())
print("Saved: combined_statistical_pri.csv")
