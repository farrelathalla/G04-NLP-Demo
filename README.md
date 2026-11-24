# G04 Judgment Analysis Demo

Web demo for the G04 NLP final project on Indonesian criminal judgments. Upload one court decision as PDF and the
pipeline runs the three tasks of the project.

1. **Task 1, crime classification.** TF-IDF word and character n-grams with a linear SVM (T3), 18 crime types.
2. **Task 2, information extraction.** Rules and an IndoBERT BIO tagger fill 14 sentencing factor slots. The route
   selector of the notebook takes victim count, victim injury, and loss value from IndoBERT.
3. **Task 3, sentence prediction.** The S2 LightGBM model runs live on the extracted facts. The champion H4 blend is
   read from the notebook export, because its text members were not saved as models.

## Structure

```
backend/                 FastAPI service, Python
  app/
    pdf_text.py          PDF to text, one text object per line, CRLF joined
    task1.py             Task 1 inference and explanation steps
    task1_model.py       Exported Task 1 preprocessing and model (from the notebook)
    task2_rules.py       Task 2 symbolic route, copied from the notebook
    task2.py             Task 2 IndoBERT route and route selector
    task3.py             Task 3 feature table, S2 model, champion lookup
    main.py              API
  artifacts/             Model files and notebook exports
  demo/                  Source txt files and metadata of the five samples
  scripts/
    make_demo_pdfs.py    Renders the sample PDFs and checks the round trip
    check_parity.py      Checks the demo against the notebook exports
web/                     Next.js app with shadcn/ui
  public/samples/        The five sample PDFs
```

## Artifacts

The two large weight files are not in git. Put them here before starting the backend.

| File | Source | Place in |
|---|---|---|
| `t3_tfidf_word_char_svm.pt` | Task 1 export (`model_export/artifacts`) | `backend/artifacts/task1/` |
| `model.safetensors` | Task 2 Kaggle output `data/task2/bert_model/` | `backend/artifacts/task2/bert_model/` |

Everything else in `backend/artifacts` is committed.

| Folder | Files |
|---|---|
| `task1/` | `t3_metadata.json`, `task1_crime_predictions.csv` |
| `task2/` | `bert_model/` (config and tokenizer), `task2_records.csv` |
| `task3/` | `models/S2_facts_lgbm.joblib`, `task3_sentence_predictions.csv`, `summary.json`, `blend_weights.csv`, `test_results.csv` |

If `model.safetensors` is missing, Task 2 falls back to the rules for every slot.

## Run

### A. Backend

```bash
cd backend
python -m venv .venv
.venv/Scripts/activate            # macOS or Linux: source .venv/bin/activate
pip install torch --index-url https://download.pytorch.org/whl/cpu
pip install -r requirements.txt
uvicorn app.main:app --port 8000
```

### B. Frontend

```bash
cd web
npm install
npm run dev
```

Open http://localhost:3000. The frontend forwards `/api/*` to `BACKEND_URL`, which defaults to
`http://127.0.0.1:8000`.

## Sample documents

The five samples are held out test documents of five crime types. Each PDF draws every line of the source txt as one
text object in the original order, so the extracted text is identical to the txt byte for byte. Rebuild and verify
them with

```bash
cd backend
python scripts/make_demo_pdfs.py --docs demo/docs --out ../web/public/samples
python scripts/check_parity.py
```

`check_parity.py` confirms three things for every sample.

1. The PDF extracts to the source txt exactly.
2. Task 1 gives the same label as the notebook export.
3. Task 2 fills every slot exactly as the notebook export.

## Notes

1. The Task 1 percentage is a softmax over SVM margins. It is a relative score, not a calibrated probability.
2. Set `G04_CORPUS` to a folder of `doc_*.txt` files to also verify uploads outside the sample set.
3. Course experiment. The output is not legal advice.

## Team

1. Farrel Athalla Putra, 13523118, Task 1
2. Aliya Husna Fayyaza, 13523062, Task 2
3. M. Fariz Rifqi R., 13523069, Task 3
