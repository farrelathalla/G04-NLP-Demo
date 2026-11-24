"""Task 2 symbolic route and shared helpers.

The code below is copied unchanged from runned/task2_information_extraction.ipynb
(cells 18, 19, 20, 32, 57, 59 to 62, and 68) so the demo extracts exactly what the
notebook extracted. Only the imports and the Doc container were added.
"""
import re
import unicodedata
from dataclasses import dataclass
from difflib import SequenceMatcher


@dataclass
class Doc:
    doc_id: str
    paragraphs: list
    spans: dict
    stats: dict

    @property
    def text(self):
        return "\n".join(self.paragraphs)

    def section(self, *names):
        return "\n".join(p for n in names if n in self.spans
                         for p in self.paragraphs[self.spans[n][0]:self.spans[n][1]])


# ---- notebook cell 18 ----
WATERMARK_LINES = {
    "hkama",
    "ahkamah Agung Repub",
    "ahkamah Agung Republik Indonesia",
    "mah Agung Republik Indonesia",
    "blik Indonesi",
    "Direktori Putusan Mahkamah Agung Republik Indonesia",
    "Disclaimer",
}
NOISE_PATTERNS = [
    re.compile(r"^Kepaniteraan Mahkamah Agung Republik Indonesia berusaha untuk selalu"),
    re.compile(r"^pelaksanaan fungsi peradilan\. Namun dalam hal-hal tertentu"),
    re.compile(r"^Dalam hal Anda menemukan inakurasi informasi"),
    re.compile(r"^Email\s*:\s*kepaniteraan@mahkamahagung\.go\.id"),
    re.compile(r"transparansi dan akuntabilitas\s*$"),
    re.compile(r"^Halaman\s+\d+\s*$", re.I),
    re.compile(r"^Hal(aman)?\.?\s*\d+\s*(dari|/)\s*(hal\.?\s*)?\d+\b.{0,80}$", re.I),
    re.compile(r"^.{0,80}\bHal(aman)?\.?\s*\d+\s*dari\s*(hal(aman)?\.?\s*)?\d+\b.{0,40}$", re.I),
]
CHAR_MAP = str.maketrans({
    "\u201c": '"', "\u201d": '"', "\u201e": '"', "\u2033": '"',
    "\u2018": "'", "\u2019": "'", "\u2032": "'", "`": "'",
    "\u2012": "-", "\u2013": "-", "\u2014": "-", "\u2015": "-", "\u2212": "-",
    "\u2022": "-", "\u00b7": "-", "\uf0b7": "-", "\uf02d": "-",
    "\u00a0": " ", "\u2009": " ", "\u200b": "", "\ufeff": "",
})


def is_noise(line):
    return line in WATERMARK_LINES or any(p.search(line) for p in NOISE_PATTERNS)


def normalise_line(line):
    line = unicodedata.normalize("NFKC", line).translate(CHAR_MAP)
    return re.sub(r"[ \t]+", " ", line).strip()
STRUCT_START = re.compile(
    r"^(Menimbang|Mengingat|Memperhatikan|M ?E ?N ?G ?A ?D ?I ?L ?I\b|Setelah\b|Telah\b|"
    r"Membaca\b|Mendengar\b|Keadaan(-keadaan)? [Yy]ang|Hal-hal [Yy]ang|Hal [Yy]ang|"
    r"Hal (memberatkan|meringankan)|Demikian(lah)? diputuskan|"
    r"P ?U ?T ?U ?S ?A ?N\b|DEMI KEADILAN|DAKWAAN|PRIMAIR|PRIMER|SUBSIDAIR|SUBSIDER|"
    r"LEBIH SUBSIDAIR|KESATU|KEDUA|KETIGA|ATAU\b|DAN\b|"
    r"Nama( Lengkap)?\b|Tempat [Ll]ahir|Umur|Tanggal [Ll]ahir|Jenis [Kk]elamin|Kebangsaan|"
    r"Kewarganegaraan|Tempat ?[Tt]inggal|Alamat\b|Agama\b|A g a m a|Pekerjaan\b|Pendidikan\b|"
    r"Terdakwa\s+(?:\S+\s+){0,8}?(?:ditangkap|ditahan|tidak\s+ditahan|menghadap|didampingi))"
)
LIST_MARKER = re.compile(r"^(\d{1,2}[.)]|[a-zA-Z][.)]|-|\*|[ivxIVX]{1,4}[.)])(\s|$)")
LONE_MARKER = re.compile(r"^(\d{1,2}[.)]|[a-zA-Z][.)]|-|\*|[ivxIVX]{1,4}[.)]|:)$")
INLINE_HEADING = re.compile(
    r"(?<=[.;])\s+(?=(?:Keadaan(?:-keadaan)?|Hal-hal|Hal)\s+(?:yang\s+)?(?:memberatkan|meringankan)\s*:)",
    re.I,
)


def join_paragraphs(lines):
    paras, buf, glue_next = [], "", False
    for line in lines:
        if not line:
            continue
        if line == ":":
            buf = f"{buf} :" if buf else ":"
            glue_next = True
            continue
        starts_new = not glue_next and buf and (
            STRUCT_START.match(line) or LIST_MARKER.match(line) or buf.endswith(";"))
        if starts_new:
            paras.append(buf)
            buf = line
        elif not buf:
            buf = line
        elif buf.endswith("-") and not buf.endswith(" -") and len(buf) > 1:
            buf += line
        else:
            buf = f"{buf} {line}"
        glue_next = bool(LONE_MARKER.match(line))
    if buf:
        paras.append(buf)
    out = []
    for p in paras:
        out.extend(s.strip() for s in INLINE_HEADING.split(re.sub(r"\s+", " ", p)) if s.strip())
    return out
COLON_RUN = re.compile(r"^(?P<label>.*?)\s*(?P<colons>(?::\s*){2,})(?P<v>.*)$")


def fix_identity_table(paras, head_limit=60):
    for i, p in enumerate(paras[:head_limit]):
        m = COLON_RUN.match(p)
        if not m:
            continue
        n = m.group("colons").count(":")
        start = i - (n - 1)
        if start < 0 or i + n - 1 >= len(paras):
            continue
        labels = paras[start:i] + [m.group("label")]
        labels[0] = re.sub(r"^(\d{1,2}\.\s*)+", "", labels[0])
        values = [m.group("v")] + paras[i + 1:i + n]
        rebuilt = [f"{l.strip()} : {v.strip()}" for l, v in zip(labels, values)]
        return paras[:start] + rebuilt + paras[i + n:]
    return paras
