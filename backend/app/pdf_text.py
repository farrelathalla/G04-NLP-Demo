"""PDF to text extraction.

The reader walks the content stream of every page with pypdf. Each text object
(BT ... ET) becomes one line, in the order it was drawn. Glyph codes are mapped back to
characters through the ToUnicode table of the font, so spacing inside a line is kept
exactly. Lines are joined with CRLF, the line ending of the source corpus.
"""
import re
from io import BytesIO

from pypdf import PdfReader
from pypdf.generic import ContentStream, TextStringObject, ByteStringObject

_HEX = re.compile(rb"<([0-9A-Fa-f]+)>")


def _hex_to_text(h):
    data = bytes.fromhex(h.decode())
    return data.decode("utf-16-be", errors="replace")


def _parse_cmap(data):
    """Parse the bfchar and bfrange blocks of a ToUnicode CMap."""
    mapping, width = {}, 1
    space = re.search(rb"begincodespacerange\s*<([0-9A-Fa-f]+)>", data)
    if space:
        width = len(space.group(1)) // 2
    for block in re.findall(rb"beginbfchar(.*?)endbfchar", data, re.S):
        pairs = _HEX.findall(block)
        for src, dst in zip(pairs[::2], pairs[1::2]):
            mapping[int(src, 16)] = _hex_to_text(dst)
    for block in re.findall(rb"beginbfrange(.*?)endbfrange", data, re.S):
        for line in block.strip().splitlines():
            parts = re.findall(rb"<[0-9A-Fa-f]+>|\[[^\]]*\]", line)
            if len(parts) < 3:
                continue
            lo, hi = int(parts[0][1:-1], 16), int(parts[1][1:-1], 16)
            if parts[2].startswith(b"["):
                for offset, dst in enumerate(_HEX.findall(parts[2])):
                    mapping[lo + offset] = _hex_to_text(dst)
            else:
                start = bytes.fromhex(parts[2][1:-1].decode())
                base = int.from_bytes(start, "big")
                for code in range(lo, hi + 1):
                    value = (base + code - lo).to_bytes(len(start), "big")
                    mapping[code] = value.decode("utf-16-be", errors="replace")
    return mapping, width


class _Font:
    def __init__(self, font_obj):
        font_obj = font_obj.get_object()
        self.map, self.width = {}, 1
        if "/ToUnicode" in font_obj:
            self.map, self.width = _parse_cmap(font_obj["/ToUnicode"].get_object().get_data())

    def decode(self, raw):
        if isinstance(raw, TextStringObject):
            raw = raw.get_original_bytes()
        elif not isinstance(raw, (bytes, ByteStringObject)):
            raw = bytes(raw)
        raw = bytes(raw)
        if not self.map:
            return raw.decode("latin-1")
        out = []
        for i in range(0, len(raw), self.width):
            code = int.from_bytes(raw[i:i + self.width], "big")
            out.append(self.map.get(code, chr(code)))
        return "".join(out)


def _page_lines(page, reader):
    resources = page.get("/Resources", {})
    resources = resources.get_object() if hasattr(resources, "get_object") else resources
    font_dict = resources.get("/Font", {})
    font_dict = font_dict.get_object() if hasattr(font_dict, "get_object") else font_dict
    fonts = {name: _Font(obj) for name, obj in font_dict.items()}

    content = ContentStream(page.get_contents(), reader)
    lines, current, font, positioned = [], None, None, False
    for operands, op in content.operations:
        if op == b"BT":
            current, positioned = [], False
        elif op == b"ET":
            # A setup block with no position and no text is not a line of the document.
            if current is not None and (positioned or current):
                lines.append("".join(current))
            current = None
        elif op in (b"Tm", b"Td", b"TD"):
            positioned = True
        elif op == b"Tf":
            font = fonts.get(operands[0])
        elif current is not None and font is not None:
            if op in (b"Tj", b"'", b'"'):
                current.append(font.decode(operands[-1]))
            elif op == b"TJ":
                current.extend(font.decode(item) for item in operands[0] if not isinstance(item, (int, float)) and not hasattr(item, "as_numeric"))
    return lines


def extract_text(pdf_bytes):
    reader = PdfReader(BytesIO(pdf_bytes))
    pages = [_page_lines(page, reader) for page in reader.pages]
    lines = [line for page in pages for line in page]
    text = "\r\n".join(lines) + "\r\n" if lines else ""
    metadata = reader.metadata or {}
    return {
        "text": text,
        "pages": len(reader.pages),
        "lines_per_page": [len(p) for p in pages],
        "title": metadata.get("/Title"),
    }
