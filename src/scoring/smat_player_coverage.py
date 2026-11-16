
from pathlib import Path
from difflib import get_close_matches
import pandas as pd
import re
import unicodedata

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / "data" / "processed"
OUTPUT = ROOT / "outputs"
OUTPUT.mkdir(exist_ok=True)

coverage = pd.read_csv(
    OUTPUT / "player_coverage_audit.csv"
)

smat = pd.read_csv(
    DATA / "smat_all_deliveries.csv",
    low_memory=False
)

def normalize(value):
    if pd.isna(value):
        return ""

    value = unicodedata.normalize(
        "NFKD", str(value)
    )
    value = "".join(
        c for c in value if not unicodedata.combining(c)
    )
    value = re.sub(
        r"[^a-z0-9 ]", " ", value.lower()
    )

    return " ".join(value.split())

for col in ["striker", "bowler"]:
    smat[f"{col}_normalized"] = smat[col].map(normalize)

all_names = sorted(
    set(smat["striker_normalized"].dropna())
    | set(smat["bowler_normalized"].dropna())
)

results = []

for _, player in coverage.iterrows():
    name = player["player"]
    role = player["role"]
    key = normalize(name)

    batting = smat[
        smat["striker_normalized"] == key
    ]

    bowling = smat[
        smat["bowler_normalized"] == key
    ]

    matched = not batting.empty or not bowling.empty

    suggestions = (
        ""
        if matched
        else "; ".join(
            get_close_matches(
                key, all_names, n=5, cutoff=0.7
            )
        )
    )

    batting_matches = batting["match_id"].nunique()
    bowling_matches = bowling["match_id"].nunique()

    results.append({
        "player": name,
        "role": role,
        "smat_found": matched,
        "batting_matches": batting_matches,
        "batting_rows": len(batting),
        "bowling_matches": bowling_matches,
        "bowling_rows": len(bowling),
        "seasons": "; ".join(
            sorted(
                set(
                    batting["season"].dropna().astype(str)
                )
                | set(
                    bowling["season"].dropna().astype(str)
                )
            )
        ),
        "suggestions": suggestions
    })

result = pd.DataFrame(results)

result.to_csv(
    OUTPUT / "smat_player_coverage.csv",
    index=False
)

print("\n=== SMAT PLAYER COVERAGE ===")
print(result.to_string(index=False))

print("\n=== SUMMARY ===")
print(result["smat_found"].value_counts())

print("\nSaved: outputs/smat_player_coverage.csv")
