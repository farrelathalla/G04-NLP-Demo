"""Task 2, information extraction of sentencing factors.

Two routes run on the same cleaned decision, as in the notebook:
1. The symbolic route (task2_rules.extract), lexicon and patterns over the sections.
2. The statistical route, an IndoBERT BIO tagger over an excerpt, then normalisation.
The route selector of the notebook took victim_count, victim_injury, and loss_value from
the statistical route and every other slot from the symbolic route.
"""
import re
from pathlib import Path

import torch
from transformers import AutoModelForTokenClassification, AutoTokenizer

from . import task2_rules as r
from .paths import TASK2_DIR

NM, NA = r.NM, r.NA

# ---- notebook cell 71 (inference part) ----
TYPES = {"defendant_age": "AGE", "prosecutor_demand_months": "DEMAND", "article_charged": "ARTICLE",
         "victim_count": "VICTIM", "victim_injury": "INJURY", "weapon_used": "WEAPON", "loss_value": "LOSS",
         "aggravating_factors": "AGG", "mitigating_factors": "MIT"}
LABELS = ["O"] + [f"{p}-{t}" for t in dict.fromkeys(TYPES.values()) for p in "BI"]
MAX_LEN, STRIDE = 256, 64
GAP = 15

# ---- notebook cell 83, result of the route selector on validation ----
BERT_FIELDS = ["victim_count", "victim_injury", "loss_value"]
TASK1_TO_TASK2 = {"kesehatan_farmasi": "kesehatan", "pemerasan_pengancaman": "pemerasan"}
SLOT_ORDER = list(r.FIELDS)


def windows(tok, text):
    enc = tok(text, max_length=MAX_LEN, stride=STRIDE, truncation=True, return_overflowing_tokens=True,
              return_offsets_mapping=True, padding="max_length")
    return [(enc["input_ids"][i], enc["attention_mask"][i], enc["offset_mapping"][i], None)
            for i in range(len(enc["input_ids"]))]


class BertTagger:
    def __init__(self, model_dir: Path):
        self.tok = AutoTokenizer.from_pretrained(model_dir)
        self.model = AutoModelForTokenClassification.from_pretrained(model_dir).eval()
        torch.set_num_threads(max(1, torch.get_num_threads()))

    # ---- notebook cell 76 ----
    def tag(self, text):
        win = windows(self.tok, text)
        with torch.no_grad():
            pred = self.model(input_ids=torch.tensor([w[0] for w in win]),
                              attention_mask=torch.tensor([w[1] for w in win])).logits.argmax(-1).tolist()
        pieces = sorted({(a, b, LABELS[l][2:]) for (_, _, offs, _), labs in zip(win, pred)
                         for (a, b), l in zip(offs, labs) if a != b and l})
        out = {}
        for typ in {p[2] for p in pieces}:
            merged = []
            for a, b, _ in (p for p in pieces if p[2] == typ):
                if merged and a - merged[-1][1] <= GAP:
                    merged[-1][1] = max(merged[-1][1], b)
                else:
                    merged.append([a, b])
            for m in merged:
                while m[0] > 0 and not text[m[0] - 1].isspace():
                    m[0] -= 1
                while m[1] < len(text) and not text[m[1]].isspace():
                    m[1] += 1
            out[typ] = [(a, text[a:b]) for a, b in merged if b - a >= 3]
        return out, len(win)


def tuntutan_range(text):
    i = text.find("### tuntutan")
    j = text.find("\n### ", i + 1) if i >= 0 else -1
    return (i, len(text) if j < 0 else j) if i >= 0 else (-1, -1)


def prefer_tuntutan(text, spans, need=""):
    i, j = tuntutan_range(text)
    ok = [x for x in spans if re.search(need, x[1], re.I)] or spans
    return [x for x in ok if i <= x[0] < j] or ok


def item_at(text, a):
    i, j = tuntutan_range(text)
    if not i <= a < j:
        return ""
    cuts = [i, j] + [i + m.start() for m in re.finditer(r"\n|\s(?=\d{1,2}\s?[.)]\s+[A-Z])", text[i:j])]
    return text[max(c for c in cuts if c <= a):min(c for c in cuts if c > a)]


