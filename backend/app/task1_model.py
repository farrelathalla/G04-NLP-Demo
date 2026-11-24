"""Preprocessing and inference for the T3 crime classifier (TF-IDF word + char, Linear SVM).

The text functions are copied unchanged from runned/task1_crime_classification.ipynb.
"""
import json
import re
import unicodedata
from collections import Counter
from pathlib import Path

import numpy as np
import scipy.sparse as sp
import torch
from sklearn.feature_extraction.text import CountVectorizer
from sklearn.preprocessing import normalize

MAX_VIEW_CHARS = 90000
CHAR_TEXT_LIMIT = 8000
WORD_TOKEN_PATTERN = r'(?u)\b\w\w+\b'
CHECKPOINT_FORMAT = 1

CHAR_MAP = {
    0x2018: "'", 0x2019: "'", 0x201c: '"', 0x201d: '"',
    0x2013: '-', 0x2014: '-', 0x2212: '-', 0x00a0: ' ', 0x00ad: '',
}
NOISE_LINE = re.compile(
    r'^\s*(?:direktori putusan.*|putusan\.mahkamahagung.*|h?k?a?hkama\w*|ahkamah agung.*|'
    r'mah agung.*|blik indonesi.*|halaman\s+\d+.*|disclaimer.*)\s*$',
    re.I,
)
DISCLAIMER_PATTERNS = [
    re.compile(r'Kepaniteraan\s+Mahkamah\s+Agung\s+Republik\s+Indonesia\s+berusaha.{0,400}?akuntabilitas', re.I | re.S),
    re.compile(r'pelaksanaan\s+fungsi\s+peradilan\.?\s+Namun.{0,900}?\(ext\.?\s*318\)', re.I | re.S),
    re.compile(r'Dalam\s+hal\s+Anda\s+menemukan\s+inakurasi.{0,500}?\(ext\.?\s*318\)', re.I | re.S),
    re.compile(r'Email\s*:\s*kepaniteraan@\S+', re.I),
    re.compile(r'Telp\s*:\s*021-?\s*384\s*3348\s*\(ext\.?\s*318\)', re.I),
]
PAGE_MARK = re.compile(
    r'(?:Halaman|Hal\.?)\s*\d+\s*(?:dari|dr)\s*\d+\s*(?:hal\.?\s*)?(?:Putusan\s*)?(?:Pidana\s*)?(?:Nomor|No\.?)?\s*',
    re.I,
)
CASE_NUMBER = re.compile(r'\b\d+/Pid\.[\w.-]+/\d{4}/PN\s+\w+', re.I)
SPLIT_ARTICLE = re.compile(r'(Pasal\s+\d{1,2})\s+(\d{1,2})(?=\s+(?:KUH|ayat))', re.I)


def normalize_chars(text):
    return unicodedata.normalize('NFKC', text).translate(CHAR_MAP)


def clean_text(raw):
    text = normalize_chars(raw)
    text = '\n'.join(line for line in text.splitlines() if not NOISE_LINE.match(line))
    for pattern in DISCLAIMER_PATTERNS:
        text = pattern.sub(' ', text)
    text = PAGE_MARK.sub(' ', text)
    text = CASE_NUMBER.sub(' ', text)
    text = re.sub(r'(\w)-\s*\n\s*(\w)', r'\1-\2', text)
    text = SPLIT_ARTICLE.sub(r'\1\2', text)
    return re.sub(r'\s+', ' ', text).strip()


CLOSING = re.compile(r'\b(?:Memperhatikan|Mengingat)\b')
HAS_ARTICLE = re.compile(r'Pasal\s+\d+', re.I)


def closing_start(text):
    tail = max(0, len(text) - 3500)
    hits = list(CLOSING.finditer(text, tail))
    for hit in reversed(hits):
        if HAS_ARTICLE.search(text, hit.start()):
            return hit.start()
    return len(text)


