"""Render the demo decisions as formal looking PDF files.

Every line of the source txt is drawn as exactly one text line, in the same order as the
file, so a plain text extraction gives the original file back byte for byte. The script
checks this round trip for every document and fails loudly if a single byte differs.

Usage
    python scripts/make_demo_pdfs.py --docs <dir with doc_*.txt> --out <pdf dir>
"""
import argparse
import json
import re
import sys
from pathlib import Path

from reportlab.lib.colors import Color
from reportlab.lib.pagesizes import A4
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app.pdf_text import extract_text  # noqa: E402

FONT_DIR = Path("C:/Windows/Fonts")
FONTS = {
    "Serif": "times.ttf",
    "Serif-Bold": "timesbd.ttf",
    "Sans": "arial.ttf",
    "Sans-Bold": "arialbd.ttf",
}

PAGE_W, PAGE_H = A4
MARGIN_L, MARGIN_R = 78, 64
BODY_TOP, BODY_BOTTOM = PAGE_H - 92, 96
BODY_W = PAGE_W - MARGIN_L - MARGIN_R

INK = Color(0.11, 0.11, 0.12)
MUTED = Color(0.42, 0.42, 0.45)
FAINT = Color(0.80, 0.80, 0.83)
RULE = Color(0.78, 0.78, 0.80)

WATERMARK = {
    "hkama", "ahkamah Agung Repub", "ahkamah Agung Republik Indonesia",
    "mah Agung Republik Indonesia", "blik Indonesi",
}
HEADER = re.compile(r"^Direktori Putusan Mahkamah Agung Republik Indonesia\s*$")
FOOTER = re.compile(
    r"^(Halaman\s+\d+|Hal\.?\s*\d+\s*(dari|/)|pelaksanaan fungsi peradilan|Dalam hal Anda menemukan|"
    r"Email\s*:\s*kepaniteraan|Kepaniteraan Mahkamah Agung Republik Indonesia berusaha|Disclaimer)",
    re.I,
)
CENTER_HEADING = re.compile(
    r"^\s*(P\s*U\s*T\s*U\s*S\s*A\s*N|DEMI KEADILAN.*|M\s*E\s*N\s*G\s*A\s*D\s*I\s*L\s*I\s*:?|"
    r"Nomor\s*:?.{0,40}|T\s*E\s*R\s*D\s*A\s*K\s*W\s*A)\s*$"
)
PARA_END = re.compile(r"[;:.]\s*$")


def register_fonts():
    for name, file in FONTS.items():
        pdfmetrics.registerFont(TTFont(name, str(FONT_DIR / file)))


def split_pages(lines):
    """Split the file at each watermark block, which is where the source PDF started a page."""
    starts = [i for i, line in enumerate(lines) if line == "hkama"]
    if not starts or starts[0] != 0:
        starts = [0] + starts
    return [lines[a:b] for a, b in zip(starts, starts[1:] + [len(lines)])]


def classify(page):
    """Label every line of one page as watermark, header, top, body, or footer."""
    kinds = ["body"] * len(page)
    i = 0
    while i < len(page) and (page[i] in WATERMARK or HEADER.match(page[i])):
        kinds[i] = "watermark" if page[i] in WATERMARK else "header"
        i += 1
    j = i
    while j < len(page) and (page[j].strip() == "" or FOOTER.match(page[j])):
        if FOOTER.match(page[j]):
            for k in range(i, j + 1):
                kinds[k] = "top"
            i = j + 1
        j += 1
    end = len(page)
    while end > i and (FOOTER.match(page[end - 1]) or (page[end - 1].strip() == "" and end - 1 > i)):
        end -= 1
    for k in range(end, len(page)):
        if FOOTER.match(page[k]):
            kinds[k] = "footer"
    for k in range(end, len(page)):
        if kinds[k] == "body" and page[k].strip() == "":
            kinds[k] = "footer"
    return kinds