def span_demand(text, spans):
    if not spans:
        return NM, NM
    s = prefer_tuntutan(text, spans, r"tahun|bulan|hari|seumur|mati")[0][1].lower()
    s = re.split(r"\bdenda\b|subsid|pengganti|masa\s+percobaan|barang\s+bukti", s)[0]
    if "seumur hidup" in s:
        return "seumur_hidup", NA
    if re.search(r"pidana\s+mati", s):
        return "mati", NA
    kind = "kurungan" if "kurungan" in s and "penjara" not in s else \
        "rehabilitasi" if "rehabilitasi" in s and "penjara" not in s else "penjara"
    y, m, d = (r.num_before(u, s)[0] or 0 for u in ("tahun", "bulan", "hari"))
    total = y * 12 + m + round(d / 30, 1)
    return kind, total if total > 0 else NM


def parse_span(text, i, s):
    end = i + len(s)
    back = list(re.finditer(r"pasal", text[max(0, i - 60):i], re.I))
    if back and not re.match(r"pasal", s, re.I):
        i = max(0, i - 60) + back[-1].start()
    head = "Pasal " if re.match(r"\d+\s*(ayat|huruf)", text[i:], re.I) else ""
    for extra in (0, 100, 200, 300):
        found = r.parse_articles(head + re.sub(r"(\d)([A-Z]{3,})", r"\1 \2", text[i:end + extra]))
        if found:
            return found
    return []


def span_articles(text, spans):
    spans = [x for x in spans if not r.NOT_PROVEN.search(item_at(text, x[0]))] or spans
    for group in (prefer_tuntutan(text, spans, r"\d"), spans):
        arts = []
        for i, s in group:
            arts += [a for a in parse_span(text, i, s) if a not in arts]
        if arts:
            return arts
    return NM


def span_victims(spans):
    joined = " ".join(spans)
    m = re.search(r"(\d+)\s*(?:\([^)]*\)\s*)?orang", joined)
    if m:
        return int(m.group(1))
    names = []
    for rx in r.VICTIM_PATTERNS:
        for n in rx.findall(joined):
            first = n.split()[0].lower()
            if len(first) > 1 and not any(r.similar_name(first, x) for x in names):
                names.append(first)
    return len(names) or 1


def by_lexicon(spans, lexicon, found_default):
    for label, rx in lexicon:
        if any(re.search(rx, s, re.I) for s in spans):
            return label
    return found_default if spans else "none"


# ---- notebook cell 77 ----
def span_loss(spans):
    vals = sorted({v for s in spans for v in map(r.rupiah, re.findall(r"Rp\.?\s*([\d.,]+)", s)) if v and v >= 1000})
    if not vals:
        return NM
    total = [r.rupiah(m) for s in spans if re.search(r"total", s, re.I) for m in re.findall(r"Rp\.?\s*([\d.,]+)", s)]
    return total[0] if total else vals[-1]


def span_factors(text, agg_spans, mit_spans):
    codes = {"agg": [], "mit": []}
    for side, spans in (("agg", agg_spans), ("mit", mit_spans)):
        for s in (x for sp in spans for x in re.split(r"\n|;", sp)):
            if len(s) < 10 or r.NONE_ITEM.search(s) or r.NOISE_ITEM.search(s):
                continue
            found = r.classify(s) or ({f"other_{'aggravating' if side == 'agg' else 'mitigating'}": side}
                                      if len(s.split()) >= 4 else {})
            for code, code_side in found.items():
                if code not in codes[code_side]:
                    codes[code_side].append(code)
    has = {"agg": "### keadaan_memberatkan" in text, "mit": "### keadaan_meringankan" in text}
    return [codes[s] if codes[s] or has[s] else NM for s in ("agg", "mit")]


