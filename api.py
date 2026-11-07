"""Local API for the RR Scouting Intelligence frontend."""

from zipfile import BadZipFile

from fastapi import FastAPI, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware

from scouting.importer import read_scouting_file
from scouting.processing import prepare_dataset
from scouting.synthetic import generate_players


app = FastAPI(title="RR Scouting Intelligence API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://127.0.0.1:3000",
        "http://localhost:3000",
    ],
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type"],
)


@app.get("/api/health")
def health():
    return {"status": "ok"}


@app.get("/api/demo")
def demo_dataset():
    result = prepare_dataset(generate_players())
    return {
        "filename": "synthetic_rr_players.csv",
        "dataset_type": "synthetic",
        **result,
    }


@app.post("/api/datasets/import")
def import_dataset(file: UploadFile):
    try:
        raw = read_scouting_file(
            file.filename or "",
            file.file.read(),
        )
        result = prepare_dataset(raw)
    except (ValueError, OSError, BadZipFile) as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
    finally:
        file.file.close()

    return {
        "filename": file.filename,
        "dataset_type": "uploaded",
        **result,
    }