
from pathlib import Path
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / "data" / "processed" / "external"
OUTPUT = ROOT / "data" / "processed" / "scoring"

OUTPUT.mkdir(parents=True, exist_ok=True)

PLAYERS = [
    ("Daryl Mitchell", "super_smash", "eade4650", "batting"),
    ("Bevon Jacobs", "super_smash", "972f217b", "batting"),
    ("Matthew Fisher", "super_smash", "7068c81e", "bowling"),
    ("Shamar Springer", "cpl", "4175d211", "bowling"),
]

BOWLER_WICKETS = {
    "bowled",
    "caught",
    "caught and bowled",
    "lbw",
    "stumped",
    "hit wicket",
}

results = []

for player, league, player_id, role in PLAYERS:

    df = pd.read_csv(
        DATA / f"{league}_deliveries.csv",
        low_memory=False,
        dtype={"striker_id": "string", "bowler_id": "string"}
    )

    if role == "batting":
        df = df[df["striker_id"] == player_id].copy()
    else:
        df = df[df["bowler_id"] == player_id].copy()

    if df.empty:
        print(f"No records found: {player}")
        continue

    for match_id, match in df.groupby("match_id"):

        if role == "batting":
            # Wides do not count as balls faced.
            balls = int((match["wides"].fillna(0) == 0).sum())

            runs = int(match["runs_off_bat"].fillna(0).sum())

            strike_rate = (
                100 * runs / balls if balls else None
            )

            results.append({
                "player": player,
                "cricsheet_id": player_id,
                "league": league,
                "role": role,
                "match_id": match_id,
                "match_date": match["match_date"].iloc[0],
                "balls": balls,
                "runs": runs,
                "strike_rate": strike_rate,
                "wickets": None,
                "runs_conceded": None,
                "economy": None,
            })

        else:
            legal = match["legal_ball"].astype(bool)

            balls = int(legal.sum())

            # Bowler conceded runs exclude byes/legbyes.
            conceded = int(
                (
                    match["runs_off_bat"].fillna(0)
                    + match["wides"].fillna(0)
                    + match["noballs"].fillna(0)
                ).sum()
            )

            wickets = 0

            for kinds in match["dismissal_types"].dropna():
                for kind in str(kinds).split("|"):
                    if kind.strip().lower() in BOWLER_WICKETS:
                        wickets += 1

            economy = (
                6 * conceded / balls if balls else None
            )

            results.append({
                "player": player,
                "cricsheet_id": player_id,
                "league": league,
                "role": role,
                "match_id": match_id,
                "match_date": match["match_date"].iloc[0],
                "balls": balls,
                "runs": None,
                "strike_rate": None,
                "wickets": wickets,
                "runs_conceded": conceded,
                "economy": economy,
            })

result = pd.DataFrame(results)

path = OUTPUT / "external_match_performance.csv"
result.to_csv(path, index=False)

print("\n=== MATCH PERFORMANCE SUMMARY ===")

summary = result.groupby(
    ["player", "league", "role"]
).agg(
    matches=("match_id", "nunique"),
    balls=("balls", "sum"),
    runs=("runs", "sum"),
    wickets=("wickets", "sum"),
    runs_conceded=("runs_conceded", "sum"),
).reset_index()

print(summary.to_string(index=False))

print("\nSaved:", path)
print("Match-performance rows:", len(result))
