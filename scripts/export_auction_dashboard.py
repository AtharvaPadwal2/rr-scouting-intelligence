
from pathlib import Path
import json
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data/processed/rr_official"
OUTPUT = ROOT / "frontend/public/data/auction-overview.json"

OUTPUT.parent.mkdir(parents=True, exist_ok=True)

sources = {
    "batters": "batting_auction_review_pool.csv",
    "bowlers": "bowling_auction_review_pool.csv",
    "uncappedBatters": "smat_batting_manual_review.csv",
    "uncappedBowlers": "smat_bowling_manual_review.csv",
}

def load_csv(filename):
    path = DATA / filename

    if not path.exists():
        raise FileNotFoundError(f"Missing: {path}")

    df = pd.read_csv(path)

    # Convert NaN to JSON null.
    return json.loads(
        df.to_json(orient="records")
    )

payload = {
    "metadata": {
        "model": "Provisional auction scouting",
        "eligibility": "UNVERIFIED",
        "description": (
            "Review pools only. Not confirmed unattached players."
        )
    },
    **{
        key: load_csv(filename)
        for key, filename in sources.items()
    }
}

with open(OUTPUT, "w", encoding="utf-8") as f:
    json.dump(payload, f, indent=2, ensure_ascii=False)

print("Exported:", OUTPUT)
print("Auction batters:", len(payload["batters"]))
print("Auction bowlers:", len(payload["bowlers"]))
print("SMAT batting reviews:", len(payload["uncappedBatters"]))
print("SMAT bowling reviews:", len(payload["uncappedBowlers"]))