MENGADILI = re.compile(r"^M ?E ?N ?G ?A ?D ?I ?L ?I\s*:?")


# ---- notebook cell 19 ----
MENIMBANG = re.compile(r"^Menimbang", re.I)
CLOSING = re.compile(r"^Demikian(lah)?\s+(diputuskan|putusan)", re.I)
LEGAL_BASIS = re.compile(r"^(Memperhatikan|Mengingat)\b", re.I)
AMAR_ITEM = re.compile(
    r"^(\d{1,2}\s*[.)]\s*|-\s*)?(Menyatakan\s+(para\s+)?Terdakwa|Menjatuhkan\s+pidana|"
    r"Membebaskan\s+(para\s+)?Terdakwa|Melepaskan\s+(para\s+)?Terdakwa)",
    re.I,
)


def no_menimbang_after(paras, i):
    return not any(MENIMBANG.match(p) for p in paras[i + 1:])


def mask_verdict(paras):
    idx = [i for i, p in enumerate(paras) if MENGADILI.match(p)]
    if idx and no_menimbang_after(paras, idx[-1]):
        return paras[:idx[-1]], True
    basis = [i for i, p in enumerate(paras) if LEGAL_BASIS.match(p)]
    if basis and no_menimbang_after(paras, basis[-1]):
        for j in range(basis[-1] + 1, len(paras)):
            if AMAR_ITEM.match(paras[j]) or CLOSING.match(paras[j]):
                return paras[:j], True
    for i, p in enumerate(paras):
        if CLOSING.match(p) and no_menimbang_after(paras, i):
            return paras[:i], True
    return paras, False
_ITEM = r"^(?:\d{1,2}\s*[.)]\s*|[a-z]\s*[.)]\s*)?"
NAME_LINE = re.compile(
    _ITEM + r"Nama\s*(?:(?:[lI]engkap|Terdakwa)\s*(?:Terdakwa\s*)?:?|:)\s*(?P<v>\S.+)$", re.I)
ADDRESS_LINE = re.compile(
    _ITEM + r"(?P<k>Tempat\s*[Tt]inggal|Alamat|Tempat\s+[Kk]ediaman)\s*:?\s*(?P<v>\S.+)$", re.I)
NAME_SPLIT = re.compile(r"\s+(?:als\.?|alias\.?|@)\s+|\s*[;,]\s*", re.I)
PARENT_SPLIT = re.compile(r"\s+(?:bin|binti|anak dari|anak|putra dari|putri dari)\s+", re.I)
TRAILING_JUNK = re.compile(r"[\s.;:,]+$")
COMMON_TOKENS = {
    "agung", "negeri", "umum", "hakim", "jaksa", "terdakwa", "saksi", "negara",
    "republik", "indonesia", "pengadilan", "putusan", "pidana", "tahun", "bulan",
    "hari", "laki", "perempuan", "islam", "kristen", "desa", "kota", "jalan",
}


def phrase_regex(phrase):
    tokens = [re.escape(t) for t in phrase.split()]
    if not tokens:
        return None
    if len(tokens) == 1 and (len(phrase) < 4 or phrase.lower() in COMMON_TOKENS):
        return None
    return re.compile(rf"(?<![\w\[]){r'[\s.]+'.join(tokens)}(?![\w\]])", re.I)


def split_names(text):
    return [TRAILING_JUNK.sub("", n).strip() for n in NAME_SPLIT.split(text) if n.strip()] if text else []


def pseudonymise(paras, head_limit=120):
    names, parents, out = [], [], list(paras)
    for i, p in enumerate(paras[:head_limit]):
        if MENIMBANG.match(p):
            break
        m = NAME_LINE.match(p)
        if m:
            value = re.sub(r"\(\s*alm\.?h?\s*\)", " ", m.group("v"), flags=re.I)
            value = re.split(r"\s+(Tempat|Umur|Jenis|Kebangsaan)\b", TRAILING_JUNK.sub("", value))[0]
            pieces = PARENT_SPLIT.split(value, maxsplit=1)
            names += split_names(pieces[0])
            parents += split_names(pieces[1] if len(pieces) > 1 else "")
            continue
        m = ADDRESS_LINE.match(p)
        if m:
            out[i] = f"{m.group('k')} : [ALAMAT]"

    pairs = sorted([(n, "[TERDAKWA]") for n in names] + [(n, "[ORANG_TUA]") for n in parents],
                   key=lambda x: -len(x[0]))
    subs = [(rx, tag) for phrase, tag in pairs if (rx := phrase_regex(phrase))]

    count = 0

    def replacer(tag):
        def repl(m):
            nonlocal count
            if not m.group(0)[0].isupper():
                return m.group(0)
            count += 1
            return tag
        return repl

    for i, p in enumerate(out):
        for rx, tag in subs:
            p = rx.sub(replacer(tag), p)
        out[i] = p
    return out, count
SECTION_ORDER = [
    "identitas", "tuntutan", "dakwaan", "pembuktian", "fakta_hukum",
    "pertimbangan", "keadaan_memberatkan", "keadaan_meringankan", "memperhatikan",
]
TUNTUTAN = re.compile(r"tuntutan\s+pidana|requisitoir|menuntut\s+(supaya|agar)|"
                      r"(mendengar|membaca)\s+(pembacaan\s+)?tuntutan", re.I)
DAKWAAN = re.compile(r"didakwa|surat\s+dakwaan", re.I)
FAKTA = re.compile(r"fakta[- ]fakta\s+hukum|fakta\s+hukum|fakta[- ]fakta\s+yang\s+terungkap", re.I)
UNSUR = re.compile(r"unsur[- ]unsur|unsur\s+[\"']?\w", re.I)


# ---- notebook cell 20 ----
MEMBERATKAN_ANY = re.compile(r"(keadaan(-keadaan)?|hal[- ]hal|hal)\s+(yang\s+)?memberatkan", re.I)
LIST_ITEM = re.compile(r"^(\d{1,2}[.)]|[a-zA-Z][.)]|-|\*)(\s|$)")
NEXT_BLOCK = re.compile(r"^(Setelah|Telah|Mendengar|Membaca|Menimbang)\b", re.I)
_HEAD = r"^-?(?:\d\.)?(?:keadaan(?:-keadaan)?|hal-?hal|hal)(?:yang)?"
FUZZY_HEAD = {
    "memberatkan": re.compile(_HEAD + r"mem?\w{0,2}berat\w{0,3}kan"),
    "meringankan": re.compile(_HEAD + r"me\w{0,3}ring\w{0,4}kan"),
}


