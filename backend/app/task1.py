"""Task 1, crime type classification.

Runs the exported T3 model (word and character TF-IDF with a linear SVM) and records each
step so the frontend can show what happened to the text.
"""
import json
import re

import numpy as np

from . import task1_model as m
from .paths import TASK1_DIR


def _first_noise_lines(raw, limit=4):
    out = []
    for line in m.normalize_chars(raw).splitlines():
        if line.strip() and m.NOISE_LINE.match(line) and line.strip() not in out:
            out.append(line.strip())
        if len(out) >= limit:
            break
    return out


def _example_around(before, pattern, width=70):
    """Return a short window of text around the first match of a pattern."""
    hit = pattern.search(before)
    if not hit:
        return None
    start = max(0, hit.start() - width)
    end = min(len(before), hit.end() + width)
    return {"before": before[start:end].strip(), "match": hit.group(0)}


class Task1:
    def __init__(self):
        self.model = m.CrimeClassifier.load(TASK1_DIR / "t3_tfidf_word_char_svm.pt")
        self.word_terms = np.asarray(sorted(self.model.word_counter.vocabulary, key=self.model.word_counter.vocabulary.get))
        self.char_terms = np.asarray(sorted(self.model.char_counter.vocabulary, key=self.model.char_counter.vocabulary.get))
        self.metadata = json.loads((TASK1_DIR / "t3_metadata.json").read_text(encoding="utf-8"))

    def run(self, raw):
        steps = {}
        text = m.clean_text(raw)
        steps["clean"] = {
            "raw_chars": len(raw),
            "clean_chars": len(text),
            "removed_lines": _first_noise_lines(raw),
        }

        cut = m.closing_start(text)
        body = text[:cut]
        steps["closing"] = {"removed_chars": len(text) - cut, "preview": text[cut:cut + 160]}

        citation = _example_around(body, m.CITATION)
        stripped = m.strip_citations(body)
        steps["citations"] = {
            "count": len(m.CITATION.findall(body)),
            "example": citation,
        }

        tokens = m.defendant_tokens(text)
        masked = m.pseudonymize(stripped, tokens)
        name_example = None
        for token in sorted(tokens, key=len, reverse=True):
            found = re.search(r"\b" + re.escape(token) + r"\b", stripped, re.I)
            if found:
                start, end = found.start(), found.end()
                name_example = {
                    "match": found.group(0),
                    "left": stripped[max(0, start - 34):start],
                    "right": stripped[end:end + 26],
                }
                break
        steps["names"] = {"count": masked.count("[NAMA]"), "example": name_example}

        view = masked[:m.MAX_VIEW_CHARS]
        steps["view"] = {"chars": len(view), "words": len(view.split()), "preview": view[:420]}

        word_x = m.CrimeClassifier._tfidf(self.model.word_counter, self.model.word_idf, [view])
        char_x = m.CrimeClassifier._tfidf(self.model.char_counter, self.model.char_idf, [view])
        scores = self.model.decision_function([view])[0]
        probability = m.to_probability(scores[None, :])[0]
        order = np.argsort(probability)[::-1]
        best = int(order[0])

        def top_terms(x, terms, k):
            row = x.tocsr()
            idx = row.indices[np.argsort(row.data)[::-1][:k]]
            weights = {int(i): float(v) for i, v in zip(row.indices, row.data)}
            return [{"term": str(terms[i]), "weight": round(weights[int(i)], 4)} for i in idx]

        word_coef = self.model.coef[best, :len(self.word_terms)]
        contrib = word_x.multiply(word_coef).tocsr()
        top_contrib = contrib.indices[np.argsort(contrib.data)[::-1][:8]]
        contrib_values = {int(i): float(v) for i, v in zip(contrib.indices, contrib.data)}

        steps["tfidf"] = {
            "word_features": int(word_x.nnz),
            "char_features": int(char_x.nnz),
            "vocabulary": {"word": len(self.word_terms), "char": len(self.char_terms)},
            "top_words": top_terms(word_x, self.word_terms, 10),
            "top_chars": top_terms(char_x, self.char_terms, 6),
        }
        steps["svm"] = {
            "scores": [
                {"label": self.model.classes[int(i)], "margin": round(float(scores[i]), 4), "confidence": round(float(probability[i]), 4)}
                for i in order
            ],
            "evidence": [{"term": str(self.word_terms[i]), "contribution": round(contrib_values[int(i)], 4)} for i in top_contrib],
        }
        return {
            "label": self.model.classes[best],
            "confidence": round(float(probability[best]), 4),
            "top": steps["svm"]["scores"][:3],
            "steps": steps,
        }
