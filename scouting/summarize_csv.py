"""Build player-team-season totals from merged Cricsheet deliveries."""

import argparse
import csv
from io import StringIO
from pathlib import Path
from zipfile import ZipFile

import pandas as pd


BOWLER_WICKETS = {
    "bowled",
    "caught",
    "caught and bowled",
    "lbw",
    "stumped",
    "hit wicket",
}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--archive", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--people", type=Path, required=True)
    args = parser.parse_args()

    data = pd.read_csv(args.input, dtype="string")

    required = {
        "match_id", "season", "competition", "format", "innings",
        "batting_team", "bowling_team", "striker", "non_striker",
        "bowler", "runs_off_bat", "wicket_type", "player_dismissed",
    }
    missing = required - set(data.columns)
    if missing:
        raise ValueError(f"Missing columns: {sorted(missing)}")
    if data.empty:
        raise ValueError("The delivery CSV is empty.")
    if data[["match_id", "season", "competition", "format"]].isna().any().any():
        raise ValueError("Match ID, season, competition, or format is missing.")
    if not data["format"].eq("T20").all():
        raise ValueError("This converter currently supports T20 matches only.")

    for column in ("runs_off_bat", "wides", "noballs"):
        if column not in data.columns:
            raise ValueError(f"Missing column: {column}")
        values = pd.to_numeric(data[column], errors="raise")
        if column != "runs_off_bat":
            values = values.fillna(0)
        if values.isna().any() or values.lt(0).any() or values.mod(1).ne(0).any():
            raise ValueError(f"Invalid counts in {column}")
        data[column] = values.astype("int64")

    data["innings"] = pd.to_numeric(data["innings"], errors="raise")
    records = {}
    batting_appearances = set()

    with ZipFile(args.archive) as archive:
        info_members = {}
        for member in archive.namelist():
            name = Path(member).name
            if name.endswith("_info.csv"):
                if name in info_members:
                    raise ValueError(f"Duplicate metadata file: {name}")
                info_members[name] = member

        for match_id, deliveries in data.groupby("match_id", sort=True):
            info_name = f"{match_id}_info.csv"
            if info_name not in info_members:
                raise ValueError(f"Missing metadata: {info_name}")

            text = archive.read(info_members[info_name]).decode("utf-8-sig")
            metadata = list(csv.reader(StringIO(text)))

            people = {}
            roster = []
            super_overs = set()
            balls_per_over = None

            for row in metadata:
                if len(row) < 3 or row[0] != "info":
                    continue
                if row[1] == "registry" and len(row) >= 5 and row[2] == "people":
                    people[row[3]] = row[4]
                elif row[1] == "player" and len(row) >= 4:
                    roster.append((row[2], row[3]))
                elif row[1] == "super_over":
                    super_overs.add(int(row[2]))
                elif row[1] == "balls_per_over":
                    balls_per_over = int(row[2])

            if balls_per_over != 6:
                raise ValueError(f"{match_id}: expected six-ball overs.")
            if not roster:
                raise ValueError(f"{match_id}: no player roster found.")

            context = deliveries[["season", "competition", "format"]].drop_duplicates()
            if len(context) != 1:
                raise ValueError(f"{match_id}: conflicting match context.")

            season, competition, match_format = context.iloc[0].tolist()
            match_players = {}

            for team, name in set(roster):
                if name not in people:
                    raise ValueError(f"{match_id}: missing ID for {name}")

                key = (people[name], team, season, competition, match_format)
                if key not in records:
                    records[key] = {
                        "player_id": people[name],
                        "player_name": name,
                        "team": team,
                        "season": season,
                        "competition": competition,
                        "format": match_format,
                        "source": "Cricsheet",
                        "age_at_season_end": None,
                        "role": None,
                        "matches": 0,
                        "batting_innings": 0,
                        "runs": 0,
                        "balls_faced": 0,
                        "dismissals": 0,
                        "legal_balls_bowled": 0,
                        "runs_conceded": 0,
                        "wickets": 0,
                        "coverage_note": "Totals from available matches only",
                    }

                records[key]["matches"] += 1
                match_players[(team, name)] = key

            regular = deliveries.loc[~deliveries["innings"].isin(super_overs)]

            for delivery in regular.to_dict("records"):
                batting_team = delivery["batting_team"]
                bowling_team = delivery["bowling_team"]
                batter_key = match_players[(batting_team, delivery["striker"])]
                bowler_key = match_players[(bowling_team, delivery["bowler"])]
                batter = records[batter_key]
                bowler = records[bowler_key]

                for name in (delivery["striker"], delivery["non_striker"]):
                    key = match_players[(batting_team, name)]
                    appearance = (match_id, delivery["innings"], key)
                    if appearance not in batting_appearances:
                        records[key]["batting_innings"] += 1
                        batting_appearances.add(appearance)

                batter["runs"] += delivery["runs_off_bat"]
                batter["balls_faced"] += int(delivery["wides"] == 0)

                bowler["legal_balls_bowled"] += int(
                    delivery["wides"] == 0 and delivery["noballs"] == 0
                )
                bowler["runs_conceded"] += (
                    delivery["runs_off_bat"]
                    + delivery["wides"]
                    + delivery["noballs"]
                )

                for kind_column, player_column in (
                    ("wicket_type", "player_dismissed"),
                    ("other_wicket_type", "other_player_dismissed"),
                ):
                    kind = delivery.get(kind_column)
                    dismissed = delivery.get(player_column)

                    if pd.isna(kind) or pd.isna(dismissed):
                        continue

                    if kind != "retired hurt":
                        dismissed_key = match_players[(batting_team, dismissed)]
                        records[dismissed_key]["dismissals"] += 1

                    if kind in BOWLER_WICKETS:
                        bowler["wickets"] += 1

    result = pd.DataFrame(records.values()).sort_values(
        ["season", "team", "player_name"]
    )
    people = pd.read_csv(args.people, dtype="string")
    profile_columns = [
        "identifier",
        "unique_name",
        "key_cricinfo",
        "key_cricbuzz",
        "key_bcci",
    ]

    result = result.merge(
        people[profile_columns].rename(columns={
            "identifier": "player_id",
            "unique_name": "registry_name",
        }),
        on="player_id",
        how="left",
        validate="many_to_one",
    )

    print(
        "Records matched to registry:",
        int(result["registry_name"].notna().sum()),
        "of",
        len(result),
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    temporary = args.output.with_suffix(".csv.tmp")
    result.to_csv(temporary, index=False)
    temporary.replace(args.output)

    print(f"Matches processed: {data['match_id'].nunique()}")
    print(f"Unique players: {result['player_id'].nunique()}")
    print(f"Player-team-season records: {len(result)}")
    print("\nRecords per season:")
    print(result.groupby("season").size().to_string())
    print(f"\nSaved to: {args.output.resolve()}")


if __name__ == "__main__":
    main()