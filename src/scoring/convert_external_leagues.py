
import json
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
EXTERNAL = ROOT / "data" / "external"
OUTPUT = ROOT / "data" / "processed" / "external"

OUTPUT.mkdir(parents=True, exist_ok=True)

LEAGUES = {
    "super_smash": EXTERNAL / "super_smash",
    "cpl": EXTERNAL / "cpl",
    "bbl": EXTERNAL / "bbl",
    "t20_blast": EXTERNAL / "t20_blast",
}


def safe_int(value):
    try:
        return int(value or 0)
    except (ValueError, TypeError):
        return 0


def convert_league(league, folder):
    records = []
    errors = []
    matches_processed = 0

    for file in sorted(folder.rglob("*.json")):
        try:
            with open(file, "r", encoding="utf-8") as f:
                match = json.load(f)

            info = match.get("info", {})
            teams = info.get("teams", [])
            dates = info.get("dates", [])

            date = str(dates[0]) if dates else None
            season = info.get("season")

            event = info.get("event", {})
            event_name = (
                event.get("name")
                if isinstance(event, dict)
                else str(event)
            )

            player_registry = info.get(
                "registry", {}
            ).get("people", {})

            for innings_number, innings in enumerate(
                match.get("innings", []), start=1
            ):
                batting_team = innings.get("team")

                bowling_team = next(
                    (
                        team for team in teams
                        if team != batting_team
                    ),
                    None,
                )

                for over in innings.get("overs", []):
                    over_number = safe_int(
                        over.get("over")
                    )

                    for index, delivery in enumerate(
                        over.get("deliveries", []),
                        start=1,
                    ):
                        runs = delivery.get("runs", {})
                        extras = delivery.get("extras", {})
                        wickets = delivery.get("wickets", [])

                        striker = delivery.get("batter")
                        bowler = delivery.get("bowler")

                        is_wide = "wides" in extras
                        is_no_ball = "noballs" in extras

                        records.append({
                            "source_league": league,
                            "source_file": file.name,
                            "match_id": file.stem,
                            "match_date": date,
                            "season": season,
                            "event": event_name,
                            "match_type": info.get("match_type"),
                            "innings": innings_number,
                            "over": over_number,
                            "delivery_index": index,
                            "batting_team": batting_team,
                            "bowling_team": bowling_team,
                            "striker": striker,
                            "striker_id": player_registry.get(
                                striker
                            ),
                            "bowler": bowler,
                            "bowler_id": player_registry.get(
                                bowler
                            ),
                            "runs_off_bat": safe_int(
                                runs.get("batter")
                            ),
                            "extras": safe_int(
                                runs.get("extras")
                            ),
                            "total_runs": safe_int(
                                runs.get("total")
                            ),
                            "wides": safe_int(
                                extras.get("wides")
                            ),
                            "noballs": safe_int(
                                extras.get("noballs")
                            ),
                            "byes": safe_int(
                                extras.get("byes")
                            ),
                            "legbyes": safe_int(
                                extras.get("legbyes")
                            ),
                            "legal_ball": (
                                not is_wide
                                and not is_no_ball
                            ),
                            "wicket_count": len(wickets),
                            "dismissal_types": "|".join(
                                str(w.get("kind", ""))
                                for w in wickets
                            ),
                            "dismissed_players": "|".join(
                                str(w.get("player_out", ""))
                                for w in wickets
                            ),
                            "target_overs": innings.get(
                                "target", {}
                            ).get("overs"),
                            "target_runs": innings.get(
                                "target", {}
                            ).get("runs"),
                        })

            matches_processed += 1

        except Exception as exc:
            errors.append({
                "file": str(file),
                "error": str(exc),
            })

    df = pd.DataFrame(records)

    if not df.empty:
        output_path = OUTPUT / f"{league}_deliveries.csv"
        df.to_csv(output_path, index=False)

    print(f"\n=== {league.upper()} ===")
    print("Matches processed:", matches_processed)
    print("Delivery rows:", len(df))
    print("Errors:", len(errors))

    if not df.empty:
        print("Unique batters:", df["striker_id"].nunique())
        print("Unique bowlers:", df["bowler_id"].nunique())

    if errors:
        error_path = OUTPUT / f"{league}_errors.csv"
        pd.DataFrame(errors).to_csv(
            error_path, index=False
        )
        print("Error report:", error_path)


if __name__ == "__main__":
    for league, folder in LEAGUES.items():
        convert_league(league, folder)