def is_heading(p, kind):
    if len(p) > 80 and ":" not in p[:80]:
        return False
    return bool(FUZZY_HEAD[kind].match(re.sub(r"\s+", "", p.lower()).replace("rn", "m")))


def first(paras, rx, start=0, end=None, match=False):
    for i in range(start, len(paras) if end is None else end):
        if rx.match(paras[i]) if match else rx.search(paras[i]):
            return i
    return None


def last(paras, cond):
    return next((i for i in range(len(paras) - 1, -1, -1) if cond(paras[i])), None)


def block_end(paras, start, stop_at_basis=False):
    ends = [first(paras, MENIMBANG, start + 1, match=True)]
    if stop_at_basis:
        ends.append(first(paras, LEGAL_BASIS, start + 1, match=True))
    return min([e for e in ends if e is not None] or [len(paras)])


def split_sections(paras):
    n = len(paras)
    spans = {}
    first_menimbang = first(paras, MENIMBANG, match=True)

    t = first(paras, TUNTUTAN, 0, first_menimbang or n)
    if t is None:
        t = first(paras, TUNTUTAN)
    if t is not None:
        e = t + 1
        while e < n and e - t <= 40 and (LIST_ITEM.match(paras[e]) or not NEXT_BLOCK.match(paras[e])):
            e += 1
        spans["tuntutan"] = [t, e]

    spans["identitas"] = [0, min(x for x in [t, first_menimbang, n] if x is not None)]

    d = first(paras, DAKWAAN, first_menimbang or 0)
    if d is not None:
        spans["dakwaan"] = [d, block_end(paras, d)]

    mb = last(paras, lambda p: is_heading(p, "memberatkan"))
    if mb is None:
        mb = last(paras, MEMBERATKAN_ANY.search)
    if mb is not None:
        mr = next((i for i in range(mb + 1, min(block_end(paras, mb, True) + 1, n))
                   if is_heading(paras[i], "meringankan")), None)
    else:
        mr = last(paras, lambda p: is_heading(p, "meringankan"))
    if mb is not None:
        spans["keadaan_memberatkan"] = [mb, mr if mr is not None else block_end(paras, mb, True)]
    if mr is not None:
        spans["keadaan_meringankan"] = [mr, block_end(paras, mr, True)]

    m = last(paras, LEGAL_BASIS.match)
    if m is not None:
        spans["memperhatikan"] = [m, n]

    lo = spans.get("dakwaan", [0, 0])[1]
    hi = mb if mb is not None else spans.get("memperhatikan", [n])[0]
    f = first(paras, FAKTA, lo, hi)
    if f is not None:
        u = first(paras, UNSUR, f + 1, hi)
        spans["pembuktian"] = [lo, f]
        spans["fakta_hukum"] = [f, u if u is not None else hi]
        if u is not None:
            spans["pertimbangan"] = [u, hi]
    elif lo < hi:
        spans["pembuktian"] = [lo, hi]

    return {k: spans[k] for k in SECTION_ORDER if k in spans and spans[k][0] < spans[k][1]}


def clean_text(raw):
    lines = [normalise_line(l) for l in raw.splitlines() if not (l.strip() and is_noise(l.strip()))]
    paras = fix_identity_table(join_paragraphs(lines))
    paras, masked = mask_verdict(paras)
    paras, n_pseudo = pseudonymise(paras)
    sections = split_sections(paras)
    stats = {
        "raw_words": len(raw.split()),
        "clean_words": sum(len(p.split()) for p in paras),
        "verdict_masked": int(masked),
        "pseudonym_replacements": n_pseudo,
        **{f"has_{s}": int(s in sections) for s in SECTION_ORDER},
    }
    return paras, sections, stats


# ---- notebook cell 32 ----
NM = "not_mentioned"
NA = "not_applicable"
MISSING = {NM, NA}
DEMAND_TYPES = ["penjara", "kurungan", "seumur_hidup", "mati", "rehabilitasi", "bebas"]
INJURY_LEVELS = ["none", "psychological", "minor", "serious", "death"]
WEAPON_TYPES = ["none", "sharp", "blunt", "firearm", "other"]
FIELDS = {
    "defendant_age":           {"type": "int", "unit": "years"},
    "prosecutor_demand_type":  {"type": "enum", "values": DEMAND_TYPES},
    "prosecutor_demand_months": {"type": "float", "unit": "months"},
    "article_charged":         {"type": "list[str]"},
    "victim_count":            {"type": "int"},
    "victim_injury":           {"type": "enum", "values": INJURY_LEVELS},
    "weapon_used":             {"type": "enum", "values": WEAPON_TYPES},
    "loss_value":              {"type": "int", "unit": "rupiah"},
    "prior_conviction":        {"type": "bool"},
    "confession":              {"type": "bool"},
    "remorse":                 {"type": "bool"},
    "cooperative":             {"type": "bool"},
    "aggravating_factors":     {"type": "codes", "values": None},
    "mitigating_factors":      {"type": "codes", "values": None},
}
AGGRAVATING = {
    "public_unrest":       "causes public unrest or disturbs public order",
    "against_gov_program": "works against a government program (narcotics, corruption, etc.)",
    "victim_loss":         "material loss to the victim, others, or the state",
    "victim_harm":         "the victim was injured, killed, traumatised, or endangered",
    "harm_to_youth":       "harms the young generation or the future of a child victim",
    "prior_conviction":    "previously convicted, recidivist, or serving another sentence",
    "enjoyed_proceeds":    "has enjoyed the proceeds of the crime",
    "evasive_or_denial":   "evasive, denies the act, or shows no remorse",
    "no_reconciliation":   "no reconciliation, the victim has not forgiven",
    "abuse_of_position":   "abuse of office, trust, or status (officer, religious figure, teacher, guardian)",
    "use_of_violence":     "violence, cruelty, or use of a weapon",
    "premeditated":        "the act was planned",
    "repeated_act":        "the act was repeated",
    "against_norms":       "against religious or moral norms",
    "other_aggravating":   "other aggravating factor not covered above",
}
MITIGATING = {
    "no_prior_conviction": "no prior conviction",
    "admission":           "admits the act, is forthright",
    "remorse":             "remorseful, promises not to reoffend",
    "polite_conduct":      "polite in court",
    "cooperative":         "cooperative, not evasive, eases the trial",
    "breadwinner":         "breadwinner or has dependants",
    "victim_forgiveness":  "reconciled, the victim forgives",
    "restitution":         "compensated the loss, returned goods, or paid compensation",
    "young_age":           "young, still in school, can still reform",
    "old_age_or_health":   "elderly or ill",
    "caregiver":           "pregnant, breastfeeding, or caring for young children",
    "no_proceeds_enjoyed": "has not enjoyed the proceeds",
    "other_mitigating":    "other mitigating factor not covered above",
}


