"""Extract the league rulebook from the league's .docx, verbatim.

The league publishes one Word document and calls it the only accepted version.
This turns it into plain text so it can be read, searched, diffed against next
season's release, and rendered as a page — without anybody retyping it.

    python generator/extract_rulebook.py rulebook/<the>.docx rulebook/<the>.txt

The output is the document's text and nothing else: no reflowing, no spelling
fixes, no tidying of the league's spacing. The rulebook contains real typos
("safetyoriented", "BENIND", "ATTEMP") and they are reproduced as written,
because the point of this file is to be quotable.

Two things are not literal characters in the .docx and are still reproduced,
because Word puts them on the page and coaches read them as part of the text:

  * List markers. Some rule numbers exist only as Word auto-numbering — "8.01"
    and "10.01" are generated from numbering.xml, not typed. They are resolved
    here the same way Word resolves them.
  * Symbol-font bullets. U+F0B7 in the Symbol font is the round bullet the
    reader sees, so it is written out as "•".

Verified against Microsoft Word's own object model: with all whitespace
removed, this output and Word's rendering of the document are the same string,
except for the anchor placeholders Word emits for the seven floating images
(which are not text). See rulebook/README.md.
"""

import sys
import zipfile
import xml.etree.ElementTree as ET
from pathlib import Path

W = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"

# Symbol/Wingdings code points used as list bullets, and the character each one
# actually draws on the page.
SYMBOL_BULLETS = {
    "": "•",
    "": "▪",
    "": "➢",
    "": "✔",
    "": "▪",
    "o": "o",
}


