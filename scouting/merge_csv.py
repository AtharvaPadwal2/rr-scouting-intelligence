"""Merge Cricsheet Ashwin delivery CSVs from a ZIP archive."""

import argparse
import csv
from io import StringIO
from pathlib import Path
from zipfile import ZipFile

import pandas as pd


REQUIRED_COLUMNS = {
    "match_id",
    "season",
    "start_date",
    "innings",
    "ball",
    "batting_team",
    "bowling_team",
    "striker",
    "non_striker",
    "bowler",
    "runs_off_bat",
}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    frames = []
    processed_matches = set()

    with ZipFile(args.input) as archive:
        members = {
            entry.filename: entry
            for entry in archive.infolist()
            if not entry.is_dir()
        }

        for filename in sorted(members):
            path = Path(filename)

            # Match delivery files have numeric names, such as 902223.csv.
            if path.suffix.lower() != ".csv" or not path.stem.isdigit():
                continue

            if path.stem in processed_matches:
                raise ValueError(f"Duplicate match file: {path.name}")

            text = archive.read(filename).decode("utf-8-sig")
            frame = pd.read_csv(
                StringIO(text),
                dtype={
                    "match_id": "string",
                    "season": "string",
                    "ball": "string",
                    "actual_delivery": "string",
                },
            )

            missing = REQUIRED_COLUMNS - set(frame.columns)
            if missing:
                raise ValueError(
                    f"{path.name}: missing columns {sorted(missing)}"
                )

            if frame.empty:
                print(f"Skipping empty delivery file: {path.name}")
                continue

            if (
                frame["match_id"].isna().any()
                or set(frame["match_id"]) != {path.stem}
            ):
                raise ValueError(f"{path.name}: unexpected match IDs")

            # Read selected metadata from the companion info file.
            info_filename = str(
                path.with_name(f"{path.stem}_info.csv")
            ).replace("\\", "/")

            metadata = {}

            if info_filename in members:
                info_text = archive.read(info_filename).decode("utf-8-sig")

                for row in csv.reader(StringIO(info_text)):
                    if len(row) >= 3 and row[0] == "info":
                        if row[1] in {"event", "match_type", "balls_per_over"}:
                            metadata[row[1]] = row[2]

            frame["competition"] = metadata.get("event", pd.NA)
            frame["format"] = metadata.get("match_type", pd.NA)
            frame["balls_per_over"] = metadata.get("balls_per_over", pd.NA)
            frame["source_file"] = path.name

            frames.append(frame)
            processed_matches.add(path.stem)

    if not frames:
        raise ValueError("No matching delivery CSV files found in the ZIP.")

    merged = pd.concat(frames, ignore_index=True, sort=False)

    # Write a temporary output first to avoid leaving a partial final CSV.
    args.output.parent.mkdir(parents=True, exist_ok=True)
    temporary_output = args.output.with_suffix(".csv.tmp")
    merged.to_csv(temporary_output, index=False)
    temporary_output.replace(args.output)

    print(f"Matches merged: {len(processed_matches)}")
    print(f"Delivery rows: {len(merged):,}")
    print(f"Columns: {len(merged.columns)}")
    print("Seasons:", ", ".join(sorted(merged["season"].dropna().unique())))
    print("First match date:", merged["start_date"].min())
    print("Last match date:", merged["start_date"].max())
    print(f"Saved to: {args.output.resolve()}")


if __name__ == "__main__":
    main()