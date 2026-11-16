
from pathlib import Path
from difflib import get_close_matches
import pandas as pd
import re
import unicodedata

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / "data" / "processed" / "external"
OUTPUT = ROOT / "outputs"

LEAGUES = ["super_smash", "cpl"]


def normalize(value):
    if pd.isna(value):
        return ""

    value = unicodedata.normalize(
        "NFKD", str(value)
    )
    value = "".join(
        c for c in value
        if not unicodedata.combining(c)
    )
    value = re.sub(
        r"[^a-z0-9 ]", " ", value.lower()
    )

    return " ".join(value.split())


coverage = pd.read_csv(
    OUTPUT / "player_coverage_audit.csv"
)

results = []

for league in LEAGUES:
    df = pd.read_csv(
        DATA / f"{league}_deliveries.csv",
        low_memory=False
    )

    for col in ["striker", "bowler"]:
        df[f"{col}_normalized"] = df[col].map(normalize)

    # Build registry of name-to-Cricsheet-ID pairs
    batters = df[
        ["striker", "striker_id", "striker_normalized"]
    ].drop_duplicates()

    batters.columns = ["name", "id", "normalized"]

    bowlers = df[
        ["bowler", "bowler_id", "bowler_normalized"]
    ].drop_duplicates()

    bowlers.columns = ["name", "id", "normalized"]

    registry = pd.concat(
        [batters, bowlers],
        ignore_index=True
    ).drop_duplicates()

    available_names = registry["normalized"].tolist()

    for _, player in coverage.iterrows():
        name = player["player"]
        role = player["role"]
        key = normalize(name)

        matched = registry[
            registry["normalized"] == key
        ]

        if matched.empty:
            suggestions = get_close_matches(
                key,
                available_names,
                n=5,
                cutoff=0.65
            )

            results.append({
                "player": name,
                "role": role,
                "league": league,
                "status": "NOT_FOUND",
                "matched_name": "",
                "cricsheet_id": "",
                "batting_matches": 0,
                "batting_rows": 0,
                "bowling_matches": 0,
                "bowling_rows": 0,
                "suggestions": "; ".join(suggestions)
            })
            continue

        for player_id in matched["id"].dropna().unique():
            player_rows = registry[
                registry["id"] == player_id
            ]

            batting = df[
                df["striker_id"] == player_id
            ]

            bowling = df[
                df["bowler_id"] == player_id
            ]

            results.append({
                "player": name,
                "role": role,
                "league": league,
                "status": "FOUND",
                "matched_name": "; ".join(
                    player_rows["name"].dropna().unique()
                ),
                "cricsheet_id": player_id,
                "batting_matches": batting["match_id"].nunique(),
                "batting_rows": len(batting),
                "bowling_matches": bowling["match_id"].nunique(),
                "bowling_rows": len(bowling),
                "suggestions": ""
            })

result = pd.DataFrame(results)

result.to_csv(
    OUTPUT / "external_player_coverage.csv",
    index=False
)

print("\n=== VERIFIED EXACT-NAME COVERAGE ===")

found = result[result["status"] == "FOUND"]

if found.empty:
    print("No exact names found.")
else:
    print(found.to_string(index=False))

print("\n=== POSSIBLE ALIASES ===")

unmatched = result[
    (result["status"] == "NOT_FOUND")
    & (result["suggestions"].str.len() > 0)
]

print(
    unmatched[
        ["player", "league", "suggestions"]
    ].to_string(index=False)
)

print("\n=== SUMMARY ===")
print(result.groupby(
    ["league", "status"]
).size())

print("\nSaved: outputs/external_player_coverage.csv")
