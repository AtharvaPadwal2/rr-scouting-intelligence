
import kagglehub
import pandas as pd
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw" / "ipl_2026"
RAW.mkdir(parents=True, exist_ok=True)

source = Path(kagglehub.dataset_download(
    "janvigoel19/ipl-2026-complete-ball-by-ball-dataset"
))

print("\nDATASET LOCATION:", source)

files = sorted(source.rglob("*.csv"))

print("\nCSV FILES FOUND:", len(files))

for file in files:
    df = pd.read_csv(file, low_memory=False)

    print("\n" + "=" * 65)
    print("FILE:", file.relative_to(source))
    print("ROWS:", len(df))
    print("COLUMNS:", len(df.columns))

    print("\nCOLUMN NAMES:")
    print(df.columns.tolist())

    print("\nFIRST 3 ROWS:")
    print(df.head(3).to_string(index=False))

    print("\nDATA TYPES:")
    print(df.dtypes.to_string())

    print("\nMISSING VALUES:")
    print(
        df.isna()
        .sum()
        .sort_values(ascending=False)
        .head(15)
    )

    print("\nEXACT DUPLICATE ROWS:")
    print(df.duplicated().sum())

    for col in df.columns:
        key = col.lower().replace("_", "").replace(" ", "")

        if key in [
            "battingteam", "bowlingteam",
            "team1", "team2", "season"
        ]:
            print(f"\nVALUES IN {col}:")
            print(df[col].value_counts().head(15))

print("\nInspection complete.")
