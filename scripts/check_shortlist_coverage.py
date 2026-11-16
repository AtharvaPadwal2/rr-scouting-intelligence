
from pathlib import Path
from difflib import get_close_matches
import pandas as pd

BASE = Path("data/processed/rr_official")

BATTERS = [
    "Daryl Mitchell", "Yash Dhull", "Karan Lal",
    "Ashish Siwach", "Tushar Raheja",
    "Aaryavir Sehwag", "Anmolpreet Singh",
    "Bevon Jacobs", "Yajas Sharma", "Aaron Hardie"
]

BOWLERS = [
    "Josh Tongue", "Tanush Kotian", "Simarjeet Singh",
    "Chetan Sakariya", "Ishant Bharadwaj",
    "Gerald Coetzee", "Shubham Kumar Gupta",
    "Shamar Springer", "Nathan Smith", "Gus Atkinson"
]

FILES = {
    "Batting": BASE / "pressure_batting_named.csv",
    "Bowling": BASE / "pressure_bowling_named.csv",
}

def norm(s):
    return "".join(c for c in str(s).lower() if c.isalnum())

for discipline, path in FILES.items():
    print(f"\n{'=' * 65}")
    print(f"{discipline.upper()} NAME COVERAGE")
    print(f"{'=' * 65}")

    df = pd.read_csv(path)
    print("Columns:", list(df.columns))
    print("Total rows:", len(df))

    candidate_columns = [
        c for c in df.columns
        if "name" in c.lower()
        or c.lower() in ["batter", "bowler", "player"]
    ]

    if not candidate_columns:
        print("No player-name column found")
        continue

    name_col = (
        "player_name" if "player_name" in df.columns
        else candidate_columns[0]
    )

    names = sorted(df[name_col].dropna().astype(str).unique())
    normalized = {norm(n): n for n in names}

    targets = BATTERS if discipline == "Batting" else BOWLERS

    for target in targets:
        key = norm(target)

        if key in normalized:
            print(f"[EXACT] {target} -> {normalized[key]}")
            continue

        surname = target.split()[-1].lower()
        surname_matches = [
            n for n in names
            if surname in n.lower().split()
        ]

        fuzzy = get_close_matches(
            key,
            list(normalized),
            n=3,
            cutoff=0.55
        )

        suggestions = list(dict.fromkeys(
            surname_matches +
            [normalized[k] for k in fuzzy]
        ))

        if suggestions:
            print(f"[REVIEW] {target}: {suggestions[:5]}")
        else:
            print(f"[MISSING] {target}")
