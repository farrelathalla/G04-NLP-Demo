"""Task 3, sentence duration prediction.

Live part: the S2 model (LightGBM on the crime type and the Task 2 record) is the only
Task 3 model that was saved, so it runs on the uploaded document. The feature table is
built with the same code as the notebook (fact_table and build_features).

Champion part: the H4 blend averages text models that were not saved, only their
predictions. For documents of the corpus the champion prediction is read from the
exported task3_sentence_predictions.csv.
"""
import json
import re
import unicodedata

import joblib
import numpy as np
import pandas as pd

from .paths import TASK3_DIR

NM, NA = "not_mentioned", "not_applicable"
MIN_MONTHS, MAX_MONTHS = 1.0, 240.0
DEMAND_TYPES = ["penjara", "kurungan", "seumur_hidup", "mati", "rehabilitasi", "bebas"]
INJURY_ORDER = {"none": 0.0, "psychological": 1.0, "minor": 2.0, "serious": 3.0, "death": 4.0}
WEAPON_TYPES = ["none", "sharp", "blunt", "firearm", "other"]
AGGRAVATING_CODES = [
    "public_unrest", "against_gov_program", "victim_loss", "victim_harm", "harm_to_youth", "prior_conviction",
    "enjoyed_proceeds", "evasive_or_denial", "no_reconciliation", "abuse_of_position", "use_of_violence",
    "premeditated", "repeated_act", "against_norms", "other_aggravating",
]
MITIGATING_CODES = [
    "no_prior_conviction", "admission", "remorse", "polite_conduct", "cooperative", "breadwinner",
    "victim_forgiveness", "restitution", "young_age", "old_age_or_health", "caregiver", "no_proceeds_enjoyed",
    "other_mitigating",
]
BOOL_FIELDS = ["prior_conviction", "confession", "remorse", "cooperative"]
CAT_COLS = ["crime_type", "demand_type", "weapon"]

# ---- notebook section 2.H, text utilities used for regex_demand_months ----
CHAR_MAP = {0x2018: "'", 0x2019: "'", 0x201c: '"', 0x201d: '"', 0x2013: "-", 0x2014: "-", 0x2212: "-", 0x00a0: " ", 0x00ad: ""}
NOISE_LINE = re.compile(
    r"^\s*(?:direktori putusan.*|putusan\.mahkamahagung.*|h?k?a?hkama\w*|ahkamah agung.*|"
    r"mah agung.*|blik indonesi.*|halaman\s+\d+.*|disclaimer.*)\s*$", re.I)
DISCLAIMER_PATTERNS = [
    re.compile(r"Kepaniteraan\s+Mahkamah\s+Agung\s+Republik\s+Indonesia\s+berusaha.{0,400}?akuntabilitas", re.I | re.S),
    re.compile(r"pelaksanaan\s+fungsi\s+peradilan\.?\s+Namun.{0,900}?\(ext\.?\s*318\)", re.I | re.S),
    re.compile(r"Dalam\s+hal\s+Anda\s+menemukan\s+inakurasi.{0,500}?\(ext\.?\s*318\)", re.I | re.S),
    re.compile(r"Email\s*:\s*kepaniteraan@\S+", re.I),
    re.compile(r"Telp\s*:\s*021-?\s*384\s*3348\s*\(ext\.?\s*318\)", re.I),
]
PAGE_MARK = re.compile(
    r"(?:Halaman|Hal\.?)\s*\d+\s*(?:dari|dr)\s*\d+\s*(?:hal\.?\s*)?(?:Putusan\s*)?(?:Pidana\s*)?(?:Nomor|No\.?)?\s*", re.I)
