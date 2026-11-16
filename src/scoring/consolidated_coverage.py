
from pathlib import Path
import pandas as pd
import re
import unicodedata

ROOT = Path(__file__).resolve().parents[2]
REGISTRY = ROOT / "data/external/registries"
EXTERNAL = ROOT / "data/processed/external"
OUTPUT = ROOT / "outputs"

OUTPUT.mkdir(exist_ok=True)

players = pd.read_csv(
    OUTPUT / "player_coverage_audit.csv"
)

LEAGUES = [
    "super_smash",
    "cpl",
    "bbl",
    "t20_blast",
]

# Previously inspected aliases; pending registry confirmation.
CANDIDATES = {
    "Daryl Mitchell": ["DJ Mitchell"],
    "Bevon Jacobs": ["BJ Jacobs"],
    "Matthew Fisher": ["MJ Fisher"],
    "Shamar Springer": ["SK Springer"],
    "Yash Dhull": ["YV Dhull"],
    "Chetan Sakariya": ["C Sakariya"],
}

def normalize(value):
    if pd.isna(value):
        return ""
    value = unicodedata.normalize("NFKD", str(value))
    value = "".join(
        c for c in value
        if not unicodedata.combining(c)
    )
    value = re.sub(r"[^a-z0-9 ]", " ", value.lower())
    return " ".join(value.split())


# Inspect registry format before using it as authoritative mapping.
for filename in ["people.csv", "names.csv"]:
    path = REGISTRY / filename

    if path.exists():
        registry = pd.read_csv(path, low_memory=False)
        print(f"\n=== {filename} ===")
        print("Rows:", len(registry))
        print("Columns:", registry.columns.tolist())
        print(registry.head(2).to_string(index=False))


results = []

for league in LEAGUES:
    df = pd.read_csv(
        EXTERNAL / f"{league}_deliveries.csv",
        dtype={
            "striker_id": "string",
            "bowler_id": "string",
        },
        low_memory=False,
    )

    df["striker_norm"] = df["striker"].map(normalize)
    df["bowler_norm"] = df["bowler"].map(normalize)

    for _, player in players.iterrows():
        name = player["player"]
        aliases = [name] + CANDIDATES.get(name, [])
        keys = {normalize(alias) for alias in aliases}

        batting = df[df["striker_norm"].isin(keys)]
        bowling = df[df["bowler_norm"].isin(keys)]

        ids = set(
            batting["striker_id"].dropna().astype(str)
        ) | set(
            bowling["bowler_id"].dropna().astype(str)
        )

        results.append({
            "player": name,
            "role": player["role"],
            "league": league,
            "batting_matches": batting["match_id"].nunique(),
            "batting_rows": len(batting),
            "bowling_matches": bowling["match_id"].nunique(),
            "bowling_rows": len(bowling),
            "cricsheet_ids": "; ".join(sorted(ids)),
            "matched_names": "; ".join(sorted(
                set(batting["striker"].dropna().astype(str))
                | set(bowling["bowler"].dropna().astype(str))
            )),
            "match_status": (
                "CANDIDATE_ALIAS"
                if ids and normalize(name) not in (
                    set(batting["striker_norm"])
                    | set(bowling["bowler_norm"])
                )
                else "EXACT_NAME"
                if ids else "NOT_FOUND"
            ),
        })

result = pd.DataFrame(results)

result.to_csv(
    OUTPUT / "consolidated_external_coverage.csv",
    index=False,
)

matched = result[
    (result["batting_rows"] > 0)
    | (result["bowling_rows"] > 0)
]

print("\n=== EXTERNAL COVERAGE MATCHES ===")
print(matched.to_string(index=False))

print("\n=== SUMMARY ===")
print("Players found:", matched["player"].nunique())
print("League-player matches:", len(matched))
print("Candidate aliases:", (
    matched["match_status"] == "CANDIDATE_ALIAS"
).sum())

print("\nSaved: outputs/consolidated_external_coverage.csv")