FIELDS["aggravating_factors"]["values"] = list(AGGRAVATING)


FIELDS["mitigating_factors"]["values"] = list(MITIGATING)
VICTIMLESS_CRIMES = {"narkotika", "psikotropika", "perjudian", "kesehatan", "senjata", "sumber_daya_alam"}
STATE_LOSS_CRIMES = {"korupsi", "pencucian_uang"}
PERSON_FIELDS = ["victim_count", "victim_injury", "weapon_used"]
VICTIM_FIELDS = PERSON_FIELDS + ["loss_value"]


def empty_record(doc_id, crime_type=None):
    rec = {"doc_id": doc_id, **{f: NM for f in FIELDS}, "evidence": {}}
    if crime_type in VICTIMLESS_CRIMES:
        rec.update({f: NA for f in VICTIM_FIELDS})
    elif crime_type in STATE_LOSS_CRIMES:
        rec.update({f: NA for f in PERSON_FIELDS})
    return rec


# ---- notebook cell 57 ----
PASAL = re.compile(
    r"Pasal\s+(?P<num>\d+(?:\s?[A-Z]\b)?)(?P<bis>\s*bis\b)?"
    r"(?:\s+ayat\s*\(?\s*(?P<ayat>\d+)(?:\s*\))?(?P<ayat2>(?:\s*(?:,|dan|&)\s*(?:ayat\s*)?\(\s*\d+\s*\))*))?"
    r"(?:\s+huruf\s+\(?(?P<huruf>[a-z])\)?\b(?P<huruf2>(?:\s*(?:,|dan)\s*(?:huruf\s+)?\(?[a-z]\)?\b)*))?"
    r"(?:\s+(?P<kw>ke|angka)\s*-?\s*(?P<ke>\d+(?:\s*(?:,|dan|&)\s*(?:(?:ke|angka)\s*-?\s*)?\d+\b)*))?",
    re.I,
)
KUHP = re.compile(r"\bKUHP\b|KUH\s*Pidana|Kitab\s+Undang[-\s]+(?:Undang[-\s]+)?Hukum\s+Pidana", re.I)
KUHAP = re.compile(r"\bKUHAP\b|Hukum\s+Acara\s+Pidana", re.I)
UU = re.compile(
    r"(?:Undang[-\s]*Undang|UU|U\.U\.?)(?:[\s.]*Darurat)?(?:[\s.]*(?:R\.?I\.?|Republik\s+Indonesia))?"
    r"[\s.]*(?:No(?:mor)?\.?|Nr\.?)?\s*:?\s*(?P<no>\d+)\s*(?:Tahun|Th\.?|/)\s*(?P<year>\d{4})",
    re.I,
)
SKIP_LAWS = {"UU8/1981", "UU48/2009", "UU49/2009", "UU2/1986"}
OMNIBUS = {"UU11/2020", "UU6/2023"}


def _laws(text):
    out = [(m.start(), "KUHP") for m in KUHP.finditer(text)]
    out += [(m.start(), "KUHAP") for m in KUHAP.finditer(text)]
    out += [(m.start(), f"UU{int(m.group('no'))}/{m.group('year')}") for m in UU.finditer(text)]
    return sorted(out)


def parse_articles(text):
    laws = _laws(text)
    result = []
    for m in PASAL.finditer(text):
        after = [name for pos, name in laws if pos > m.end() - 1]
        if (m.group("kw") or "").lower() == "angka" and after and after[0] in OMNIBUS:
            continue
        law = next((name for name in after if name not in OMNIBUS), None)
        if law is None or law == "KUHAP" or law in SKIP_LAWS:
            continue
        num = re.match(r"(\d+)\s?([A-Za-z]?)", m.group("num"))
        base = f"{law}:{int(num.group(1))}{num.group(2).upper()}" + ("bis" if m.group("bis") else "")
        ayats = ([m.group("ayat")] + re.findall(r"\d+", m.group("ayat2") or "")) if m.group("ayat") else [None]
        kes = re.findall(r"\d+", m.group("ke") or "") or [None]
        hurufs = ([m.group("huruf")] + re.findall(r"\b([a-z])\b", m.group("huruf2") or "", re.I)) if m.group("huruf") else [""]
        for ay in ayats:
            for hf in hurufs:
                art = base + (f"({ay})" if ay else "") + hf.lower()
                for ke in kes:
                    a = art + (f"ke-{ke}" if ke else "")
                    if a not in result:
                        result.append(a)
    accessory = [a for a in result if re.match(r"KUHP:(55|56|64|65)\b", a)]
    return [a for a in result if a not in accessory] + accessory
KUHP_RANGES = [
    ((362, 367), "pencurian"), ((372, 377), "penggelapan"), ((378, 395), "penipuan"),
    ((351, 358), "penganiayaan"), ((170, 170), "penganiayaan"), ((303, 303), "perjudian"),
    ((338, 350), "pembunuhan"), ((368, 371), "pemerasan"), ((480, 481), "penadahan"),
    ((281, 296), "kesusilaan"), ((263, 276), "pemalsuan"), ((406, 412), "perusakan"),
]
UU_MAP = {
    "UU35/2009": "narkotika", "UU5/1997": "psikotropika",
    "UU35/2014": "perlindungan_anak", "UU23/2002": "perlindungan_anak", "UU17/2016": "perlindungan_anak",
    "UU31/1999": "korupsi", "UU20/2001": "korupsi", "UU23/2004": "kdrt",
    "UU12/1951": "senjata", "UU22/2009": "lalu_lintas", "UU36/2009": "kesehatan",
    "UU17/2023": "kesehatan", "UU11/2008": "ite", "UU19/2016": "ite", "UU1/2024": "ite",
    "UU21/2007": "perdagangan_orang", "UU8/2010": "pencucian_uang", "UU12/2022": "kekerasan_seksual",
}


