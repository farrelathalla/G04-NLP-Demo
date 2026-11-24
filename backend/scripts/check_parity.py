"""Check that the demo reproduces the notebooks on the sample PDFs.

For every sample it checks that
1. the PDF extracts to the source txt byte for byte,
2. Task 1 predicts the same label as task1_crime_predictions.csv,
3. Task 2 fills every slot exactly as task2_records.csv.

Usage
    python scripts/check_parity.py
"""
import json
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.pdf_text import extract_text  # noqa: E402
from app.task1 import Task1  # noqa: E402
from app.task2 import Task2  # noqa: E402
from app.task3 import Task3  # noqa: E402

PDF_DIR = ROOT.parent / "web" / "public" / "samples"


def as_text(value):
    return "|".join(value) if isinstance(value, list) else str(value)


def same(a, b):
    if a == b:
        return True
    try:
        return float(a) == float(b)
    except ValueError:
        return False


def main():
    t1, t2, t3 = Task1(), Task2(), Task3()
    labels = pd.read_csv(ROOT / "artifacts/task1/task1_crime_predictions.csv").set_index("file_name")
    records = pd.read_csv(ROOT / "artifacts/task2/task2_records.csv", dtype=str, keep_default_na=False).set_index("doc_id")
    ok = True
    for sample in json.loads((ROOT / "demo/samples.json").read_text()):
        doc = sample["id"]
        raw = extract_text((PDF_DIR / f"{doc}.pdf").read_bytes())["text"]
        exact = raw == (ROOT / "demo/docs" / f"{doc}.txt").read_bytes().decode("utf-8")
        text = raw.replace("\r\n", "\n")
        a = t1.run(text)
        b = t2.run(text, doc, a["label"])
        c = t3.run(text, doc, a["label"], b["record"])
        diffs = [f for f, v in b["record"].items() if not same(as_text(v), records.loc[doc, f])]
        label_ok = a["label"] == labels.loc[f"{doc}.txt", "crime_type_pred"]
        ok &= exact and label_ok and not diffs
        print(f"{doc}: pdf exact={exact} task1 same={label_ok} task2 diffs={diffs or 'none'} "
              f"S2={c['live']['months']} H4={c['champion']['months']} true={c['champion']['true_months']}")
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