def extract_bert(tagger, doc, crime=None):
    text = r.excerpt(doc)
    pos, n_windows = tagger.tag(text)
    sp = {t: [s for _, s in v] for t, v in pos.items()}
    arts = span_articles(text, pos.get("ARTICLE", []))
    ctype = crime or (r.crime_type(arts) if isinstance(arts, list) else None)
    rec = r.empty_record(doc.doc_id, ctype)
    age = re.search(r"\d{1,3}", " ".join(sp.get("AGE", [])))
    rec["defendant_age"] = int(age.group()) if age and 8 <= int(age.group()) <= 100 else NM
    rec["prosecutor_demand_type"], rec["prosecutor_demand_months"] = span_demand(text, pos.get("DEMAND", []))
    rec["article_charged"] = arts

    if ctype in r.VICTIMLESS_CRIMES or (isinstance(arts, list) and r.victimless_law(arts)):
        rec.update({f: NA for f in r.VICTIM_FIELDS})
    else:
        rec["loss_value"] = span_loss(sp.get("LOSS", []))
        if ctype in r.STATE_LOSS_CRIMES:
            rec.update({f: NA for f in r.PERSON_FIELDS})
        elif sp.get("VICTIM") or ctype in r.PROPERTY_CRIMES:
            rec["victim_count"] = span_victims(sp.get("VICTIM", []))
            rec["victim_injury"] = by_lexicon(sp.get("INJURY", []), [("death", r"meninggal\s+dunia|kematian|tewas"),
                                                                     ("serious", r"\bserius\b")] + r.INJURY, "minor")
            rec["weapon_used"] = by_lexicon(sp.get("WEAPON", []), r.WEAPON, "other")

    rec["aggravating_factors"], rec["mitigating_factors"] = span_factors(text, sp.get("AGG", []), sp.get("MIT", []))
    rec.update(r.bools_from_codes(rec["aggravating_factors"], rec["mitigating_factors"]))
    agg_text = " ".join(sp.get("AGG", [])).lower()
    for field, rx in (("confession", r"tidak\s+mengakui"), ("remorse", r"tidak\s+menyesal|tidak\s+ada\s+penyesalan"),
                      ("cooperative", r"(?<!tidak\s)berbelit|tidak\s+kooperatif")):
        if rec[field] == NM and re.search(rx, agg_text):
            rec[field] = False
    rec["crime_type_provisional"] = ctype
    spans = {t: [s[:220] for _, s in v][:4] for t, v in pos.items()}
    return rec, {"excerpt_chars": len(text), "windows": n_windows, "spans": spans}


class Task2:
    def __init__(self):
        model_dir = TASK2_DIR / "bert_model"
        self.tagger = BertTagger(model_dir) if (model_dir / "model.safetensors").exists() else None

    def run(self, raw, doc_id, crime_task1):
        paras, sections, stats = r.clean_text(raw)
        doc = r.Doc(doc_id, paras, sections, stats)
        crime = TASK1_TO_TASK2.get(crime_task1, crime_task1)

        rule = r.extract(doc, crime=crime)
        evidence = rule.pop("evidence", {})
        rule.pop("notes", None)

        bert_info = None
        if self.tagger is None:
            record, route = dict(rule), {f: "rule" for f in SLOT_ORDER}
        elif crime in r.VICTIMLESS_CRIMES and set(BERT_FIELDS) <= set(r.VICTIM_FIELDS):
            record = {**rule, **{f: NA for f in r.VICTIM_FIELDS}}
            route = {f: ("rule" if f not in BERT_FIELDS else "not_applicable") for f in SLOT_ORDER}
            bert_info = {"skipped": "victimless crime, the statistical slots do not apply"}
        else:
            bert, bert_info = extract_bert(self.tagger, doc, crime=crime)
            record = {**rule, **{f: bert[f] for f in BERT_FIELDS}}
            route = {f: ("bert" if f in BERT_FIELDS else "rule") for f in SLOT_ORDER}

        section_view = [
            {"name": name, "paragraphs": end - start, "preview": paras[start][:180]}
            for name, (start, end) in sections.items()
        ]
        pseudo = next((p for p in paras[:80] if "[TERDAKWA]" in p), None)
        return {
            "record": {f: record[f] for f in SLOT_ORDER},
            "crime_type_used": crime,
            "route": route,
            "evidence": {k: (v if isinstance(v, list) else [v]) for k, v in evidence.items() if v},
            "stats": {k: stats[k] for k in ("raw_words", "clean_words", "verdict_masked", "pseudonym_replacements")},
            "paragraphs": len(paras),
            "sections": section_view,
            "pseudonym_example": pseudo[:200] if pseudo else None,
            "bert": bert_info,
        }
