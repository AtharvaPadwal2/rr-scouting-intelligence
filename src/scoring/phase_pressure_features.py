
from pathlib import Path
import pandas as pd
import numpy as np

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / "data" / "processed" / "external"
OUTPUT = ROOT / "data" / "processed" / "scoring"

OUTPUT.mkdir(parents=True, exist_ok=True)

PLAYERS = {
    "super_smash": {
        "eade4650": ("Daryl Mitchell", "batting"),
        "972f217b": ("Bevon Jacobs", "batting"),
        "7068c81e": ("Matthew Fisher", "bowling"),
    },
    "cpl": {
        "4175d211": ("Shamar Springer", "bowling"),
    },
}

BOWLER_WICKETS = {
    "bowled", "caught", "caught and bowled",
    "lbw", "stumped", "hit wicket",
}

all_records = []
league_records = []

for league, players in PLAYERS.items():
    df = pd.read_csv(
        DATA / f"{league}_deliveries.csv",
        low_memory=False,
        dtype={"striker_id": "string", "bowler_id": "string"},
    )

    df["phase"] = np.select(
        [
            df["over"] < 6,
            df["over"] < 15,
        ],
        ["powerplay", "middle"],
        default="death",
    )

    df["batting_ball"] = df["wides"].fillna(0).eq(0)
    df["bowling_ball"] = df["legal_ball"].astype(str).str.lower().eq("true")

    df["bowler_runs"] = (
        df["runs_off_bat"].fillna(0)
        + df["wides"].fillna(0)
        + df["noballs"].fillna(0)
    )

    df["bowler_wickets"] = df["dismissal_types"].fillna("").apply(
        lambda value: sum(
            kind.strip().lower() in BOWLER_WICKETS
            for kind in str(value).split("|")
        )
    )

    # Baselines from the entire competition, not just shortlisted players.
    for phase, group in df.groupby("phase"):
        batting_balls = group["batting_ball"].sum()
        bowling_balls = group["bowling_ball"].sum()

        league_records.append({
            "league": league,
            "phase": phase,
            "batting_sr_baseline": (
                100 * group["runs_off_bat"].sum() / batting_balls
                if batting_balls else np.nan
            ),
            "bowling_economy_baseline": (
                6 * group["bowler_runs"].sum() / bowling_balls
                if bowling_balls else np.nan
            ),
            "wickets_per_100_balls": (
                100 * group["bowler_wickets"].sum() / bowling_balls
                if bowling_balls else np.nan
            ),
        })

    for player_id, (name, role) in players.items():
        id_column = (
            "striker_id" if role == "batting" else "bowler_id"
        )

        player_df = df[df[id_column] == player_id]

        for phase, group in player_df.groupby("phase"):
            balls = int(
                group["batting_ball"].sum()
                if role == "batting"
                else group["bowling_ball"].sum()
            )

            if balls == 0:
                continue

            all_records.append({
                "player": name,
                "league": league,
                "role": role,
                "phase": phase,
                "matches": group["match_id"].nunique(),
                "balls": balls,
                "runs": (
                    group["runs_off_bat"].sum()
                    if role == "batting" else np.nan
                ),
                "wickets": (
                    group["bowler_wickets"].sum()
                    if role == "bowling" else np.nan
                ),
                "runs_conceded": (
                    group["bowler_runs"].sum()
                    if role == "bowling" else np.nan
                ),
            })

baselines = pd.DataFrame(league_records)
features = pd.DataFrame(all_records)

features = features.merge(
    baselines,
    on=["league", "phase"],
    how="left",
    validate="many_to_one",
)

features["player_strike_rate"] = np.where(
    features["role"].eq("batting"),
    100 * features["runs"] / features["balls"],
    np.nan,
)

features["player_economy"] = np.where(
    features["role"].eq("bowling"),
    6 * features["runs_conceded"] / features["balls"],
    np.nan,
)

features["batting_impact"] = (
    features["player_strike_rate"]
    - features["batting_sr_baseline"]
)

features["bowling_impact"] = (
    features["bowling_economy_baseline"]
    - features["player_economy"]
)

baselines.to_csv(
    OUTPUT / "league_phase_baselines.csv",
    index=False,
)

features.to_csv(
    OUTPUT / "phase_pressure_features.csv",
    index=False,
)

print("\n=== LEAGUE PHASE BASELINES ===")
print(baselines.round(2).to_string(index=False))

print("\n=== PLAYER PHASE PERFORMANCE ===")
print(
    features[
        [
            "player", "league", "role", "phase",
            "matches", "balls", "player_strike_rate",
            "player_economy", "batting_impact", "bowling_impact",
        ]
    ].round(2).to_string(index=False)
)

print("\nSaved phase features and league baselines.")
