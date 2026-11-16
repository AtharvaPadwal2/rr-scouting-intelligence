
from pathlib import Path
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]

DATA = ROOT / "data" / "processed" / "rr_official"
REPORT = ROOT / "data" / "reports" / "rr_official"

REPORT.mkdir(parents=True, exist_ok=True)

df = pd.read_csv(
    DATA / "deliveries_clean.csv",
    low_memory=False
)

# Updated provisional classification.
# 'other' appears to account for most over-count
# anomalies, but requires external validation.

df["extra_normalized"] = (
    df["extras_type"]
    .astype("string")
    .str.lower()
    .str.strip()
)

illegal_types = {"wide", "overstep", "other"}

df["legal_ball_candidate"] = ~df[
    "extra_normalized"
].isin(illegal_types)

df["legal_ball_candidate"] = (
    df["legal_ball_candidate"].fillna(True)
    .astype(bool)
)

# Keep uncertainty explicit.
df["flag_ambiguous_extra"] = (
    df["extra_normalized"].eq("other")
    .fillna(False)
)

# Group by match, innings and over.
overs = (
    df.groupby(
        ["match_id", "innings", "overid"],
        dropna=False
    )
    .agg(
        events=("match_id", "size"),
        legal_balls=("legal_ball_candidate", "sum"),
        ambiguous_events=("flag_ambiguous_extra", "sum")
    )
    .reset_index()
)

last_over = (
    overs.groupby(["match_id", "innings"])["overid"]
    .max()
    .rename("last_over")
    .reset_index()
)

overs = overs.merge(
    last_over,
    on=["match_id", "innings"],
    validate="many_to_one"
)

overs["flag_over_six"] = (
    overs["legal_balls"] > 6
)

overs["flag_incomplete_nonterminal"] = (
    (overs["overid"] < overs["last_over"])
    & (overs["legal_balls"] < 6)
)

overs["flag_zero_legal"] = (
    overs["legal_balls"] == 0
)

flags = [
    "flag_over_six",
    "flag_incomplete_nonterminal",
    "flag_zero_legal",
]

flagged = overs[overs[flags].any(axis=1)].copy()

# Export every event from flagged overs.
details = df.merge(
    flagged[["match_id", "innings", "overid"]],
    on=["match_id", "innings", "overid"],
    how="inner",
    validate="many_to_one"
)

# Export without overwriting the source-cleaned file.
overs.to_csv(
    REPORT / "revised_over_audit.csv",
    index=False
)

flagged.to_csv(
    REPORT / "remaining_over_anomalies.csv",
    index=False
)

details.to_csv(
    REPORT / "remaining_anomaly_deliveries.csv",
    index=False
)

print("\n=== REVISED LEGAL BALL AUDIT ===")
print("Total deliveries:", len(df))

print(
    "Wide events:",
    int(df["extra_normalized"].eq("wide").sum())
)
print(
    "No-ball events:",
    int(df["extra_normalized"].eq("overstep").sum())
)
print(
    "Ambiguous 'other' events:",
    int(df["flag_ambiguous_extra"].sum())
)

print("Overs exceeding six:", int(overs["flag_over_six"].sum()))
print(
    "Incomplete nonterminal overs:",
    int(overs["flag_incomplete_nonterminal"].sum())
)
print(
    "Zero-legal-ball overs:",
    int(overs["flag_zero_legal"].sum())
)

print("\n=== REMAINING EXCEPTIONS ===")
print(flagged.to_string(index=False))

print("\nAudit files saved.")
print("Delivery legality remains provisional.")