CASE_NUMBER = re.compile(r"\b\d+/Pid\.[\w.-]+/\d{4}/PN\s+\w+", re.I)
SPLIT_ARTICLE = re.compile(r"(Pasal\s+\d{1,2})\s+(\d{1,2})(?=\s+(?:KUH|ayat))", re.I)
VERDICT_HEADING = re.compile(r"M\s*E\s*N\s*G\s*A\s*D\s*I\s*L\s*I\s*:|\bMENGADILI\b")
DEMAND_ANCHOR = re.compile(r"tuntutan\s+pidana|pada\s+pokoknya\s+menuntut|menuntut\s+(?:supaya|agar)", re.I)
DEMAND_PHRASE = re.compile(r"pidana\s+(penjara|kurungan)\b", re.I)
DEMAND_LIFE = re.compile(r"penjara\s+seumur\s+hidup|pidana\s+mati\b", re.I)
DEMAND_STOP = re.compile(r"\b(?:denda|subsid\w*|dikurang\w*|dengan\s+perintah|masa\s+percobaan|dan\s+membayar)", re.I)
DURATION = re.compile(r"(\d{1,3}(?:[.,]\d)?)\s*(?:\([^)]{0,40}\))?\s*(tahun|bulan|hari)\b", re.I)


def clean_text(raw):
    text = unicodedata.normalize("NFKC", raw).translate(CHAR_MAP)
    text = "\n".join(line for line in text.splitlines() if not NOISE_LINE.match(line))
    for pattern in DISCLAIMER_PATTERNS:
        text = pattern.sub(" ", text)
    text = PAGE_MARK.sub(" ", text)
    text = CASE_NUMBER.sub(" ", text)
    text = re.sub(r"(\w)-\s*\n\s*(\w)", r"\1-\2", text)
    text = SPLIT_ARTICLE.sub(r"\1\2", text)
    return re.sub(r"\s+", " ", text).strip()


def mask_verdict(text):
    match = VERDICT_HEADING.search(text, int(len(text) * 0.5))
    return text[:match.start()] if match else text


def parse_duration(segment):
    months = 0.0
    for value, unit in DURATION.findall(segment):
        value = float(value.replace(",", "."))
        months += value * 12 if unit.lower() == "tahun" else value if unit.lower() == "bulan" else value / 30
    return months


def regex_demand(text):
    anchor = DEMAND_ANCHOR.search(text)
    if not anchor:
        return np.nan, "none", None
    window = text[anchor.start():anchor.start() + 3000]
    for match in DEMAND_PHRASE.finditer(window):
        segment = DEMAND_STOP.split(window[match.end():match.end() + 160], maxsplit=1)[0]
        months = parse_duration(segment)
        if months > 0:
            return months, match.group(1).lower(), window[match.start():match.end() + len(segment)].strip()
    if DEMAND_LIFE.search(window):
        return np.nan, "life_or_death", None
    return np.nan, "none", None


# ---- notebook section 8.B, feature table ----
def to_float(value):
    if isinstance(value, bool):
        return float(value)
    if value is None or value == "" or value == NM:
        return np.nan
    if value == NA:
        return -1.0
    try:
        return float(value)
    except (TypeError, ValueError):
        return np.nan


def to_flag(value):
    if value in (True, "True", "true", 1):
        return 1.0
    if value in (False, "False", "false", 0):
        return 0.0
    return np.nan


def to_category(value, allowed):
    if value in (None, "", NM):
        return NM
    if value == NA:
        return NA
    return value if value in allowed else "other_value"


def as_list(value):
    return value if isinstance(value, list) else []


def safe_name(code):
    return re.sub(r"[^0-9A-Za-z]+", "_", code).strip("_")


def to_months(log_values):
    return np.clip(np.expm1(np.asarray(log_values, dtype=np.float64)), MIN_MONTHS, MAX_MONTHS)


