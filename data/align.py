"""Align English translation units to Persian couplets.

Translations do not follow Ganjoor's verse numbering exactly (Ganjoor's Masnavi
Book 1 has 4,013 couplets, Nicholson's edition 4,003), and Whinfield's abridged
version skips and merges verses. So we align by meaning, not by number: embed
both sides with a multilingual sentence encoder (LaBSE by default) and find the
best monotonic path with dynamic programming, allowing 1:1, 1:2, 2:1 and skips
(the vecalign / Gale-Church idea).

Usage:
    python data/align.py --persian data/interim/persian.jsonl \
        --english data/interim/english/nicholson_mathnawi.jsonl \
        --out data/interim/aligned/nicholson_mathnawi.jsonl

English input rows: {"source", "book", "poem_number" (optional), "unit_id",
"verse_start", "verse_end" (translator's own numbering, optional), "english_text",
"translator", "license_note"}.
"""

from __future__ import annotations

import argparse
import json
from collections import defaultdict
from pathlib import Path
from typing import Callable, Sequence

import numpy as np

SKIP_PENALTY = 0.3  # cost of leaving a Persian couplet or English unit unaligned
MERGE_PENALTY = 0.1  # small cost so merges only win when clearly better
MIN_SIM = 0.35  # aligned pairs below this similarity are dropped from the output


def monotonic_align(
    sim: np.ndarray,
    merge_sim: Callable[[str, int, int], float] | None = None,
    band: int | None = None,
):
    """Best monotonic alignment over a Persian x English similarity matrix.

    Returns a list of (persian_indices, english_indices) beads. Moves:
    1:1, 2:1 (two couplets -> one English unit), 1:2, and skips on either side.
    band limits the search to cells within that distance of the diagonal,
    which keeps a whole Masnavi book (~4,000 x 4,000) tractable.
    merge_sim(kind, i, j) can give a better score for merged beads; by default
    a merged bead scores its weakest pairwise similarity, so both halves must
    match the other side for a merge to beat a 1:1 plus a skip.
    """
    n, m = sim.shape
    score = np.full((n + 1, m + 1), -np.inf)
    back: dict[tuple[int, int], tuple[int, int]] = {}
    score[0, 0] = 0.0
    moves = [(1, 1), (2, 1), (1, 2), (1, 0), (0, 1)]
    for i in range(n + 1):
        for j in range(m + 1):
            if i == 0 and j == 0:
                continue
            if band is not None and abs(j - i * m / max(n, 1)) > band:
                continue
            best, arg = -np.inf, None
            for di, dj in moves:
                pi, pj = i - di, j - dj
                if pi < 0 or pj < 0 or score[pi, pj] == -np.inf:
                    continue
                if di == 0 or dj == 0:
                    gain = -SKIP_PENALTY
                elif (di, dj) == (1, 1):
                    gain = sim[pi, pj]
                else:
                    block = sim[pi:i, pj:j]
                    s = merge_sim(f"{di}:{dj}", pi, pj) if merge_sim else block.min()
                    gain = 2 * s - MERGE_PENALTY
                if score[pi, pj] + gain > best:
                    best, arg = score[pi, pj] + gain, (pi, pj)
            score[i, j], back[(i, j)] = best, arg
    beads, cur = [], (n, m)
    while cur != (0, 0):
        prev = back[cur]
        p, e = list(range(prev[0], cur[0])), list(range(prev[1], cur[1]))
        if p and e:
            beads.append((p, e))
        cur = prev
    return beads[::-1]


def embed_labse(texts: Sequence[str]) -> np.ndarray:
    from sentence_transformers import SentenceTransformer

    model = SentenceTransformer("sentence-transformers/LaBSE")
    return model.encode(list(texts), batch_size=64, normalize_embeddings=True, show_progress_bar=True)


def align_group(persian: list[dict], english: list[dict], embed) -> list[dict]:
    p_emb = embed([r["persian_text"].replace(" / ", " ") for r in persian])
    e_emb = embed([r["english_text"] for r in english])
    sim = p_emb @ e_emb.T
    out = []
    band = 200 if max(sim.shape) > 400 else None
    for p_idx, e_idx in monotonic_align(sim, band=band):
        s = float(sim[np.ix_(p_idx, e_idx)].mean())
        if s < MIN_SIM:
            continue
        base = dict(persian[p_idx[0]])
        if len(p_idx) > 1:  # two couplets share one English unit
            base["persian_text"] = " // ".join(persian[i]["persian_text"] for i in p_idx)
            base["verse_end"] = persian[p_idx[-1]]["verse_number"]
        eng = english[e_idx[0]]
        base.update(
            english_text=" ".join(english[j]["english_text"] for j in e_idx),
            translator=eng["translator"],
            license_note=eng["license_note"],
            align_score=round(s, 4),
            align_type=f"{len(p_idx)}:{len(e_idx)}",
        )
        out.append(base)
    return out


def group_key(row: dict) -> tuple:
    # Masnavi: align a whole book at once; Divan: one ghazal at a time.
    return (row["source"], row.get("book")) if row["source"] == "Masnavi" else (row["source"], row["poem_number"])


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--persian", type=Path, required=True)
    ap.add_argument("--english", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    args = ap.parse_args()

    persian, english = defaultdict(list), defaultdict(list)
    for line in args.persian.open(encoding="utf-8"):
        r = json.loads(line)
        persian[group_key(r)].append(r)
    for line in args.english.open(encoding="utf-8"):
        r = json.loads(line)
        english[group_key(r)].append(r)

    args.out.parent.mkdir(parents=True, exist_ok=True)
    n = 0
    with args.out.open("w", encoding="utf-8") as f:
        for key, eng_rows in english.items():
            for row in align_group(persian[key], eng_rows, embed_labse):
                f.write(json.dumps(row, ensure_ascii=False) + "\n")
                n += 1
    print(f"wrote {n} aligned rows to {args.out}")


if __name__ == "__main__":
    main()
