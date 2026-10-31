"""Download and clean the public-domain English translations.

Usage:
    python data/fetch_translations.py                 # every source marked "ok"
    python data/fetch_translations.py --only whinfield_masnavi

Each source is an OCR text file (`*_djvu.txt`) of one scanned edition on the
Internet Archive. Before parsing, the scan's title page is checked for the
expected translator, volume and year, so a reprint or the wrong volume is
refused rather than silently used. Raw downloads go to data/raw/ and cleaned
translation units to data/interim/english/<source>.jsonl, in the row format
data/align.py reads.

Two layouts are handled:
  * paragraphs: Nicholson's Mathnawi prints one couplet per paragraph and
    numbers every fifth verse in the margin. We keep those numbers
    (`translator_verse`) to check the alignment later.
  * lines: Whinfield, Redhouse and Nicholson's Divan print each half-line
    (hemistich) on its own line, so a couplet is about two lines. We keep
    lines as units and let the aligner join two or three of them.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import urllib.request
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from data.sources import SOURCES  # noqa: E402

ARCHIVE = "https://archive.org/download/{id}/{file}"
ROMAN = {"I": 1, "II": 2, "III": 3, "IV": 4, "V": 5, "VI": 6}


@dataclass
class Scan:
    archive_id: str
    file: str
    title_checks: list[str]  # regexes that must all match the first lines (title page)
    layout: str  # "paragraphs" or "lines"
    books: list[int] = field(default_factory=list)  # Masnavi books in this volume, in order
    title_lines: int = 1400


SCANS = {
    "whinfield_masnavi": Scan(
        "masnaviimanavisp00jala_0",
        "masnaviimanavisp00jala_0_djvu.txt",
        [r"WHINFIELD", r"SECOND\s+EDITION", r"\b1898\b", r"TRANSLATED\s+AND\s+ABRIDGED"],
        "lines",
        books=[1, 2, 3, 4, 5, 6],
    ),
    "nicholson_mathnawi_1_2": Scan(
        "in.ernet.dli.2015.70297",
        "2015.70297.Mathnawi-Of-Jalaluddin-Rumi-Vol2_djvu.txt",
        [r"NICHOLSON", r"VOLUME\s+II\b", r"FIRST\s*&\s*SECOND\s+BOOKS", r"\b1926\b"],
        "paragraphs",
        books=[1, 2],
    ),
    "nicholson_mathnawi_3_4": Scan(
        "in.ernet.dli.2015.70298",
        "2015.70298.Mathnawi-Of-Jalaluddin-Rumi-Vol4_djvu.txt",
        # the OCR reads the year on the title page as "I 93°"
        [r"NICHOLSON", r"VOLUME\s+IV\b", r"THIRD\s+\S+\s+FOURTH\s+BOOKS", r"[I1]\s?9\s?3[0°o]"],
        "paragraphs",
        books=[3, 4],
    ),
    "nicholson_divan_1898": Scan(
        "india.history.resource.111025",
        "111025_djvu.txt",
        [r"SELECTED\s+POEMS", r"DIVANI\s+SHAMSI\s+TABRIZ", r"NICH.LSON", r"\b1898\b"],
        "lines",
    ),
    "redhouse_mesnevi_1881": Scan(
        "in.ernet.dli.2015.55252",
        "2015.55252.Mesnevi_djvu.txt",
        # this copy's title page has no date; the preface is signed 1880 and
        # the book appeared in Trubner's Oriental Series in 1881
        [r"MESNEVI", r"BOOK\s+THE\s+FIRST", r"VERSIFIED", r"TR\S*BNER", r"\b1880\b"],
        "lines",
        books=[1],
        title_lines=1800,
    ),
}


# ---------------------------------------------------------------- download


def download(key: str, raw_dir: Path) -> str:
    scan = SCANS[key]
    path = raw_dir / f"{key}.txt"
    if not path.exists():
        raw_dir.mkdir(parents=True, exist_ok=True)
        url = ARCHIVE.format(id=scan.archive_id, file=scan.file)
        print(f"downloading {url}")
        with urllib.request.urlopen(url, timeout=120) as r:
            path.write_bytes(r.read())
    return path.read_text(encoding="utf-8", errors="replace")


def check_title_page(key: str, text: str) -> None:
    scan = SCANS[key]
    head = re.sub(r"[ \t]+", " ", "\n".join(text.splitlines()[: scan.title_lines]))
    missing = [rx for rx in scan.title_checks if not re.search(rx, head, re.I)]
    if missing:
        raise SystemExit(f"{key}: title page of {scan.archive_id} does not match {missing}; wrong edition?")


# ---------------------------------------------------------------- shared cleaning

HEADER = re.compile(
    r"^\W*\d{0,3}\W*(MATHNAW|MASNAVI|MESNEV|THE\s+M\s?A\s?S\s?N\s?A\s?V\s?I|BOOK\s+[IVXL1]+)\S*.{0,40}$", re.I
)
FOOTNOTE = re.compile(r"^\W{0,4}\d?\W{0,3}\s*(Literal\S*|Lit\.|Or\b|i\.\s?e\.|Cf\.|Reading|Var\.|Koran\b|See\b|On the Day)", re.I)
FUNCTION_WORDS = set(
    "the of and to a in is that i my me thou thy thee he his him it its be not for with as by from this was "
    "are all who what when so but if or no on at have hath art will shall o you your we our they their".split()
)


def squash(s: str) -> str:
    return re.sub(r"\s+", " ", s).strip()


def drop_marks(s: str) -> str:
    """Remove stray digits left by footnote marks and marginal verse numbers."""
    s = re.sub(r"(?<=\S)\s+[\di?°]?\d[\d?°]*(?=\s|$)", "", s)
    return re.sub(r"(?<=[a-z,;:.)”’])\d{1,2}\b", "", s)


def join_lines(lines: list[str]) -> str:
    """Join OCR lines, undoing end-of-line hyphenation (separa- / tions)."""
    out = ""
    for ln in lines:
        ln = ln.strip()
        if out.endswith(("-", "¬")) and ln[:1].islower():
            out = out[:-1] + ln
        else:
            out = f"{out} {ln}" if out else ln
    return squash(out)


def is_junk(line: str) -> bool:
    """Page numbers, running heads, and short OCR debris."""
    s = line.strip()
    letters = [c for c in s if c.isalpha()]
    if len(letters) < 4:
        return True
    if HEADER.match(s):
        return True
    upper = sum(c.isupper() for c in letters) / len(letters)
    if upper > 0.8 and len(letters) < 50:  # running heads like THE KING AND THE HANDMAIDEN
        return True
    ascii_share = sum(c.isascii() for c in letters) / len(letters)
    return ascii_share < 0.9  # mangled Persian or Greek


def build_vocab(text: str, min_count: int = 3) -> set[str]:
    """Words seen at least min_count times in the whole scan. Real English
    words recur across hundreds of pages; OCR noise mostly does not."""
    counts = Counter(re.findall(r"[a-z]{3,}", text.lower()))
    return {w for w, c in counts.items() if c >= min_count}


def english_quality(s: str, vocab: set[str] | None = None) -> float:
    """Rough score for "this is English prose", 0 to 1.

    OCR of the facing Persian pages comes out as Latin-letter noise
    ("Galore 9 etl tie slag"), so besides well-formed words we also need a
    normal share of English function words.
    """
    toks = re.findall(r"\S+", s)
    if not toks:
        return 0.0
    good = sum(bool(re.fullmatch(r"[\"“‘'(\[]*[A-Za-z][a-z’'-]*[A-Za-z’']?[)\]\"”’'.,;:!?—-]*", t)) for t in toks)
    words = [re.sub(r"[^a-z]", "", t.lower()) for t in toks]
    func = sum(w in FUNCTION_WORDS for w in words) / len(toks)
    score = good / len(toks)
    if func < 0.12 and len(toks) >= 5:
        score *= func / 0.12
    long = [w for w in words if len(w) >= 3]
    if vocab is not None and long:
        score = min(score, sum(w in vocab for w in long) / len(long))
    return score


# ---------------------------------------------------------------- Nicholson's Mathnawi (paragraphs)

ANCHOR_START = re.compile(r"^\W{0,2}(\d{1,4})\s+(?=[A-Z(“\"‘'’])")
ANCHOR_END = re.compile(r"(?<=\S)\s+(\d{1,4})\s*$")


def paragraphs(text: str) -> list[list[str]]:
    paras, cur = [], []
    for line in text.splitlines():
        if line.strip():
            cur.append(line)
        elif cur:
            paras.append(cur)
            cur = []
    if cur:
        paras.append(cur)
    return paras


def clean_paragraphs(text: str) -> list[dict]:
    """Verse paragraphs with any marginal verse number pulled out."""
    out: list[dict] = []
    for para in paragraphs(text):
        lines = [l for l in para if not is_junk(l)]
        if not lines:
            continue
        first, anchor = lines[0], None
        m = ANCHOR_START.match(first) or ANCHOR_END.search(first)
        if m:
            anchor = int(m.group(1))
            first = first[: m.start()] + first[m.end() :] if m.re is ANCHOR_END else first[m.end() :]
        body = drop_marks(join_lines([first] + lines[1:]))
        if FOOTNOTE.match(body) or english_quality(body) < 0.6:
            continue
        # a verse split by a page break continues in lower case
        if out and anchor is None and body[:1].islower() and not out[-1]["text"].endswith((".", "!", "?", "”", '"')):
            out[-1]["text"] = join_lines([out[-1]["text"], body])
            continue
        out.append({"text": body, "anchor": anchor})
    return out


def anchor_chain(raw: list[tuple[int, int]], n_books: int) -> tuple[list[tuple[int, int]], list[int]]:
    """Longest believable sequence of marginal numbers, with n_books - 1 resets.

    raw holds (paragraph index, number) for every number the OCR found in a
    margin, including stray page numbers and misreads. A step from (i, v) to
    (j, w) is believable when w is a later multiple of 5 and the number of
    paragraphs between them roughly matches w - v; a reset (a new book) goes
    from a high number back to 5 or 10. Dynamic programming keeps the longest
    chain. Returns the chain and the chain positions where each book starts.
    """
    pts = [(i, v) for i, v in raw if v % 5 == 0]
    n = len(pts)
    NEG = -1.0
    best = [[NEG] * n_books for _ in range(n)]  # best[k][r]: longest chain ending at k with r resets
    back: list[list[tuple[int, int] | None]] = [[None] * n_books for _ in range(n)]
    for k, (i, v) in enumerate(pts):
        if v <= 10 and i - (v - 1) >= 0:
            best[k][0] = 1.0
        for q in range(max(0, k - 300), k):
            j, w = pts[q]
            step, gap = v - w, i - j
            for r in range(n_books):
                if best[q][r] == NEG:
                    continue
                if 0 < step <= 150 and abs(gap - step) <= 0.25 * step + 4:
                    nr, gain = r, 1.0
                elif 0 < step <= 300 and 0 < gap <= 3 * step + 100:
                    nr, gain = r, 0.1  # bridge a misordered or duplicated page
                elif v <= 10 and w >= 500 and r + 1 < n_books and gap > 0:
                    nr, gain = r + 1, 1.0
                else:
                    continue
                if best[q][r] + gain > best[k][nr]:
                    best[k][nr], back[k][nr] = best[q][r] + gain, (q, r)
    end = max(range(n), key=lambda k: best[k][n_books - 1])
    if best[end][n_books - 1] == NEG:
        raise SystemExit(f"could not find {n_books} books in the verse numbering")
    chain, cur = [], (end, n_books - 1)
    while cur is not None:
        chain.append(cur)
        cur = back[cur[0]][cur[1]]
    chain.reverse()
    anchors = [pts[k] for k, _ in chain]
    starts = [0] + [m for m in range(1, len(chain)) if chain[m][1] != chain[m - 1][1]]
    return anchors, starts


def number_verses(paras: list[dict], books: list[int]) -> list[dict]:
    """Split a volume into books and number its verses from the marginal anchors.

    Nicholson prints the number of every fifth verse. Anchors restart at 5 when
    a new book begins. Between two anchors n and n+5k there should be exactly 5k
    paragraphs; when that holds, every paragraph gets its verse number. Where it
    does not (a section heading, a footnote or an OCR merge sits in between),
    the paragraphs keep only an estimate, and the aligner sorts it out.
    """
    anchors, book_starts = anchor_chain([(i, p["anchor"]) for i, p in enumerate(paras) if p["anchor"]], len(books))

    rows = []
    for b, book in enumerate(books):
        a = anchors[book_starts[b] : book_starts[b + 1] if b + 1 < len(books) else None]
        start = max(0, a[0][0] - (a[0][1] - 1) - 2)  # slack for a heading before verse 1
        end = min(len(paras), a[-1][0] + 5)
        numbers: dict[int, int] = {}
        for (i0, v0), (i1, v1) in zip(a, a[1:]):
            if i1 - i0 == v1 - v0:
                numbers.update({i0 + k: v0 + k for k in range(v1 - v0)})
        numbers[a[-1][0]] = a[-1][1]
        xs, ys = [i for i, _ in a], [v for _, v in a]
        for i in range(start, end):
            est = round(float(np.interp(i, xs, ys, left=ys[0] - (xs[0] - i), right=ys[-1] + (i - xs[-1]))))
            rows.append(
                {"book": book, "para": i, "text": paras[i]["text"], "translator_verse": numbers.get(i), "verse_est": est}
            )
    return rows


def parse_nicholson_mathnawi(text: str, scan: Scan) -> list[dict]:
    text = re.sub(r"[ \t]+", " ", text)
    rows = number_verses(clean_paragraphs(text), scan.books)
    return [
        {
            "source": "Masnavi",
            "book": r["book"],
            "unit_id": f"p{r['para']}",
            "translator_verse": r["translator_verse"],
            "translator_verse_est": r["verse_est"],
            "english_text": r["text"],
        }
        for r in rows
    ]


# ---------------------------------------------------------------- line layouts


def verse_lines(lines: list[str], vocab: set[str] | None = None) -> list[str]:
    """Keep verse lines; drop running heads, page numbers and footnote blocks."""
    out, in_note = [], False
    prev_blank = True
    for raw in lines:
        s = squash(raw)
        if not s:
            prev_blank = True
            continue
        if is_junk(s):
            in_note = False  # a running head or page number ends a footnote block
            prev_blank = False
            continue
        # footnotes start after a gap with a reference mark: "1 Love signifies ..."
        if prev_blank and re.match(r"^[1-9¹²³*†]\s+[A-Z“\"]", s) and not re.match(r"^1\s+(too|am|have|was|will|see|know)\b", s):
            in_note = True
        prev_blank = False
        if in_note or english_quality(s, vocab) < 0.6 or FOOTNOTE.match(s):
            continue
        s = re.sub(r"^1\s+(?=[a-z])", "I ", s)  # OCR reads the pronoun I as 1
        s = re.sub(r"^0\s+(?=[A-Za-z])", "O ", s)  # and the vocative O as 0
        s = drop_marks(s)
        # wrapped continuation of a long line starts in lower case
        if out and s[:1].islower() and not out[-1].endswith((".", "!", "?", ";")):
            out[-1] = join_lines([out[-1], s])
        else:
            out.append(s)
    return out


def book_spans(lines: list[str], books: list[int], body_start: int) -> dict[int, tuple[int, int]]:
    """Book boundaries from running heads like '[book ii.' or 'BOOK II.]'."""
    first_seen: dict[int, int] = {}
    for i, ln in enumerate(lines[body_start:], start=body_start):
        m = re.match(r"^\W*book\s+([ivx]{1,3})\W*$", ln.strip(), re.I)
        if m and (n := ROMAN.get(m.group(1).upper())) in books and n not in first_seen:
            if not first_seen or n > max(first_seen):
                first_seen[n] = i
    starts = [body_start] + [max(first_seen[b] - 60, body_start) for b in books[1:]]
    ends = starts[1:] + [len(lines)]
    return {b: (s, e) for b, s, e in zip(books, starts, ends)}


def parse_whinfield(text: str, scan: Scan) -> list[dict]:
    lines = text.splitlines()
    body = next(i for i, l in enumerate(lines) if re.match(r"^\s*PROLOGUE\.\s*$", l) and i > 1000)
    vocab = build_vocab(text)
    rows = []
    for book, (s, e) in book_spans(lines, scan.books, body).items():
        for k, ln in enumerate(verse_lines(lines[s:e], vocab)):
            rows.append({"source": "Masnavi", "book": book, "unit_id": f"b{book}l{k}", "english_text": ln})
    return rows


def parse_redhouse(text: str, scan: Scan) -> list[dict]:
    lines = text.splitlines()
    start = next(i for i, l in enumerate(lines) if re.match(r"^\s*From reed-flute", l) and i > 8000)
    end = max(i for i, l in enumerate(lines) if re.match(r"^\s*THE END\.", l))
    return [
        {"source": "Masnavi", "book": 1, "unit_id": f"b1l{k}", "english_text": ln}
        for k, ln in enumerate(verse_lines(lines[start:end], build_vocab(text)))
    ]


def parse_nicholson_divan(text: str, scan: Scan) -> list[dict]:
    """Poems I-XLVIII sit between the introduction and the notes; each English
    page faces a page of (unusable) Persian OCR, which verse_lines drops."""
    lines = text.splitlines()
    numeral = re.compile(r"^\s*([XLVI]{1,7}L?)\.\s*$")
    heads = [i for i, l in enumerate(lines) if numeral.match(l)]
    start = heads[0]
    notes = next(i for i in heads if i > start + 1000 and numeral.match(lines[i]).group(1) == "I")
    vocab = build_vocab(text)
    rows, poem, k = [], 0, 0
    for i in range(start, notes):
        if numeral.match(lines[i]):
            poem, k = poem + 1, 0  # OCR misses a few headings, so this is only a guide
            continue
        for ln in verse_lines([lines[i]], vocab):
            rows.append(
                {"source": "Divan", "book": None, "unit_id": f"n{poem}l{k}", "nicholson_poem_guess": poem, "english_text": ln}
            )
            k += 1
    # re-run continuation joining across the line-by-line pass
    merged: list[dict] = []
    for r in rows:
        t = r["english_text"]
        if merged and t[:1].islower() and not merged[-1]["english_text"].endswith((".", "!", "?", ";")):
            merged[-1]["english_text"] = join_lines([merged[-1]["english_text"], t])
        else:
            merged.append(r)
    return merged


PARSERS = {
    "whinfield_masnavi": parse_whinfield,
    "nicholson_mathnawi_1_2": parse_nicholson_mathnawi,
    "nicholson_mathnawi_3_4": parse_nicholson_mathnawi,
    "nicholson_divan_1898": parse_nicholson_divan,
    "redhouse_mesnevi_1881": parse_redhouse,
}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", nargs="*", help="source keys (default: every source marked ok)")
    ap.add_argument("--raw-dir", type=Path, default=Path("data/raw"))
    ap.add_argument("--out-dir", type=Path, default=Path("data/interim/english"))
    args = ap.parse_args()

    keys = args.only or [k for k in SCANS if SOURCES[k]["status"] == "ok"]
    args.out_dir.mkdir(parents=True, exist_ok=True)
    for key in keys:
        src = SOURCES[key]
        if src["status"] != "ok":
            raise SystemExit(f"{key} is marked {src['status']!r} in sources.py; not downloading")
        scan = SCANS[key]
        text = download(key, args.raw_dir)
        check_title_page(key, text)
        rows = PARSERS[key](text, scan)
        with (args.out_dir / f"{key}.jsonl").open("w", encoding="utf-8") as f:
            for r in rows:
                r.update(
                    translator=src["translator"],
                    license_note=src["license_note"],
                    edition=f"{src['what']} (archive.org/details/{scan.archive_id})",
                    layout=scan.layout,
                )
                f.write(json.dumps(r, ensure_ascii=False) + "\n")
        print(f"{key}: {len(rows)} {scan.layout[:-1]} units")


if __name__ == "__main__":
    main()
