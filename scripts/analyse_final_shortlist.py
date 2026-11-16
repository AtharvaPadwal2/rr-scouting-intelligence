
from pathlib import Path
import pandas as pd

BASE = Path("data/processed/rr_official")

BATTERS = [
    "Daryl Mitchell",
    "Yash Dhull",
    "Karan Lal",
    "Ashish Siwach",
    "Tushar Raheja",
    "Aaryavir Sehwag",
    "Anmolpreet Singh",
    "Bevon Jacobs",
    "Yajas Sharma",
    "Aaron Hardie",
]

BOWLERS = [
    "Josh Tongue",
    "Tanush Kotian",
    "Simarjeet Singh",
    "Chetan Sakariya",
    "Ishant Bharadwaj",
    "Gerald Coetzee",
    "Shubham Kumar Gupta",
    "Shamar Springer",
    "Nathan Smith",
    "Gus Atkinson",
]

FILES = {
    "Batting adjusted": "pressure_batting_adjusted.csv",
    "Batting reliability": "pressure_batting_reliability.csv",
    "Batting consistency": "pressure_batting_match_consistency.csv",
    "Bowling adjusted": "pressure_bowling_adjusted.csv",
    "Bowling reliability": "pressure_bowling_reliability.csv",
    "Bowling consistency": "pressure_bowling_match_consistency.csv",
}

def normalize(value):
    return "".join(
        char for char in str(value).lower()
        if char.isalnum()
    )

for label, filename in FILES.items():
    path = BASE / filename

    print(f"\n{'=' * 65}")
    print(label.upper())
    print(f"{'=' * 65}")

    if not path.exists():
        print("File missing")
        continue

    df = pd.read_csv(path)

    print("Columns:", list(df.columns))
    print("Total records:", len(df))

    names = BATTERS if label.startswith("Batting") else BOWLERS

    name_columns = [
        col for col in df.columns
        if any(
            word in col.lower()
            for word in ["player", "batter", "bowler", "name"]
        )
        and not any(
            word in col.lower()
            for word in ["id", "opponent", "non_striker"]
        )
    ]

    if not name_columns:
        print("No player-name column detected")
        print(df.head(3).to_string(index=False))
        continue

    matched_rows = pd.DataFrame()

    for col in name_columns:
        normalized_values = df[col].fillna("").map(normalize)
        targets = {normalize(name) for name in names}

        found = df[normalized_values.isin(targets)]
        matched_rows = pd.concat([matched_rows, found])

    matched_rows = matched_rows.drop_duplicates()

    if matched_rows.empty:
        print("No exact normalized name matches.")
        print("Sample names:")
        print(df[name_columns[0]].dropna().head(12).to_list())
    else:
        print(matched_rows.to_string(index=False))
