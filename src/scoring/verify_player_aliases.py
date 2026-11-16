
from pathlib import Path
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / "data" / "processed" / "external"
OUTPUT = ROOT / "outputs"

CANDIDATES = {
    "super_smash": {
        "Daryl Mitchell": "DJ Mitchell",
        "Bevon Jacobs": "BJ Jacobs",
        "Matthew Fisher": "MJ Fisher",
    },
    "cpl": {
        "Shamar Springer": "SK Springer",
    },
}

results = []

for league, players in CANDIDATES.items():
    df = pd.read_csv(
        DATA / f"{league}_deliveries.csv",
        low_memory=False
    )

    for target, alias in players.items():
        batting = df[
            df["striker"].astype(str).str.casefold()
            == alias.casefold()
        ]

        bowling = df[
            df["bowler"].astype(str).str.casefold()
            == alias.casefold()
        ]

        combined = pd.concat(
            [batting, bowling],
            ignore_index=True
        ).drop_duplicates(
            subset=[
                "match_id",
                "innings",
                "over",
                "delivery_index",
            ]
        )

        ids = set(
            batting["striker_id"].dropna().astype(str)
        ) | set(
            bowling["bowler_id"].dropna().astype(str)
        )

        teams = set(
            batting["batting_team"].dropna()
        ) | set(
            bowling["bowling_team"].dropna()
        )

        results.append({
            "player": target,
            "alias": alias,
            "league": league,
            "cricsheet_ids": "; ".join(sorted(ids)),
            "teams": "; ".join(sorted(teams)),
            "matches": combined["match_id"].nunique(),
            "batting_rows": len(batting),
            "bowling_rows": len(bowling),
            "first_match": (
                combined["match_date"].min()
                if not combined.empty else None
            ),
            "last_match": (
                combined["match_date"].max()
                if not combined.empty else None
            ),
        })

result = pd.DataFrame(results)

result.to_csv(
    OUTPUT / "player_alias_candidates.csv",
    index=False
)

print("\n=== PLAYER ALIAS VERIFICATION ===")
print(result.to_string(index=False))

print("\nSaved: outputs/player_alias_candidates.csv")
