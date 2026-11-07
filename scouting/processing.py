"""Prepare player-season records for scouting analytics."""

import json

import pandas as pd


REQUIRED_COLUMNS = [
    "player_id",
    "player_name",
    "season",
    "age_at_season_end",
    "role",
]

COUNT_COLUMNS = [
    "runs",
    "balls_faced",
    "dismissals",
    "wickets",
    "runs_conceded",
    "legal_balls_bowled",
]


def clean_count(values, minimum=0):
    """Convert valid whole-number counts to nullable integers."""
    numbers = pd.to_numeric(values, errors="coerce")
    valid = (
        numbers.ge(minimum)
        & numbers.lt(2**63)
        & numbers.mod(1).eq(0)
    ).fillna(False)
    return numbers.where(valid).astype("Int64")


def prepare_dataset(raw):
    """Clean records, calculate rates, and return JSON-safe data."""
    missing_columns = [
        column for column in REQUIRED_COLUMNS if column not in raw.columns
    ]
    if missing_columns:
        raise ValueError(
            "Missing required columns: " + ", ".join(missing_columns)
        )

    if raw.empty:
        raise ValueError("The file contains no player records.")

    duplicates = int(raw.duplicated().sum())
    data = raw.drop_duplicates().copy()

    for column in ("player_id", "player_name", "role"):
        data[column] = (
            data[column]
            .astype("string")
            .str.strip()
            .replace("", pd.NA)
        )

    data["role"] = data["role"].str.casefold()
    data["age_at_season_end"] = clean_count(
        data["age_at_season_end"], minimum=1
    )

    for column in COUNT_COLUMNS:
        if column in data.columns:
            data[column] = clean_count(data[column])

    if {"runs", "balls_faced"}.issubset(data.columns):
        valid_balls = data["balls_faced"].where(data["balls_faced"].gt(0))
        data["calculated_batting_strike_rate"] = (
            data["runs"].div(valid_balls).mul(100).round(2)
        )

    if {"runs_conceded", "legal_balls_bowled"}.issubset(data.columns):
        valid_bowling_balls = data["legal_balls_bowled"].where(
            data["legal_balls_bowled"].gt(0)
        )
        data["calculated_bowling_economy"] = (
            data["runs_conceded"].mul(6).div(valid_bowling_balls).round(2)
        )
    if {"runs", "dismissals"}.issubset(data.columns):
        valid_dismissals = data["dismissals"].where(data["dismissals"].gt(0))
        data["calculated_batting_average"] = (
            data["runs"].div(valid_dismissals).round(2)
        )

    if {"runs_conceded", "wickets"}.issubset(data.columns):
        valid_wickets = data["wickets"].where(data["wickets"].gt(0))
        data["calculated_bowling_average"] = (
            data["runs_conceded"].div(valid_wickets).round(2)
        )

    if {"legal_balls_bowled", "wickets"}.issubset(data.columns):
        valid_wickets = data["wickets"].where(data["wickets"].gt(0))
        data["calculated_bowling_strike_rate"] = (
            data["legal_balls_bowled"].div(valid_wickets).round(2)
        )

    summary = {
        "raw_rows": len(raw),
        "cleaned_rows": len(data),
        "duplicates_removed": duplicates,
        "unique_players": int(data["player_id"].nunique()),
        "valid_strike_rate_rows": (
            int(data["calculated_batting_strike_rate"].notna().sum())
            if "calculated_batting_strike_rate" in data.columns
            else 0
        ),
    }

    # pandas serializes missing values as JSON null.
    records = json.loads(data.to_json(orient="records", date_format="iso"))

    return {
        "summary": summary,
        "columns": list(data.columns),
        "records": records,
    }