def crime_type(articles):
    for a in articles:
        law, _, rest = a.partition(":")
        if law in UU_MAP:
            return UU_MAP[law]
        if law == "KUHP":
            num = int(re.match(r"\d+", rest).group())
            for (lo, hi), name in KUHP_RANGES:
                if lo <= num <= hi:
                    return name
    return "lainnya" if articles else None
VICTIMLESS_LAWS = {"UU41/1999", "UU18/2013", "UU22/2001", "UU31/2004", "UU45/2009", "UU6/2011",
                   "UU10/1995", "UU17/2006", "UU11/1995", "UU39/2007", "UU4/2009", "UU3/2020",
                   "UU32/2009", "UU5/1990"}
ONLINE_GAMBLING = re.compile(r"^UU(11/2008|19/2016|1/2024):(27\(2\)|45\(2\))")


def victimless_law(articles):
    return any(a.partition(":")[0] in VICTIMLESS_LAWS or ONLINE_GAMBLING.match(a) for a in articles)


# ---- notebook cell 59 ----
WORDS = {"nol": 0, "satu": 1, "se": 1, "dua": 2, "tiga": 3, "empat": 4, "lima": 5, "enam": 6,
         "tujuh": 7, "delapan": 8, "sembilan": 9, "sepuluh": 10, "sebelas": 11}


def word_number(text):
    total, cur = 0, 0
    for w in re.findall(r"[a-z]+", text.lower()):
        if w in WORDS:
            cur += WORDS[w]
        elif w == "belas":
            cur += 10
        elif w == "puluh":
            cur = (cur or 1) * 10
        elif w == "ratus":
            cur = (cur or 1) * 100
        elif w.startswith("se") and w[2:] in ("puluh", "ratus", "belas"):
            cur += {"puluh": 10, "ratus": 100, "belas": 11}[w[2:]]
    return total + cur or None


def num_before(unit, text):
    m = re.search(r"(\d+)\s*(?:\(([^()]*)\))?\s*" + unit + r"(?!\s*\d{4})", text, re.I) or \
        re.search(r"(\d+)\s*\(([^)]*?)\b" + unit + r"\b[^)]*\)", text, re.I)
    if m:
        return int(m.group(1)), m
    m = re.search(r"((?:(?:se|satu|dua|tiga|empat|lima|enam|tujuh|delapan|sembilan|sepuluh|sebelas)\w*\s+)"
                  r"(?:(?:belas|puluh|ratus|satu|dua|tiga|empat|lima|enam|tujuh|delapan|sembilan)\s+){0,3})" + unit,
                  text, re.I)
    if m:
        n = word_number(m.group(1))
        return (n, m) if n else (None, None)
    return None, None


def rupiah(s):
    s = s.strip().rstrip(",;")
    s = re.sub(r"[,.]\s*-+$|,00$|\.00$", "", s.strip())
    s = re.sub(r",\d{1,2}$", "", s)
    digits = re.sub(r"[^\d]", "", s)
    return int(digits) if digits else None
AGE = re.compile(r"Umur[^:\n]{0,40}:\s*(\d{1,3})\s*(?:\([^)]*\)\s*)?(?:tahun|th\b|/)", re.I)
AGE_AFTER_DATE = re.compile(r"Umur[^:\n]{0,40}:[^\n]{0,40}?\b(\d{1,3})\s*tahun", re.I)


def age(doc):
    head = doc.section("identitas") or doc.text[:5000]
    m = AGE.search(head) or AGE.search(doc.text[:5000]) or AGE_AFTER_DATE.search(head)
    if m and 8 <= int(m.group(1)) <= 100:
        return int(m.group(1)), m.group(0)
    return NM, None
DEMAND_ITEM = re.compile(r"m[ae]nj\s?atuh?kan\s+(pidana|hukuman)|menghukum\s+terdakwa|memidana\s+terdakwa|"
                         r"dijatuhi\s+pidana|dengan\s+pidana\s+penjara\s+selama", re.I)
DURATION = re.compile(r"\d+\s*(?:\([^)]*\))?\s*(?:tahun|bulan|hari)(?!\s*\d{4})|\d+\s*\([^)]*\b(?:tahun|bulan|hari)\b[^)]*\)", re.I)


def demand(doc):
    text = " ".join(doc.section("tuntutan").split("\n"))
    if not text:
        return NM, NM, None
    m = DEMAND_ITEM.search(text)
    if m is None:
        if re.search(r"membebaskan\s+terdakwa", text, re.I):
            return "bebas", NA, None
        return NM, NM, None
    item = text[m.start():m.start() + 500]
    item = re.sub(r"dakwaan\s+(lebih\s+)?(primai?r|subsid\w*)", "dakwaan", item, flags=re.I)
    low = item.lower()
    if "seumur hidup" in low:
        return "seumur_hidup", NA, item[:200]
    if re.search(r"pidana\s+mati", low):
        return "mati", NA, item[:200]
    main = re.split(r"\bdenda\b|subsid|pengganti|masa\s+percobaan|barang\s+bukti|\s\d\.\s+Menetapkan", item, flags=re.I)[0]
    kind = "kurungan" if re.search(r"kurungan", main, re.I) and not re.search(r"penjara", main, re.I) else "penjara"
    if not re.search(r"penjara|kurungan", main, re.I) and re.search(r"rehabilitasi", item, re.I):
        kind, main = "rehabilitasi", item
    d = DURATION.search(main)
    if d is None:
        return kind, NM, item[:200]
    seg = main[d.start():d.start() + 80]
    years, _ = num_before(r"tahun", seg)
    months, _ = num_before(r"bulan", seg)
    days, _ = num_before(r"hari", seg)
    total = (years or 0) * 12 + (months or 0) + round((days or 0) / 30, 1)
    return kind, (total if total > 0 else NM), main[max(0, d.start() - 40):d.start() + 60]
PROVEN = re.compile(r"(?:sebagaimana|diatur|melanggar|dalam)\b.{0,200}?Pasal", re.I)
NOT_PROVEN = re.compile(r"tidak\s+(terbukti|bersalah)|membebaskan", re.I)


