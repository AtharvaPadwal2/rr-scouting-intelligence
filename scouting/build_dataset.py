"""Aggregate Cricsheet JSON matches into player-season records."""

import argparse
import json
from pathlib import Path

import pandas as pd


BOWLER_WICKETS = {
    "bowled",
    "caught",
    "caught and bowled",
    "lbw",
    "stumped",
    "hit wicket",
    "hit the ball twice",
}

NON_DISMISSALS = {"retired hurt", "obstructing the field"}


TOTALS = [
    "matches",
    "batting_innings",
    "runs",
    "balls_faced",
    "dismissals",
    "legal_balls_bowled",
    "runs_conceded",
    "wickets",
]


def read_match(path):
    match = json.loads(path.read_text(encoding="utf-8"))
    info = match["info"]

    if info["match_type"] != "T20":
        raise ValueError(f"{path.name}: this converter currently supports T20.")

    if info["balls_per_over"] != 6:
        raise ValueError(f"{path.name}: expected six-ball overs.")

    people = info["registry"]["people"]
    rows = {}

    for team, names in info["players"].items():
        for name in names:
            rows[name] = {
                "player_id": people[name],
                "player_name": name,
                "team": team,
                "season": str(info["season"]),
                "competition": info["event"]["name"],
                "format": info["match_type"],
                "source": "Cricsheet",
                "age_at_season_end": None,
                "role": None,
                **{column: 0 for column in TOTALS},
            }
            rows[name]["matches"] = 1

    for innings in match["innings"]:
        if innings.get("super_over"):
            continue

        appeared = set()

        for over in innings["overs"]:
            for delivery in over["deliveries"]:
                batter = delivery["batter"]
                bowler = delivery["bowler"]
                appeared.update([batter, delivery["non_striker"]])

                extras = delivery.get("extras", {})
                runs = delivery["runs"]

                rows[batter]["runs"] += runs["batter"]
                rows[batter]["balls_faced"] += int(not extras.get("wides", 0))

                legal = not extras.get("wides", 0) and not extras.get("noballs", 0)
                rows[bowler]["legal_balls_bowled"] += int(legal)
                rows[bowler]["runs_conceded"] += (
                    runs["batter"]
                    + extras.get("wides", 0)
                    + extras.get("noballs", 0)
                )

                for wicket in delivery.get("wickets", []):
                    kind = wicket["kind"]

                    if kind not in NON_DISMISSALS:
                        rows[wicket["player_out"]]["dismissals"] += 1

                    if kind in BOWLER_WICKETS:
                        rows[bowler]["wickets"] += 1

        for name in appeared:
            rows[name]["batting_innings"] += 1

    return list(rows.values())


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    files = sorted(args.input.glob("*.json"))

    if not files:
        raise ValueError(f"No JSON files found in {args.input}")

    records = []
    for path in files:
        records.extend(read_match(path))

    frame = pd.DataFrame(records)
    keys = ["player_id", "team", "season", "competition", "format"]

    aggregation = {column: "sum" for column in TOTALS}
    aggregation.update({
        "player_name": "first",
        "source": "first",
        "age_at_season_end": "first",
        "role": "first",
    })

    dataset = frame.groupby(keys, as_index=False).agg(aggregation)
    dataset["source_match_count"] = len(files)
    dataset["coverage_note"] = "Totals from supplied matches only"

    args.output.parent.mkdir(parents=True, exist_ok=True)
    dataset.to_csv(args.output, index=False)

    print(f"Processed {len(files)} matches.")
    print(f"Created {len(dataset)} player-team-season records.")
    print(f"Seasons: {', '.join(sorted(dataset['season'].unique()))}")
    print(f"Saved to {args.output}")


if __name__ == "__main__":
    main()