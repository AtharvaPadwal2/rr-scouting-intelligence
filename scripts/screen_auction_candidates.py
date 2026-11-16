
from pathlib import Path
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data" / "processed" / "rr_official"

# Manual research decisions, not inferred from match data.
EXCLUDE = {
    "Andre Russell": "Retired from IPL",
    "Dinesh Karthik": "Retired from IPL",
    "Ravichandran Ashwin": "Retired from IPL",
    "Tim Southee": "KKR coaching role - exclude pending review",
    "Ambati Rayudu": "Retired from IPL in 2023",
}
PLAYING_STATUS_REVIEW = {
    "Matthew Wade",
    "Angelo Mathews",
}

# Known Pakistan internationals in our current Top 25.
# Extend this set when screening the full candidate pool.
PAKISTAN_REVIEW = {
    "Babar Azam", "Fakhar Zaman",
    "Shadab Khan", "Iftikhar Ahmed",
    "Mohammad Rizwan", "Faheem Ashraf",
    "Abrar Ahmed", "Sufiyan Muqeem",
    "Shaheen Afridi", "Mohammad Nawaz",
    "Mohammad Wasim", "Ahmed Daniyal",
    "Salman Mirza", "Haris Rauf",
}

# Explicitly confirmed unsold at IPL 2026 auction.
# This is NOT proof of current contract status.
UNSOLD_2026 = {
    "Vijay Shankar",
    "Maheesh Theekshana",
}

NEEDS_REGISTRATION_CHECK = {
    "Glenn Maxwell",
}

def screen(filename, output_prefix):
    df = pd.read_csv(DATA / filename)

    df["player_name"] = (
        df["player_name"].fillna("").astype(str).str.strip()
    )

    df["screening_status"] = "CONTRACT_CHECK_REQUIRED"
    df["screening_note"] = (
        "Not in historical IPL 2026 mapping; "
        "current status unverified"
    )

    for name, reason in EXCLUDE.items():
        mask = df["player_name"].eq(name)
        df.loc[mask, "screening_status"] = "EXCLUDE"
        df.loc[mask, "screening_note"] = reason

    mask = df["player_name"].isin(PAKISTAN_REVIEW)
    df.loc[mask, "screening_status"] = "EXCLUDE"
    df.loc[mask, "screening_note"] = (
        "Pakistan international - not a practical IPL target"
    )

    mask = df["player_name"].isin(UNSOLD_2026)
    df.loc[mask, "screening_status"] = "PRIORITY_VERIFY"
    df.loc[mask, "screening_note"] = (
        "Unsold in 2026 auction; "
        "verify current contract and 2027 registration"
    )

    mask = df["player_name"].isin(NEEDS_REGISTRATION_CHECK)
    df.loc[mask, "screening_status"] = "REGISTRATION_CHECK"
    df.loc[mask, "screening_note"] = (
        "Did not register for 2026 auction; "
        "2027 participation unknown"
    )
    mask = df["player_name"].isin(PLAYING_STATUS_REVIEW)

    df.loc[mask, "screening_status"] = "PLAYING_STATUS_REVIEW"
    df.loc[mask, "screening_note"] = (
    "Verify active playing status and 2027 auction intentions"
    )

    # Export all rows for full audit.
    df.to_csv(
        DATA / f"{output_prefix}_eligibility_audit.csv",
        index=False
    )

    # This is a REVIEW POOL, not confirmed free agents.
    pool = df[
        df["screening_status"].isin([
            "CONTRACT_CHECK_REQUIRED",
            "PRIORITY_VERIFY",
            "REGISTRATION_CHECK"
        ])
    ].copy()

    pool = pool.sort_values(
        "adjusted_score", ascending=False
    ).reset_index(drop=True)

    pool.insert(0, "review_rank", range(1, len(pool) + 1))

    pool.to_csv(
        DATA / f"{output_prefix}_review_pool.csv",
        index=False
    )

    print(f"\n=== {output_prefix.upper()} REVIEW TOP 20 ===")
    print(
        pool[[
            "review_rank", "player_name",
            "adjusted_score", "screening_status"
        ]].head(20).round(2).to_string(index=False)
    )

    print("Excluded:", int(
        df["screening_status"].eq("EXCLUDE").sum()
    ))
    print("Remaining for verification:", len(pool))


screen(
    "unattached_batting_candidates.csv",
    "batting_auction"
)

screen(
    "unattached_bowling_candidates.csv",
    "bowling_auction"
)

print("\nNo player is confirmed auction-eligible by this script.")
