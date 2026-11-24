"""FastAPI service for the G04 demo.

Endpoints
1. GET  /api/health     models that are loaded
2. GET  /api/samples    the demo documents
3. GET  /api/models     metrics of the three tasks, read from the exported artifacts
4. POST /api/analyze    upload one PDF and run the whole pipeline
"""
import hashlib
import json
import re
import time
from contextlib import asynccontextmanager

import pandas as pd
from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware

from .paths import CORPUS_DIR, DEMO_DIR, TASK1_DIR, TASK3_DIR
from .pdf_text import extract_text

MAX_UPLOAD = 15 * 1024 * 1024
STATE = {}


def _sha(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _load_samples():
    meta = json.loads((DEMO_DIR / "samples.json").read_text(encoding="utf-8"))
    for item in meta:
        raw = (DEMO_DIR / "docs" / f"{item['id']}.txt").read_bytes().decode("utf-8")
        item["sha256"] = _sha(raw)
    return meta


@asynccontextmanager
async def lifespan(app):
    from .task1 import Task1
    from .task2 import Task2
    from .task3 import Task3

    start = time.time()
    STATE["task1"] = Task1()
    STATE["task2"] = Task2()
    STATE["task3"] = Task3()
    STATE["samples"] = _load_samples()
    STATE["by_hash"] = {s["sha256"]: s for s in STATE["samples"]}
    labels = pd.read_csv(TASK1_DIR / "task1_crime_predictions.csv").set_index("file_name")
    STATE["task1_labels"] = labels
    STATE["load_seconds"] = round(time.time() - start, 1)
    yield
    STATE.clear()


app = FastAPI(title="G04 NLP Demo", lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])


@app.get("/api/health")
def health():
    return {
        "status": "ok",
        "load_seconds": STATE.get("load_seconds"),
        "task2_bert": STATE.get("task2") is not None and STATE["task2"].tagger is not None,
    }


@app.get("/api/samples")
def samples():
    return [{k: v for k, v in s.items() if k != "sha256"} for s in STATE["samples"]]


@app.get("/api/models")
def models():
    t1 = STATE["task1"].metadata
    t3 = STATE["task3"]
    test = pd.read_csv(TASK3_DIR / "test_results.csv")
    return {
        "task1": {"model": t1["model"], "classes": len(t1["classes"]), "metrics": t1["metrics"],
                  "train_documents": t1["train_documents"],
                  "features": {"word": t1["n_word_features"], "char": t1["n_char_features"]}},
        "task2": {"selector": {"bert": ["victim_count", "victim_injury", "loss_value"]},
                  "test_scores": {"defendant_age": 98.7, "prosecutor_demand_type": 100.0, "prosecutor_demand_months": 100.0,
                                  "article_charged": 90.0, "victim_count": 75.3, "victim_injury": 76.7, "weapon_used": 88.7,
                                  "loss_value": 87.3, "prior_conviction": 95.3, "confession": 94.7, "remorse": 98.7,
                                  "cooperative": 100.0, "aggravating_factors": 92.9, "mitigating_factors": 98.1}},
        "task3": {"summary": t3.summary, "blend": t3.blend,
                  "leaderboard": test[["experiment", "block", "val_mae", "test_mae", "test_r2"]].round(3).to_dict("records")},
    }


def _identify(name, text):
    """Find which corpus document the upload is, and whether its text is identical."""
    sample = STATE["by_hash"].get(_sha(text))
    if sample:
        return sample["id"], {"source": "demo set", "exact": True, "original_chars": len(text)}
    match = re.search(r"doc_\d+", name or "")
    doc_id = match.group(0) if match else None
    original = None
    if doc_id and (DEMO_DIR / "docs" / f"{doc_id}.txt").exists():
        original = (DEMO_DIR / "docs" / f"{doc_id}.txt").read_bytes().decode("utf-8")
    elif doc_id and CORPUS_DIR and (CORPUS_DIR / f"{doc_id}.txt").exists():
        original = (CORPUS_DIR / f"{doc_id}.txt").read_bytes().decode("utf-8")
    if original is None:
        return doc_id or "upload", {"source": None, "exact": None, "original_chars": None}
    return doc_id, {"source": "corpus", "exact": original == text, "original_chars": len(original)}


@app.post("/api/analyze")
async def analyze(file: UploadFile = File(...)):
    data = await file.read()
    if len(data) > MAX_UPLOAD:
        raise HTTPException(413, "The file is larger than 15 MB")
    if not data.startswith(b"%PDF"):
        raise HTTPException(400, "Please upload a PDF file")
    timings = {}

    t = time.perf_counter()
    try:
        extracted = extract_text(data)
    except Exception as error:  # noqa: BLE001
        raise HTTPException(422, f"Could not read the PDF: {error}") from error
    raw = extracted["text"]
    if not raw.strip():
        raise HTTPException(422, "The PDF has no text layer")
    doc_id, match = _identify(file.filename, raw)
    timings["extract"] = time.perf_counter() - t

    # The notebooks read the corpus in text mode, which turns CRLF into LF.
    text = raw.replace("\r\n", "\n")

    t = time.perf_counter()
    task1 = STATE["task1"].run(text)
    timings["task1"] = time.perf_counter() - t
    labels = STATE["task1_labels"]
    key = f"{doc_id}.txt"
    task1["true_label"] = labels.loc[key, "crime_type_label"] if key in labels.index else None
    task1["split"] = labels.loc[key, "split"] if key in labels.index else None

    t = time.perf_counter()
    task2 = STATE["task2"].run(text, doc_id, task1["label"])
    timings["task2"] = time.perf_counter() - t

    t = time.perf_counter()
    task3 = STATE["task3"].run(text, doc_id, task1["label"], task2["record"])
    timings["task3"] = time.perf_counter() - t

    words = raw.split()
    return {
        "doc_id": doc_id,
        "file_name": file.filename,
        "extraction": {
            "pages": extracted["pages"],
            "lines": raw.count("\r\n"),
            "chars": len(raw),
            "words": len(words),
            "sha256": _sha(raw),
            "match": match,
            "text": raw,
        },
        "task1": task1,
        "task2": task2,
        "task3": task3,
        "timings_ms": {k: round(v * 1000) for k, v in timings.items()},
    }
