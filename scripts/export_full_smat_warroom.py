
from pathlib import Path
import json
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data" / "processed"
RR = DATA / "rr_official"
OUT = ROOT / "frontend" / "public" / "data"
OUT.mkdir(parents=True, exist_ok=True)

smat = pd.read_csv(
    DATA / "smat_player_seasons.csv",
    dtype={"player_id": str},
    low_memory=False
)

smat["player_id"] = smat["player_id"].str.strip()

numeric_cols = [
    "matches", "batting_innings", "runs",
    "balls_faced", "dismissals",
    "legal_balls_bowled", "runs_conceded",
    "wickets"
]

for col in numeric_cols:
    smat[col] = pd.to_numeric(
        smat[col], errors="coerce"
    )

def optional(path):
    if not path.exists():
        return []
    frame = pd.read_csv(
        path, dtype={"player_id": str}, low_memory=False
    )
    frame["player_id"] = frame["player_id"].str.strip()
    return json.loads(frame.to_json(orient="records"))

payload = {
    "metadata": {
        "dataset": "SMAT player-season records",
        "coverage": "Available Cricsheet matches only",
        "age_as_of": "2026-11-10",
        "warning": (
            "Historical SMAT data is incomplete. "
            "Domestic participation does not prove "
            "uncapped or unattached status."
        )
    },
    "seasons": sorted(
        smat["season"].dropna().astype(str).unique().tolist()
    ),
    "records": json.loads(
        smat.to_json(orient="records")
    ),
    "dob_registry": optional(
        RR / "uncapped_indian_dob_registry.csv"
    ),
    "eligibility_registry": optional(
        RR / "uncapped_indian_verification_priority.csv"
    ),
}

destination = OUT / "smat-warroom.json"
destination.write_text(
    json.dumps(payload, ensure_ascii=False),
    encoding="utf-8"
)

print("Exported:", destination)
print("Player-season records:", len(smat))
print("Unique players:", smat["player_id"].nunique())
print("Seasons:", len(payload["seasons"]))
print("DOB registry records:", len(payload["dob_registry"]))
print(
    "Eligibility review records:",
    len(payload["eligibility_registry"])
)