def articles(doc):
    t = doc.section("tuntutan")
    items = [x for p in t.split("\n") for x in re.split(r"\s(?=\d{1,2}\s?[.)]\s+[A-Z])", p)]
    first = next((x for x in items if re.search(r"terbukti|bersalah", x, re.I) and not NOT_PROVEN.search(x)), "")
    arts = parse_articles(first)
    if arts:
        return arts, first
    basis = doc.section("memperhatikan")
    arts = parse_articles(basis)
    return (arts, basis) if arts else (NM, None)


def facts_text(doc):
    return doc.section("fakta_hukum") or doc.section("dakwaan")
LOSS = re.compile(r"(?:kerugian|merugikan)[^.;]{0,80}?(?:sebesar|sejumlah|senilai|kurang lebih|sekitar|\u00b1|total)?\s*"
                  r"Rp\.?\s*([\d.,]+(?:\s*,-)?)", re.I)


# ---- notebook cell 60 ----
def loss(doc):
    for sec in (doc.section("fakta_hukum"), doc.section("dakwaan"), doc.section("pertimbangan"),
                doc.section("pembuktian"), doc.text):
        sec = re.sub(r"\b(PT|CV|Tbk|No|Nomor|R\.I)\.", r"\1", sec)
        m = LOSS.search(sec)
        if m:
            v = rupiah(m.group(1))
            if v and v >= 1000:
                return v, m.group(0)
    return NM, None
NAME = r"([A-Z][A-Za-z.']+(?:\s+[A-Z][A-Za-z.']+){0,3})"
VICTIM_PATTERNS = [
    re.compile(r"(?:[Ss]aksi\s+)?(?:[Aa]nak\s+)?[Kk]orban\s+" + NAME),
    re.compile(r"(?:milik|kepunyaan|seizin(?:\s+dari)?|izin(?:\s+dari)?|persetujuan)\s+(?:[Ss]aksi\s+)(?:[Kk]orban\s+)?" + NAME),
]
NOT_NAMES = {"tersebut", "yang", "dan", "mengalami", "merasa", "terdakwa", "anak", "saksi", "korban", "pt", "cv",
             "laki", "perempuan", "setelah", "kemudian", "lalu", "pada", "dengan", "berdiri", "sedang", "saat", "ketika",
             "sehingga", "bahwa", "atas", "untuk", "dari", "di", "ke", "yaitu", "adalah", "selanjutnya", "lainnya"}


def similar_name(a, b):
    return SequenceMatcher(None, a.lower(), b.lower()).ratio() >= 0.8


def victims(doc):
    text = facts_text(doc) + "\n" + doc.section("dakwaan")
    first_tokens = {}
    for rx in VICTIM_PATTERNS:
        for n in rx.findall(text):
            n = re.sub(r"\s+(Alias|Als|Bin|Binti)\b.*", "", n).strip(" .")
            tok = n.split()[0].lower().strip(".")
            if tok not in NOT_NAMES and len(tok) > 1 and \
                    not any(similar_name(tok, t) for t in first_tokens):
                first_tokens[tok] = n
    if first_tokens:
        return len(first_tokens), ", ".join(first_tokens.values())
    if re.search(r"\bkorban\b", text, re.I):
        return 1, "korban"
    return NM, None
PROPERTY_CRIMES = {"pencurian", "penggelapan", "penipuan", "penadahan", "pemerasan", "perusakan"}
INJURY = [
    ("death", r"(?:korban|saksi)[^.;]{0,120}meninggal\s+dunia|meninggal\s+dunia[^.;]{0,40}korban|mengakibatkan\s+(?:matinya|kematian)"),
    ("serious", r"luka\s+berat|patah\s+tulang|cacat|rawat\s+inap|dirawat\s+di\s+rumah\s+sakit|dioperasi|operasi"),
    ("minor", r"\bluka|\bmemar\b|lecet|robek|bengkak|lebam|benjol"),
    ("psychological", r"trauma|ketakutan|psikis|depresi"),
]


def injury(doc):
    text = facts_text(doc) + "\n" + doc.section("keadaan_memberatkan")
    for label, rx in INJURY:
        m = re.search(rx, text, re.I)
        if m:
            return label, m.group(0)
    return "none", None
WEAPON = [
    ("firearm", r"senjata\s+api|pistol|revolver|senapan|airsoft"),
    ("sharp", r"senjata\s+tajam|sajam|pisau|parang|celurit|clurit|badik|golok|sabit|arit|keris|samurai|pedang|belati|cutter|kater|gunting"),
    ("blunt", r"\bkayu\b|balok|\bbatu\b|\bbesi\b|botol|\bhelm\b|palu|tongkat|pentungan|\bbata\b"),
]
ATTACK = r"memukul|dipukul|menusuk|ditusuk|membacok|dibacok|menebas|melukai|mengancam|diancam|menganiaya|menembak|ditembak|mengayunkan|menyabet"


def weapon(doc):
    text = facts_text(doc)
    for sent in re.split(r"(?<=[.;])\s+", text):
        if not re.search(ATTACK, sent, re.I):
            continue
        for label, rx in WEAPON:
            m = re.search(rx, sent, re.I)
            if m:
                return label, sent[:300]
    return "none", None
NEG_FIRST = [
    ("mit", "no_prior_conviction", r"(belum|tidak)\s+pernah\s+(di\s?hukum|dipidana|dijatuhi|terlibat|tersangkut|berurusan|"
                                   r"dihukum|menjalani|melakukan\s+tindak)"),
    ("mit", "cooperative", r"tidak\s+(berbelit|mempersulit)|^belit"),
    ("mit", "no_proceeds_enjoyed", r"(belum|tidak)\s+(sempat\s+)?menikmati"),
    ("agg", "no_reconciliation", r"(tidak|belum)\s+(ada(nya)?\s+|terjadi\s+)?(perdamaian|berdamai|dimaafkan|memaafkan|ada\s+i'?tikad)"),
    ("agg", "evasive_or_denial", r"tidak\s+(mengakui|menyesal|jujur|berterus\s+terang)|kurang\s+(jujur|terbuka)|tidak\s+ada\s+penyesalan|berbelit|mempersulit"),
]