def fit_size(text, font, size, width, minimum=4.0):
    while size > minimum and pdfmetrics.stringWidth(text, font, size) > width:
        size -= 0.25
    return size


def draw_line(c, text, x, y, font, size, color, word_space=0.0):
    # Text state (word spacing) survives across text objects, so it is set on every line.
    t = c.beginText()
    t.setTextOrigin(x, y)
    t.setFont(font, size)
    t.setFillColor(color)
    t.setWordSpace(word_space)
    t.textOut(text)
    c.drawText(t)


MARKER = re.compile(r"^\s*(\d{1,2}\s*[.)]|-|[a-zA-Z]\s*[.)]|•)\s*$")
LABEL_TAB = 150
MARKER_INDENT = 20


def build_rows(page, kinds):
    """Group body lines into visual rows.

    A short label followed by a line that starts with a colon shares one row, like an
    identity table. A lone list marker shares a row with the line after it. Lines keep
    their order, only their position on the page changes.
    """
    rows, i = [], 0
    body = [k for k, kind in enumerate(kinds) if kind == "body"]
    body_set = set(body)
    while i < len(body):
        k = body[i]
        line = page[k].strip()
        nxt = k + 1 if k + 1 in body_set else None
        if nxt is not None and line and len(line) <= 34 and not line.startswith(":") \
                and not line.endswith((";", ".")) and page[nxt].lstrip().startswith(":"):
            row = [(k, "label"), (nxt, "value")]
            i += 2
            if page[nxt].strip() == ":" and k + 2 in body_set and len(page[k + 2].strip()) <= 60 \
                    and not page[k + 2].lstrip().startswith(":"):
                row.append((k + 2, "after_colon"))
                i += 1
            rows.append(row)
        elif nxt is not None and MARKER.match(page[k]) and page[nxt].strip() and not MARKER.match(page[nxt]):
            rows.append([(k, "marker"), (nxt, "item")])
            i += 2
        else:
            rows.append([(k, "text")])
            i += 1
    return rows