class Numbering:
    """Word's numbering.xml, far enough to rebuild the markers it draws."""

    def __init__(self, xml: bytes | None):
        self.abstract: dict[str, dict[int, dict]] = {}
        self.numid: dict[str, tuple[str | None, dict[int, int]]] = {}
        self.counters: dict[tuple[str, int], int] = {}
        if xml is None:
            return
        root = ET.fromstring(xml)
        for a in root.findall(W + "abstractNum"):
            levels = {}
            for lvl in a.findall(W + "lvl"):
                fmt = lvl.find(W + "numFmt")
                text = lvl.find(W + "lvlText")
                start = lvl.find(W + "start")
                levels[int(lvl.get(W + "ilvl"))] = {
                    "fmt": fmt.get(W + "val") if fmt is not None else "decimal",
                    "text": text.get(W + "val") if text is not None else "",
                    "start": int(start.get(W + "val")) if start is not None else 1,
                }
            self.abstract[a.get(W + "abstractNumId")] = levels
        for n in root.findall(W + "num"):
            abstract = n.find(W + "abstractNumId")
            overrides = {}
            for override in n.findall(W + "lvlOverride"):
                start = override.find(W + "startOverride")
                if start is not None:
                    overrides[int(override.get(W + "ilvl"))] = int(start.get(W + "val"))
            self.numid[n.get(W + "numId")] = (
                abstract.get(W + "val") if abstract is not None else None,
                overrides,
            )

    def _level(self, num_id: str, ilvl: int) -> dict | None:
        abstract, _ = self.numid.get(num_id, (None, {}))
        return self.abstract.get(abstract, {}).get(ilvl)

    def _start(self, num_id: str, ilvl: int) -> int:
        _, overrides = self.numid.get(num_id, (None, {}))
        if ilvl in overrides:
            return overrides[ilvl]
        level = self._level(num_id, ilvl)
        return level["start"] if level else 1

    @staticmethod
    def _format(value: int, fmt: str) -> str:
        if fmt == "decimalZero":
            return f"{value:02d}"
        if fmt in ("lowerLetter", "upperLetter"):
            # Word wraps past z as aa, bb, cc — not as ab, ac.
            n = value - 1
            letters = chr(ord("a") + n % 26) * (n // 26 + 1)
            return letters if fmt == "lowerLetter" else letters.upper()
        if fmt in ("lowerRoman", "upperRoman"):
            numerals = [(1000, "m"), (900, "cm"), (500, "d"), (400, "cd"),
                        (100, "c"), (90, "xc"), (50, "l"), (40, "xl"),
                        (10, "x"), (9, "ix"), (5, "v"), (4, "iv"), (1, "i")]
            out, left = "", value
            for amount, symbol in numerals:
                while left >= amount:
                    out += symbol
                    left -= amount
            return out if fmt == "lowerRoman" else out.upper()
        return str(value)

    def marker(self, num_id: str, ilvl: int) -> str:
        """Advance this list one item and return the marker Word would draw."""
        level = self._level(num_id, ilvl)
        if level is None:
            return ""
        if level["fmt"] == "bullet":
            return SYMBOL_BULLETS.get(level["text"], level["text"])

        key = (num_id, ilvl)
        self.counters[key] = self.counters.get(key, self._start(num_id, ilvl) - 1) + 1
        # Starting an item at this level restarts every level below it.
        for other in [k for k in self.counters if k[0] == num_id and k[1] > ilvl]:
            del self.counters[other]

        out = level["text"]
        for depth in range(9):
            token = f"%{depth + 1}"
            if token not in out:
                continue
            # A level nobody has reached yet sits at its start value, which is
            # how "10.01" gets its 10 without a level-0 item ever appearing.
            value = self.counters.get((num_id, depth), self._start(num_id, depth))
            above = self._level(num_id, depth)
            out = out.replace(token, self._format(value, above["fmt"] if above else "decimal"))
        return out


def run_text(node: ET.Element) -> str:
    """Every character a run puts on the page, in order."""
    out = []
    for n in node.iter():
        if n.tag == W + "t":
            out.append(n.text or "")
        elif n.tag == W + "tab":
            out.append("\t")
        elif n.tag in (W + "br", W + "cr"):
            out.append("\n")
        elif n.tag == W + "noBreakHyphen":
            out.append("-")
        elif n.tag == W + "sym":
            char = n.get(W + "char")
            if char:
                out.append(SYMBOL_BULLETS.get(chr(int(char, 16)), chr(int(char, 16))))
    return "".join(out)


RUN_LIKE = (W + "r", W + "ins", W + "smartTag", W + "hyperlink", W + "sdt")


def paragraph_text(p: ET.Element, numbering: Numbering) -> str:
    marker = ""
    num_pr = p.find(W + "pPr/" + W + "numPr")
    if num_pr is not None:
        num_id = num_pr.find(W + "numId")
        ilvl = num_pr.find(W + "ilvl")
        # numId 0 is Word's way of saying "this paragraph is not in a list".
        if num_id is not None and num_id.get(W + "val") != "0":
            marker = numbering.marker(
                num_id.get(W + "val"),
                int(ilvl.get(W + "val")) if ilvl is not None else 0,
            )
    body = "".join(run_text(child) for child in p if child.tag in RUN_LIKE)
    if marker:
        return f"{marker}\t{body}" if body else marker
    return body


def walk(container: ET.Element, numbering: Numbering, out: list[str]) -> None:
    for child in container:
        if child.tag == W + "p":
            out.append(paragraph_text(child, numbering))
        elif child.tag == W + "tbl":
            rows = child.findall(W + "tr")
            # A table where every row is one cell is page layout, not data —
            # the cover page is built that way. Unwrap it.
            layout = all(len(r.findall(W + "tc")) == 1 for r in rows)
            for row in rows:
                cells = []
                for cell in row.findall(W + "tc"):
                    inner: list[str] = []
                    walk(cell, numbering, inner)
                    if layout:
                        out.extend(inner)
                    else:
                        cells.append(" ".join(x.strip() for x in inner if x.strip()))
                if not layout:
                    out.append("\t".join(cells))
        elif child.tag == W + "sdt":
            content = child.find(W + "sdtContent")
            if content is not None:
                walk(content, numbering, out)


def extract(docx: Path) -> str:
    archive = zipfile.ZipFile(docx)
    document = ET.fromstring(archive.read("word/document.xml"))
    try:
        numbering = Numbering(archive.read("word/numbering.xml"))
    except KeyError:
        numbering = Numbering(None)
    lines: list[str] = []
    walk(document.find(W + "body"), numbering, lines)
    return "\n".join(lines).rstrip("\n") + "\n"


def extract_media(docx: Path, dest: Path) -> list[str]:
    """Save the document's images beside the text so nothing is left behind."""
    archive = zipfile.ZipFile(docx)
    names = sorted(n for n in archive.namelist() if n.startswith("word/media/"))
    written = []
    if names:
        dest.mkdir(parents=True, exist_ok=True)
    for name in names:
        target = dest / Path(name).name
        target.write_bytes(archive.read(name))
        written.append(target.name)
    return written


def main(argv: list[str]) -> int:
    if len(argv) != 3:
        print(__doc__.strip().split("\n\n")[2].strip(), file=sys.stderr)
        return 2
    docx, out = Path(argv[1]), Path(argv[2])
    text = extract(docx)
    out.write_text(text, encoding="utf-8", newline="\n")
    media = extract_media(docx, out.parent / "media")
    print(f"{out}: {len(text.splitlines())} lines, {len(text)} characters")
    if media:
        print(f"{out.parent / 'media'}: {len(media)} images")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