# ---- notebook cell 61 ----
PATTERNS = [
    ("mit", "admission", r"mengaku|terus\s+terang|berterus\s+terang|membenarkan\s+perbuatan"),
    ("mit", "remorse", r"menyesal|penyesalan|merasa\s+bersalah|berjanji\s+(untuk\s+)?(tidak|tak)|tidak\s+akan\s+mengulangi"),
    ("mit", "polite_conduct", r"\bsopan\b|bersikap\s+baik|berlaku\s+baik|tata\s+tertib"),
    ("mit", "cooperative", r"ko+peratif|memperlancar|mempermudah|lancar"),
    ("mit", "breadwinner", r"tulang\s*punggung|tanggungan|nafkah|menafkahi|kepala\s+(rumah\s+tangga|keluarga)|tanggung\s+jawab\s+(terhadap\s+)?keluarga"),
    ("mit", "victim_forgiveness", r"memaafkan|dimaafkan|perdamaian|berdamai|\bdamai\b|meminta\s+maaf|permo\w+\s+maaf"),
    ("mit", "restitution", r"mengganti|ganti\s+rugi|mengembalikan|dikembalikan|santunan|membayar\s+kerugian"),
    ("mit", "young_age", r"masih\s+muda|(usia|berusia)\s+(relatif\s+)?muda|masih\s+sekolah|pelajar|mahasiswa|memperbaiki\s+diri|mengubah\s+(diri|sikap|perilaku)|"
                         r"diharapkan\s+(untuk\s+)?(mengubah|memperbaiki|berubah)|masa\s+depan(nya)?\s+masih"),
    ("mit", "old_age_or_health", r"lanjut\s+usia|lansia|sudah\s+tua|usia\s+lanjut|menderita\s+(sakit|penyakit)|"
                                 r"(sedang|dalam\s+keadaan)\s+sakit|sakit-sakitan|kondisi\s+kesehatan|riwayat\s+penyakit"),
    ("mit", "caregiver", r"hamil|menyusui|balita|anak\s+(yang\s+)?masih\s+kecil|\bbayi\b"),
    ("agg", "prior_conviction", r"(sudah|pernah|telah)\s+(pernah\s+)?(di\s?hukum|dipidana|dijatuhi)|residivis|sedang\s+menjalani\s+(pidana|hukuman)"),
    ("agg", "public_unrest", r"meresahka\w*|keresahan|ketertiban|mengganggu\s+(keamanan|ketenangan)"),
    ("agg", "against_gov_program", r"p\w?ogram\s+pemerintah|(upaya|usaha|kebijakan|peringatan)\s+pemerintah|tidak\s+mendukung\s+pemerintah|(upaya|usaha)\s+pemberantasan|"
                                   r"pemerintah\s+(yang\s+)?sedang|pemerintah\s+dan|program\s+pemberantasan|peredaran\s+narkotika"),
    ("agg", "victim_loss", r"merugikan|kerugian"),
    ("agg", "victim_harm", r"luka|cacat|trauma|membahayakan\s+(jiwa|nyawa)|penderitaan|rasa\s+sakit|ketakutan|tertekan|"
                           r"(menghilangkan|hilangnya)\s+nyawa|meninggal\s+dunia|"
                           r"(korban|saksi|anak)[^.;]{0,60}(meninggal|kematian)|meninggalnya"),
    ("agg", "harm_to_youth", r"generasi|masa\s+depan|merusak\s+(mental|moral)"),
    ("agg", "enjoyed_proceeds", r"(telah|sudah|sempat)\s+menikmati|untuk\s+kepentingan\s+(pribadi|sendiri|dirinya)|"
                                r"memperoleh\s+(uang|keuntungan)|memanfaatkan\s+uang"),
    ("agg", "abuse_of_position", r"jabatan|aparat|anggota\s+(polri|tni|kepolisian)|pegawai\s+negeri|\basn\b|tokoh|\bguru\b|kepercayaan|seharusnya\s+(melindungi|menjaga)|ayah\s+(kandung|tiri)"),
    ("agg", "use_of_violence", r"kekerasan|kejam|sadis|senjata"),
    ("agg", "premeditated", r"direncanakan|perencanaan|terencana"),
    ("agg", "repeated_act", r"berulang|sudah\s+sering|lebih\s+dari\s+(satu|sekali)|beberapa\s+kali|\d+\s*(\([^)]*\))?\s*kali"),
    ("agg", "against_norms", r"norma|kesusilaan|asusila|\bagama\b"),
]
NEG_SUPPRESS = {
    "no_prior_conviction": {"prior_conviction"}, "cooperative": {"evasive_or_denial"},
    "no_proceeds_enjoyed": {"enjoyed_proceeds"}, "no_reconciliation": {"victim_forgiveness"},
    "evasive_or_denial": {"admission", "remorse", "cooperative"},
}
CONFLICT = {"cooperative": "evasive_or_denial", "young_age": "harm_to_youth"}
NONE_ITEM = re.compile(r"^\s*(tidak\s+ada|tidak\s+ditemukan|nihil)\b", re.I)
NOISE_ITEM = re.compile(
    r"^(dan\s+)?((keadaan|hal)(-\w+)?\s+)?(yang\s+)?(memberatkan|meringankan|meringangkan)\b|"
    r"^dan\s+(yang\s+)?(meringankan|memberatkan)|^menimbang|biaya\s+perkara|^paraf|^putusan\s+nomor|"
    r"tujuan\s+pemidanaan|majelis\s+hakim\s+berpendapat",
    re.I,
)


def bullets(section_text):
    lines = section_text.split("\n")
    if not lines:
        return []
    head = re.sub(r"^.*?(memberatkan|meringankan)\w*\s*:?\s*", "", lines[0], count=1, flags=re.I)
    items = []
    for line in [head] + lines[1:]:
        for part in re.split(r"\s+-\s+|\s+\d{1,2}\.\s+(?=[A-Z])", line):
            part = re.sub(r"^(\d{1,2}[.)]|-|[a-z][.)])\s*", "", part.strip()).strip(" ;.")
            if len(part) >= 5:
                items.append(part)
    return items


def classify(item):
    low = item.lower()
    found = {}
    for side, code, rx in NEG_FIRST:
        if re.search(rx, low):
            found[code] = side
    for win, lose in CONFLICT.items():
        if win in found:
            found.pop(lose, None)
    blocked = set().union(*(NEG_SUPPRESS.get(c, set()) for c in found)) if found else set()
    for side, code, rx in PATTERNS:
        if code not in blocked and code not in found and re.search(rx, low):
            found[code] = side
    for win, lose in CONFLICT.items():
        if win in found:
            found.pop(lose, None)
    return found