def draw_page(c, page, kinds, number, total, doc_label):
    c.setStrokeColor(RULE)
    c.setLineWidth(0.6)
    c.line(MARGIN_L, PAGE_H - 70, PAGE_W - MARGIN_R, PAGE_H - 70)
    c.line(MARGIN_L, 84, PAGE_W - MARGIN_R, 84)
    c.setLineWidth(0.4)
    c.line(MARGIN_L - 22, BODY_BOTTOM - 4, MARGIN_L - 22, BODY_TOP + 10)

    rows = build_rows(page, kinds)
    leading = min(16.0, (BODY_TOP - BODY_BOTTOM) / max(1, len(rows)))
    size = min(11.4, leading * 0.76)
    place = {}
    indent_open = False
    for r, row in enumerate(rows):
        y = BODY_TOP - r * leading
        for k, role in row:
            place[k] = (y, role, indent_open and role == "text")
        last_line = page[row[-1][0]]
        if row[0][1] == "marker":
            indent_open = not PARA_END.search(last_line)
        elif indent_open and PARA_END.search(last_line):
            indent_open = False

    wm_x, wm_y = MARGIN_L - 30, BODY_BOTTOM + 8
    top_y = PAGE_H - 40

    footer_lines = [line for line, k in zip(page, kinds) if k == "footer"]
    footer_y = 72
    footer_step = 62 / max(1, len(footer_lines))

    for index, (line, kind) in enumerate(zip(page, kinds)):
        if kind == "watermark":
            c.saveState()
            c.translate(wm_x, wm_y)
            c.rotate(90)
            draw_line(c, line, 0, 0, "Sans-Bold", 7.5, FAINT)
            c.restoreState()
            wm_x -= 0.01
            wm_y += pdfmetrics.stringWidth(line, "Sans-Bold", 7.5) + 14
        elif kind == "header":
            s = fit_size(line, "Sans-Bold", 8.4, BODY_W)
            w = pdfmetrics.stringWidth(line, "Sans-Bold", s)
            draw_line(c, line, (PAGE_W - w) / 2, PAGE_H - 62, "Sans-Bold", s, MUTED)
        elif kind == "top":
            s = fit_size(line, "Sans", 7.2, BODY_W)
            w = pdfmetrics.stringWidth(line, "Sans", s)
            draw_line(c, line, PAGE_W - MARGIN_R - w, top_y, "Sans", s, MUTED)
            top_y -= 9
        elif kind == "footer":
            is_page_no = re.match(r"^Halaman\s+\d+\s*$", line)
            font = "Sans-Bold" if is_page_no else "Sans"
            s = fit_size(line, font, 7.6 if is_page_no else 6.2, BODY_W)
            w = pdfmetrics.stringWidth(line, font, s)
            x = PAGE_W - MARGIN_R - w if is_page_no else MARGIN_L
            draw_line(c, line, x, footer_y, font, s, INK if is_page_no else MUTED)
            footer_y -= footer_step
        else:
            y, role, indented = place[index]
            stripped = line.strip()
            if role == "text" and CENTER_HEADING.match(line) and len(stripped) < 60:
                font = "Serif-Bold"
                s = fit_size(line, font, size + 0.6, BODY_W)
                w = pdfmetrics.stringWidth(line, font, s)
                draw_line(c, line, (PAGE_W - w) / 2, y, font, s, INK)
                continue
            if role == "label":
                draw_line(c, line, MARGIN_L, y, "Serif", size, INK)
                continue
            if role == "value":
                draw_line(c, line, MARGIN_L + LABEL_TAB, y, "Serif", size, INK)
                continue
            if role == "after_colon":
                draw_line(c, line, MARGIN_L + LABEL_TAB + 10, y, "Serif", size, INK)
                continue
            if role == "marker":
                draw_line(c, line, MARGIN_L + (4 if stripped == "-" else 0), y, "Serif", size, INK)
                continue
            x = MARGIN_L + (MARKER_INDENT if role == "item" or indented else 0)
            width = PAGE_W - MARGIN_R - x
            s = fit_size(line, "Serif", size, width)
            draw_line(c, line, x, y, "Serif", s, INK)


def render(txt_path, pdf_path):
    raw = txt_path.read_bytes().decode("utf-8")
    assert raw.endswith("\r\n"), f"{txt_path.name} does not end with CRLF"
    lines = raw[:-2].split("\r\n")
    pages = split_pages(lines)
    c = canvas.Canvas(str(pdf_path), pagesize=A4, pageCompression=1)
    c.setTitle(f"Putusan {txt_path.stem}")
    c.setAuthor("G04 NLP Demo")
    c.setSubject("Demo document rendered from the course corpus")
    for number, page in enumerate(pages, start=1):
        draw_page(c, page, classify(page), number, len(pages), txt_path.stem)
        c.showPage()
    c.save()
    return raw, len(pages)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--docs", required=True, type=Path)
    parser.add_argument("--out", required=True, type=Path)
    args = parser.parse_args()
    register_fonts()
    args.out.mkdir(parents=True, exist_ok=True)
    report = []
    for txt in sorted(args.docs.glob("doc_*.txt")):
        pdf = args.out / f"{txt.stem}.pdf"
        raw, n_pages = render(txt, pdf)
        back = extract_text(pdf.read_bytes())["text"]
        same = back == raw
        report.append({"doc": txt.stem, "pages": n_pages, "bytes": len(raw.encode()), "round_trip_exact": same})
        if not same:
            a, b = raw.split("\r\n"), back.split("\r\n")
            for i, (x, y) in enumerate(zip(a, b)):
                if x != y:
                    print(f"{txt.stem} first difference at line {i + 1}:\n  txt {x!r}\n  pdf {y!r}")
                    break
            else:
                print(f"{txt.stem} line count differs: txt {len(a)} pdf {len(b)}")
    print(json.dumps(report, indent=2))
    if not all(r["round_trip_exact"] for r in report):
        sys.exit(1)


if __name__ == "__main__":
    main()
