"""Extract Rumi's Persian couplets from a local clone of ganjoor/ganjoor-data.

Usage:
    git clone --depth 1 https://github.com/ganjoor/ganjoor-data /tmp/ganjoor-data
    python data/extract_ganjoor.py --ganjoor /tmp/ganjoor-data --out data/interim/persian.jsonl

One output row per bayt (couplet). Only the verse text and the metre label are
kept; Ganjoor's editorial extras (AI summaries, couplet glosses, literary tags)
are dropped.
"""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

PERSIAN_DIGITS = str.maketrans("۰۱۲۳۴۵۶۷۸۹", "0123456789")
SLUG_NUM = re.compile(r"sh(\d+)$")

# (source label, category path under poets/moulavi, book number or None)
COLLECTIONS = [("Masnavi", f"masnavi/daftar{i}", i) for i in range(1, 7)] + [
    ("Divan", "shams/ghazalsh", None),
]


def poem_paths(cat_dir: Path) -> list[Path]:
    """Poem files in the order Ganjoor lists them in the category's _cat.json."""
    cat = json.loads((cat_dir / "_cat.json").read_text(encoding="utf-8"))
    return [cat_dir / (p["FullUrl"].rsplit("/", 1)[1] + ".json") for p in cat["Poems"]]


def couplets(poem: dict) -> list[tuple[str, str]]:
    """Group Right/Left hemistichs into couplets by CoupletIndex."""
    by_idx: dict[int, dict[str, str]] = {}
    for v in sorted(poem.get("Verses", []), key=lambda v: v["VOrder"]):
        idx = v.get("CoupletIndex")
        if idx is None or v.get("Position") not in ("Right", "Left"):
            continue  # skip prose lines, headings, single-line paragraphs
        by_idx.setdefault(idx, {})[v["Position"]] = v["Text"].strip()
    return [(h["Right"], h["Left"]) for _, h in sorted(by_idx.items()) if "Right" in h and "Left" in h]


def extract(root: Path):
    base = root / "poets" / "moulavi"
    for source, rel, book in COLLECTIONS:
        verse_in_book = 0  # Masnavi verses are numbered continuously within each daftar
        for path in poem_paths(base / rel):
            poem = json.loads(path.read_text(encoding="utf-8"))
            poem_number = int(SLUG_NUM.search(path.stem).group(1))
            metre = (poem.get("Metre") or {}).get("Rhythm", "")
            for i, (h1, h2) in enumerate(couplets(poem), start=1):
                verse_in_book += 1
                yield {
                    "id": f"{source.lower()}-{book or 'g'}-{poem_number}-{i}",
                    "source": source,
                    "book": book,
                    "poem_number": poem_number,
                    "poem_title": poem.get("Title", "").translate(PERSIAN_DIGITS),
                    "verse_number": verse_in_book if source == "Masnavi" else i,
                    "verse_in_poem": i,
                    "hemistich_1": h1,
                    "hemistich_2": h2,
                    "persian_text": f"{h1} / {h2}",
                    "meter_name": metre,
                    "ganjoor_url": "https://ganjoor.net" + poem["FullUrl"],
                }


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--ganjoor", type=Path, required=True, help="path to a ganjoor-data clone")
    ap.add_argument("--out", type=Path, default=Path("data/interim/persian.jsonl"))
    args = ap.parse_args()
    args.out.parent.mkdir(parents=True, exist_ok=True)
    n = 0
    with args.out.open("w", encoding="utf-8") as f:
        for row in extract(args.ganjoor):
            f.write(json.dumps(row, ensure_ascii=False) + "\n")
            n += 1
    print(f"wrote {n} couplets to {args.out}")


if __name__ == "__main__":
    main()