INLINE_MIT = re.compile(r"(?:keadaan|hal)(?:[\s/-]*(?:keadaan|hal))*\s+yang\s+meringan[g]?kan\s*:?", re.I)


def factor_sections(doc):
    agg, mit = doc.section("keadaan_memberatkan"), doc.section("keadaan_meringankan")
    m = INLINE_MIT.search(agg, 40)
    if m and not mit.strip():
        agg, mit = agg[:m.start()], agg[m.start():]
    return {"agg": agg, "mit": mit}


# ---- notebook cell 62 ----
def factors(doc):
    agg, mit, ev_agg, ev_mit = [], [], [], []
    texts = factor_sections(doc)
    present = {side: bool(t.strip()) for side, t in texts.items()}
    for side in ("agg", "mit"):
        for item in bullets(texts[side]):
            if NONE_ITEM.search(item) or NOISE_ITEM.search(item):
                continue
            found = classify(item) or {f"other_{'aggravating' if side == 'agg' else 'mitigating'}": side}
            for code, code_side in found.items():
                target, ev = (agg, ev_agg) if code_side == "agg" else (mit, ev_mit)
                if code not in target:
                    target.append(code)
                    ev.append(item)
    out_agg = agg if present["agg"] or agg else NM
    out_mit = mit if present["mit"] or mit else NM
    return out_agg, out_mit, ev_agg, ev_mit


def bools_from_codes(agg, mit):
    agg = agg if isinstance(agg, list) else []
    mit = mit if isinstance(mit, list) else []
    def pick(true_if, false_if):
        return True if true_if else False if false_if else NM
    return {
        "prior_conviction": pick("prior_conviction" in agg, "no_prior_conviction" in mit),
        "confession": pick("admission" in mit, False),
        "remorse": pick("remorse" in mit, False),
        "cooperative": pick("polite_conduct" in mit or "cooperative" in mit, False),
    }


def denial_flags(doc):
    text = factor_sections(doc)["agg"].lower()
    return {
        "confession": bool(re.search(r"tidak\s+mengakui", text)),
        "remorse": bool(re.search(r"tidak\s+menyesal|tidak\s+ada\s+penyesalan", text)),
        "cooperative": bool(re.search(r"(?<!tidak\s)berbelit|tidak\s+kooperatif", text)),
    }


def extract(doc, crime=None):
    arts, art_ev = articles(doc)
    ctype = crime or (crime_type(arts) if isinstance(arts, list) else None)
    rec = empty_record(doc.doc_id, ctype)
    ev = {}

    rec["defendant_age"], ev["defendant_age"] = age(doc)
    rec["prosecutor_demand_type"], rec["prosecutor_demand_months"], ev["prosecutor_demand_months"] = demand(doc)
    rec["article_charged"], ev["article_charged"] = arts, art_ev

    no_victim = ctype in VICTIMLESS_CRIMES or (isinstance(arts, list) and victimless_law(arts))
    if no_victim:
        rec.update({f: NA for f in VICTIM_FIELDS})
    if not no_victim:
        rec["loss_value"], ev["loss_value"] = loss(doc)
    if not no_victim and ctype not in STATE_LOSS_CRIMES:
        rec["victim_count"], ev["victim_count"] = victims(doc)
        if rec["victim_count"] == NM and ctype in PROPERTY_CRIMES:
            rec["victim_count"] = 1
        if rec["victim_count"] == NM:
            rec["victim_injury"], rec["weapon_used"] = NM, NM
        else:
            rec["victim_injury"], ev["victim_injury"] = injury(doc)
            rec["weapon_used"], ev["weapon_used"] = weapon(doc)

    agg, mit, ev_agg, ev_mit = factors(doc)
    rec["aggravating_factors"], rec["mitigating_factors"] = agg, mit
    ev["aggravating_factors"], ev["mitigating_factors"] = ev_agg, ev_mit

    rec.update(bools_from_codes(agg, mit))
    for field, denied in denial_flags(doc).items():
        if denied and rec[field] == NM:
            rec[field] = False

    notes = []
    if isinstance(agg, list) and isinstance(mit, list) and "prior_conviction" in agg and "no_prior_conviction" in mit:
        rec["prior_conviction"] = NM
        notes.append("konflik prior_conviction (kemungkinan multi-terdakwa)")

    rec["evidence"] = {k: v for k, v in ev.items() if v}
    rec["notes"] = "; ".join(notes)
    rec["crime_type_provisional"] = ctype
    return rec


# ---- notebook cell 68 ----
EXCERPT = [("identitas", 1500), ("tuntutan", 3000), ("fakta_hukum", 10000),
           ("keadaan_memberatkan", 3000), ("keadaan_meringankan", 3000), ("memperhatikan", 1000)]
EXTRA = [(re.compile(r"kerugian|dirugikan|merugikan|kehilangan", re.I), re.compile(r"Rp\.?\s*\d")),
         (re.compile(r"visum", re.I), None)]
EXTRA_LIMIT = 3000


def excerpt(doc):
    parts = []
    sections = list(EXCERPT)
    if "fakta_hukum" not in doc.spans:
        sections.insert(2, ("dakwaan", 8000))
    for name, limit in sections:
        text = doc.section(name)
        if not text:
            continue
        cut = text[:limit]
        if len(text) > limit:
            cut += "\n[...dipotong...]"
        parts.append(f"### {name}\n{cut}")
    body = "\n\n".join(parts)
    extra, seen = [], set()
    paras = doc.paragraphs
    for i, p in enumerate(paras):
        if p[:200] in body:
            continue
        if p.rstrip().endswith(":") and i + 1 < len(paras):
            p = p + " " + " ".join(paras[i + 1:i + 3])[:400]
        end = 0
        for a, b in EXTRA:
            for m in a.finditer(p):
                if m.start() < end:
                    continue
                win = p[max(0, m.start() - 150): m.start() + 500]
                key = re.sub(r"\W+", "", p[m.start():m.start() + 150]).lower()
                if (b is None or b.search(win)) and key not in seen:
                    seen.add(key)
                    extra.append(win)
                    end = m.start() + 500
    if extra:
        cut = "\n".join(extra)
        parts.append("### kalimat_lain (kerugian/visum)\n" + cut[:EXTRA_LIMIT]
                     + ("\n[...dipotong...]" if len(cut) > EXTRA_LIMIT else ""))
    return f"doc_id: {doc.doc_id}\n\n" + "\n\n".join(parts) + "\n"