CITATION = re.compile(
    r'Pasal\s+\d+\s*[A-Z]?(?![a-z])(?:\s*(?:ayat|ay\.?)\s*\(?\s*\d+\s*\)?)?(?:\s*(?:huruf|hrf\.?)\s*[a-z]\b)?(?:\s*ke-?\s*\d+)?'
    r'|(?:Undang\s*-?\s*Undang|UU\.?|Perppu)\D{0,45}?\d{1,3}\s*(?:Tahun|Thn\.?|Th\.?|/)\s*\d{4}'
    r'(?:\s+tentang\s+[^,.\x3b]{0,70})?'
    r'|Kitab\s+Undang\s*-?\s*Undang\s+Hukum\s+(?:Acara\s+)?Pidana|K\.?U\.?H\.?A?\.?P(?:idana)?\b',
    re.I,
)
NAME_FIELD = re.compile(r'Nama(?:\s+lengkap)?\s*:\s*(.{3,90}?)(?=\x3b|\s+\d+\s*[.)]|\s+Tempat\b|\s+Umur\b)', re.I)
NAME_STOP_TOKENS = {
    'alias', 'als', 'bin', 'binti', 'alm', 'almarhum', 'almarhumah', 'anak', 'terdakwa', 'saksi', 'korban',
    'nama', 'lengkap', 'panggilan', 'dan', 'dengan', 'yang', 'para', 'tempat', 'lahir', 'umur', 'tahun',
}
NAME_WITH_PATRONYM = re.compile(
    r"\b(?!(?:Terdakwa|Saksi|Anak|Korban|Majelis|Hakim|Penuntut|Umum|Para)\b)"
    r"[A-Z][\w'.]+(?:\s+[A-Z][\w'.]+){0,4}\s+(?:Bin|Binti|BIN|BINTI|Als\.?|ALS\.?|Alias|ALIAS)\s+"
    r"[A-Z][\w'.]+(?:\s+[A-Z][\w'.]+){0,3}"
)
NAME_AFTER_ROLE = re.compile(
    r"\b(Terdakwa|Saksi(?:\s+Korban)?|Korban|Sdr\.?|Sdri\.?|Anak\s+Saksi|Anak\s+Korban)\s+"
    r"((?:[A-Z]{2,}[A-Z'.]*\s*){1,5})"
)
OFFENCE_TERMS = re.compile(
    r'\b(?:pencurian|mencuri|dicuri|curian|penggelapan|menggelapkan|digelapkan|penipuan|menipu|ditipu|'
    r'penadahan|menadah|penadah|penganiayaan|menganiaya|dianiaya|pengeroyokan|mengeroyok|pembunuhan|'
    r'membunuh|dibunuh|persetubuhan|menyetubuhi|disetubuhi|pencabulan|mencabuli|dicabuli|pemerkosaan|'
    r'perkosaan|perjudian|berjudi|penjudi|narkotika|psikotropika|korupsi|pemerasan|memeras|diperas|'
    r'pengancaman|pemalsuan|memalsukan|dipalsukan|perdagangan\s+orang|tindak\s+pidana)\b',
    re.I,
)


def strip_citations(text):
    return re.sub(r'\s+', ' ', CITATION.sub(' [PASAL] ', text)).strip()


def defendant_tokens(text):
    tokens = set()
    for match in NAME_FIELD.finditer(text[:20000]):
        for token in re.findall(r"[A-Za-z']{3,}", match.group(1)):
            if token.lower() not in NAME_STOP_TOKENS:
                tokens.add(token.lower())
    return tokens


def pseudonymize(text, name_tokens=()):
    if name_tokens:
        ordered = sorted(map(re.escape, name_tokens), key=len, reverse=True)
        text = re.sub(r'\b(?:' + '|'.join(ordered) + r')\b', ' [NAMA] ', text, flags=re.I)
    text = NAME_WITH_PATRONYM.sub(' [NAMA] ', text)
    text = NAME_AFTER_ROLE.sub(lambda m: f'{m.group(1)} [NAMA] ', text)
    text = re.sub(r'(?:\[NAMA\]\s*)+', '[NAMA] ', text)
    return re.sub(r'\s+', ' ', text).strip()


def build_main_view(raw):
    """Build the leakage-safe `no_citation` view used to train T3."""
    text = clean_text(raw)
    body = text[:closing_start(text)]
    masked = pseudonymize(strip_citations(body), defendant_tokens(text))
    return masked[:MAX_VIEW_CHARS]


def build_views_for_paths(paths):
    return [build_main_view(Path(path).read_text(encoding='utf-8', errors='replace')) for path in paths]


def head_text(text):
    return text[:CHAR_TEXT_LIMIT].lower()


def _merge_counts(keys, dfs, tfs, new_keys, new_tfs):
    all_keys = np.concatenate([keys, *new_keys])
    all_dfs = np.concatenate([dfs, *[np.ones(len(part), dtype=np.int32) for part in new_keys]])
    all_tfs = np.concatenate([tfs, *new_tfs])
    order = np.argsort(all_keys)
    all_keys = all_keys[order]
    starts = np.flatnonzero(np.r_[True, all_keys[1:] != all_keys[:-1]])
    return all_keys[starts], np.add.reduceat(all_dfs[order], starts), np.add.reduceat(all_tfs[order], starts)


