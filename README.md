# RR Scouting Intelligence

Phase 1, step 1. A local Streamlit shell and a deterministic synthetic T20 dataset.
All records are fictional and contain intentional defects for testing.

## Run on Windows PowerShell

Use Python 3.11 or 3.12. From the extracted project directory:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
.\.venv\Scripts\python.exe -m streamlit run app.py
```

Open http://127.0.0.1:8501. The overview shows 96 fictional players over
three seasons. Use the sidebar to open the dataset preview, change the season,
and download the full CSV. Using the virtual environment's Python directly works
without activating it. Substitute `-3.11` if that is the installed version.

On macOS or Linux, use `python3 -m venv .venv`, then use `.venv/bin/python`
in place of the Windows executable.

## Tests and CSV generation

```powershell
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe -m scouting.synthetic
```

The default CSV is written to `data/synthetic/players.csv`. To regenerate
without replacing that file, pass `--output data/synthetic/players-v2.csv`.

## Project structure

| Path | Purpose |
|---|---|
| `app.py` | Streamlit entry point and demo navigation |
| `.streamlit/config.toml` | RR palette, localhost binding and telemetry settings |
| `scouting/synthetic.py` | Seeded player-season generator and CSV command |
| `tests/` | Generator tests and Streamlit smoke test |
| `requirements*.txt` | Pinned direct dependencies |
| `data/private/` | Reserved for local proprietary inputs and excluded from Git |

If the Python launcher cannot find Python 3.12, run `py -0p` to see installed
versions. If port 8501 is occupied, add `--server.port 8502` to the launch
command and open http://127.0.0.1:8502.

The demo schema is a development fixture. The next step is a local CSV/XLSX
importer with explicit column mapping and data-quality reporting. Keep official
records in `data/private/` and derived exports in `data/exports/`.
