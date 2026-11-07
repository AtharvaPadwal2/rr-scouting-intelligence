from io import BytesIO
from pathlib import Path

import pandas as pd


def read_scouting_file(filename: str, content: bytes) -> pd.DataFrame:
    """Read a CSV or the first worksheet of an XLSX file."""
    extension = Path(filename).suffix.lower()

    if not content:
        raise ValueError("The file is empty.")

    if extension == ".csv":
        return pd.read_csv(BytesIO(content), encoding="utf-8-sig")

    if extension == ".xlsx":
        return pd.read_excel(BytesIO(content), engine="openpyxl", sheet_name=0)

    raise ValueError("Choose a .csv or .xlsx file.")