def select_vocabulary(analyzer, docs, min_df, max_df, max_features, flush_terms=6_000_000):
    """Low-memory equivalent of CountVectorizer's min_df, max_df, and max_features selection."""
    keys = np.empty(0, dtype=np.int64)
    dfs = np.empty(0, dtype=np.int32)
    tfs = np.empty(0, dtype=np.int64)
    key_buffer, tf_buffer, buffered = [], [], 0
    for doc in docs:
        counts = Counter(analyzer(doc))
        key_buffer.append(np.fromiter(map(hash, counts), dtype=np.int64, count=len(counts)))
        tf_buffer.append(np.fromiter(counts.values(), dtype=np.int64, count=len(counts)))
        buffered += len(counts)
        if buffered >= flush_terms:
            keys, dfs, tfs = _merge_counts(keys, dfs, tfs, key_buffer, tf_buffer)
            key_buffer, tf_buffer, buffered = [], [], 0
    if key_buffer:
        keys, dfs, tfs = _merge_counts(keys, dfs, tfs, key_buffer, tf_buffer)
    del key_buffer, tf_buffer

    mask = (dfs >= min_df) & (dfs <= max_df * len(docs))
    kept, kept_tfs = keys[mask], tfs[mask]
    del keys, dfs, tfs, mask
    names = [None] * len(kept)
    remaining = len(kept)
    for doc in docs:
        terms = list(set(analyzer(doc)))
        hashes = np.fromiter(map(hash, terms), dtype=np.int64, count=len(terms))
        positions = np.searchsorted(kept, hashes).clip(max=len(kept) - 1)
        for index in np.flatnonzero(kept[positions] == hashes):
            position = int(positions[index])
            if names[position] is None:
                names[position] = terms[index]
                remaining -= 1
        if remaining == 0:
            break
    if remaining:
        raise RuntimeError(f'{remaining} vocabulary terms were not recovered')

    order = sorted(range(len(names)), key=names.__getitem__)
    ordered_names = [names[i] for i in order]
    ordered_tfs = kept_tfs[np.asarray(order)]
    del names, order, kept, kept_tfs
    if len(ordered_names) > max_features:
        chosen = (-ordered_tfs).argsort()[:max_features]
        ordered_names = sorted(ordered_names[int(i)] for i in chosen)
    return {term: index for index, term in enumerate(ordered_names)}


def to_probability(scores):
    """Softmax over SVM margins. This is a relative confidence, not a calibrated probability."""
    scores = np.asarray(scores, dtype=np.float64)
    shifted = scores - scores.max(axis=1, keepdims=True)
    probability = np.exp(shifted)
    return probability / probability.sum(axis=1, keepdims=True)


def _terms(vectorizer):
    terms = [''] * len(vectorizer.vocabulary_)
    for term, index in vectorizer.vocabulary_.items():
        terms[index] = term
    return terms


def save_checkpoint(path, word_vectorizer, char_vectorizer, svm, classes, metadata):
    checkpoint = {
        'format': CHECKPOINT_FORMAT,
        'classes': list(classes),
        'word_terms': _terms(word_vectorizer),
        'char_terms': _terms(char_vectorizer),
        'word_idf': torch.from_numpy(np.asarray(word_vectorizer.idf_, dtype=np.float64)),
        'char_idf': torch.from_numpy(np.asarray(char_vectorizer.idf_, dtype=np.float64)),
        'coef': torch.from_numpy(svm.coef_.astype(np.float32)),
        'intercept': torch.from_numpy(svm.intercept_.astype(np.float32)),
        'metadata': json.loads(json.dumps(metadata)),
    }
    torch.save(checkpoint, path)


class CrimeClassifier:
    def __init__(self, checkpoint):
        if checkpoint.get('format') != CHECKPOINT_FORMAT:
            raise ValueError('Unsupported checkpoint format')
        self.classes = checkpoint['classes']
        self.metadata = checkpoint['metadata']
        self.word_idf = checkpoint['word_idf'].numpy()
        self.char_idf = checkpoint['char_idf'].numpy()
        self.coef = checkpoint['coef'].numpy()
        self.intercept = checkpoint['intercept'].numpy()
        self.word_counter = CountVectorizer(
            lowercase=True, ngram_range=(1, 2), token_pattern=WORD_TOKEN_PATTERN,
            vocabulary={term: i for i, term in enumerate(checkpoint['word_terms'])},
        )
        self.char_counter = CountVectorizer(
            analyzer='char_wb', ngram_range=(3, 5), preprocessor=head_text,
            vocabulary={term: i for i, term in enumerate(checkpoint['char_terms'])},
        )

    @classmethod
    def load(cls, path):
        return cls(torch.load(path, map_location='cpu', weights_only=True))

    @staticmethod
    def _tfidf(counter, idf, views):
        X = counter.transform(views).astype(np.float32).tocsr()
        X.sum_duplicates()
        X.data = 1 + np.log(X.data)
        X.data *= idf[X.indices]
        return normalize(X, norm='l2', copy=False)

    def decision_function(self, views):
        X = sp.hstack([
            self._tfidf(self.word_counter, self.word_idf, views),
            self._tfidf(self.char_counter, self.char_idf, views),
        ]).tocsr()
        return np.asarray(X @ self.coef.T) + self.intercept

    def predict_views(self, views):
        return self.decision_function(views).argmax(axis=1)

    def predict(self, raw_text, top_k=3):
        view = build_main_view(raw_text)
        if not view:
            raise ValueError('The document is empty after preprocessing')
        probability = to_probability(self.decision_function([view]))[0]
        order = np.argsort(probability)[::-1][:top_k]
        return {
            'label': self.classes[int(order[0])],
            'top': [{'label': self.classes[int(i)], 'confidence': float(probability[i])} for i in order],
        }