class Task3:
    def __init__(self):
        self.model = joblib.load(TASK3_DIR / "models" / "S2_facts_lgbm.joblib")
        self.columns = list(self.model.feature_name_)
        categories = self.model.booster_.pandas_categorical or []
        self.categories = dict(zip(CAT_COLS, categories))
        self.article_columns = {c.split("_", 2)[2]: c for c in self.columns if c.startswith("art_")}
        self.predictions = pd.read_csv(TASK3_DIR / "task3_sentence_predictions.csv").set_index("file_name")
        self.summary = json.loads((TASK3_DIR / "summary.json").read_text())
        weights = pd.read_csv(TASK3_DIR / "blend_weights.csv", index_col=0)["weight"]
        self.blend = [{"model": k, "weight": round(float(v), 4)} for k, v in weights.sort_values(ascending=False).items() if v > 0]

    def features(self, record, crime, regex_months):
        demand = to_float(record.get("prosecutor_demand_months"))
        loss = to_float(record.get("loss_value"))
        injury = record.get("victim_injury")
        row = {
            "crime_type": crime, "t2_missing": 0.0,
            "age": to_float(record.get("defendant_age")),
            "demand_type": to_category(record.get("prosecutor_demand_type"), DEMAND_TYPES),
            "demand_months": demand if demand > 0 else np.nan,
            "victim_count": to_float(record.get("victim_count")),
            "injury": INJURY_ORDER.get(injury, -1.0 if injury == NA else np.nan),
            "weapon": to_category(record.get("weapon_used"), WEAPON_TYPES),
            "log_loss": np.log1p(loss) if loss >= 0 else loss,
        }
        for field in BOOL_FIELDS:
            row[field] = to_flag(record.get(field))
        aggravating = set(as_list(record.get("aggravating_factors")))
        mitigating = set(as_list(record.get("mitigating_factors")))
        for code in AGGRAVATING_CODES:
            row[f"agg_{code}"] = float(code in aggravating)
        for code in MITIGATING_CODES:
            row[f"mit_{code}"] = float(code in mitigating)
        row["n_aggravating"] = float(len(aggravating & set(AGGRAVATING_CODES)))
        row["n_mitigating"] = float(len(mitigating & set(MITIGATING_CODES)))
        articles = {safe_name(a) for a in as_list(record.get("article_charged"))}
        row["n_articles"] = float(len(as_list(record.get("article_charged"))))
        for name, column in self.article_columns.items():
            row[column] = float(name in articles)
        row["regex_demand_months"] = regex_months
        row["demand_any"] = row["demand_months"] if not np.isnan(row["demand_months"]) else regex_months
        row["log_demand"] = np.log1p(row["demand_any"])
        frame = pd.DataFrame([row])[self.columns]
        for column in CAT_COLS:
            frame[column] = pd.Categorical(frame[column], categories=self.categories.get(column))
        return frame

    def run(self, raw, doc_id, crime, record):
        masked = mask_verdict(clean_text(raw))
        regex_months, regex_type, regex_phrase = regex_demand(masked)
        frame = self.features(record, crime, regex_months)
        live = float(to_months(self.model.predict(frame))[0])

        contrib = self.model.predict(frame, pred_contrib=True)[0]
        base = float(contrib[-1])
        drivers = sorted(
            ({"feature": c, "value": None if pd.isna(frame[c].iloc[0]) else (str(frame[c].iloc[0]) if c in CAT_COLS else float(frame[c].iloc[0])),
              "effect": float(v)} for c, v in zip(self.columns, contrib[:-1]) if abs(v) > 1e-6),
            key=lambda d: -abs(d["effect"]),
        )[:8]

        champion = None
        key = f"{doc_id}.txt"
        if key in self.predictions.index:
            row = self.predictions.loc[key]
            champion = {
                "months": None if pd.isna(row["pred_months"]) else float(row["pred_months"]),
                "true_months": None if pd.isna(row["months_true"]) else float(row["months_true"]),
                "split": row["split"],
                "prediction_type": row["prediction_type"],
                "crime_type_true": row["crime_type"],
            }

        shown = ["crime_type", "demand_type", "demand_months", "regex_demand_months", "demand_any", "age",
                 "victim_count", "injury", "weapon", "log_loss", "n_aggravating", "n_mitigating", "n_articles"]
        table = []
        for c in shown:
            v = frame[c].iloc[0]
            table.append({"feature": c, "value": None if pd.isna(v) else (str(v) if c in CAT_COLS else round(float(v), 3))})
        return {
            "live": {"model": "S2_facts_lgbm", "months": round(live, 2), "base_months": round(float(to_months(base)), 2),
                     "drivers": drivers},
            "regex_demand": {"months": None if np.isnan(regex_months) else round(float(regex_months), 2),
                             "type": regex_type, "phrase": regex_phrase},
            "features": table,
            "n_features": len(self.columns),
            "champion": champion,
        }
