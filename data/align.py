"""Align English translation units to Persian couplets.

Translations do not follow Ganjoor's verse numbering exactly (Ganjoor's Masnavi
Book 1 has 4,013 couplets, Nicholson's edition 4,003), and Whinfield's abridged
version skips and merges verses. So we align by meaning, not by number: embed
both sides with a multilingual sentence encoder (LaBSE) and find the best
monotonic path with dynamic programming, allowing 1:1, 2:1, 1:2, 1:3 and skips
(the vecalign / Gale-Church idea).

Two English layouts come out of fetch_translations.py:
  * paragraphs (Nicholson's Mathnawi): one unit is one couplet.
  * lines (Whinfield, Redhouse, Nicholson's Divan): one unit is a half-line, so
    a couplet is usually two units. Joined pairs and triples of lines are
    embedded too, so a 1:2 bead is scored on the joined English text.

The Divan translation is a selection of 48 ghazals whose numbering does not
match Ganjoor, so we first find which Ganjoor ghazals it contains (each pair of
English lines votes for its nearest Persian couplet) and then align against
those ghazals in order.

Usage:
    python data/align.py --persian data/interim/persian.jsonl \
        --english data/interim/english/nicholson_mathnawi_1_2.jsonl \
        --out data/interim/aligned/nicholson_mathnawi_1_2.jsonl
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

BIAS = 0.3  # LaBSE similarity an unrelated Persian/English pair typically reaches; a match must beat it
SKIP_PENALTY = 0.05  # cost of leaving a Persian couplet or English unit unaligned
MERGE_PENALTY = 0.05  # small cost so merges only win when clearly better
MIN_SIM = 0.45  # beads at or above this similarity are kept on their own
CONTEXT_MIN_SIM = 0.25  # weaker beads are kept only when confident neighbours sit right next to them

HALF_LINE_CHARS = 60  # in line layouts, a lone line shorter than this is one hemistich

PARAGRAPH_MOVES = [(1, 1), (2, 1), (1, 2)]
LINE_MOVES = [(1, 1), (1, 2), (1, 3), (2, 1)]


def monotonic_align(
    sim: np.ndarray,
    merge_sims: dict[tuple[int, int], np.ndarray] | None = None,
    moves: list[tuple[int, int]] | None = None,
    band: int | None = None,
):
    """Best monotonic alignment over a Persian x English similarity matrix.

    Returns a list of (persian_indices, english_indices) beads. A bead that
    covers di couplets and dj English units with similarity s gains
    max(di, dj) * (s - BIAS); skipping a unit on either side costs SKIP_PENALTY.
    merge_sims[(di, dj)][i, j] can give the similarity of the merged bead
    starting at (i, j), e.g. Persian couplet i against English lines j and j+1
    joined. Without it a merged bead scores its weakest pairwise similarity.
    band limits the search to cells within that distance of the diagonal.

    The table is filled one Persian row at a time with numpy: every move that
    comes from an earlier row is a vector operation, and the English-skip move
    within a row is a running maximum.
    """
    moves = moves or PARAGRAPH_MOVES
    merge_sims = merge_sims or {}
    n, m = sim.shape
    NEG = -1e18
    score = np.full((n + 1, m + 1), NEG)
    came = np.full((n + 1, m + 1), -1, dtype=np.int8)  # move index, len(moves) = Persian skip
    row_from = np.zeros((n + 1, m + 1), dtype=np.int32)  # English skips: column the run started from
    cols = np.arange(m + 1)
    allowed = np.ones((n + 1, m + 1), dtype=bool)
    if band is not None:
        diag = np.arange(n + 1)[:, None] * m / max(n, 1)
        allowed = np.abs(cols[None, :] - diag) <= band

    def bead_gain(i: int, di: int, dj: int) -> np.ndarray:
        """Gain of the move (di, dj) into every cell of row i (index j = end column)."""
        g = np.full(m + 1, NEG)
        if dj > m:
            return g
        pi = i - di
        if (di, dj) in merge_sims:
            s = merge_sims[(di, dj)][pi, : m - dj + 1]
        else:
            s = np.min([sim[pi + a, k : m - dj + 1 + k] for a in range(di) for k in range(dj)], axis=0)
        g[dj:] = max(di, dj) * (s - BIAS) - (MERGE_PENALTY if (di, dj) != (1, 1) else 0.0)
        return g

    for i in range(n + 1):
        cand = np.full(m + 1, NEG)
        move = np.full(m + 1, -1, dtype=np.int8)
        if i == 0:
            cand[0] = 0.0
        else:
            for k, (di, dj) in enumerate(moves):
                if di > i:
                    continue
                prev = np.full(m + 1, NEG)
                prev[dj:] = score[i - di, : m + 1 - dj]
                c = prev + bead_gain(i, di, dj)
                better = c > cand
                cand[better], move[better] = c[better], k
            c = score[i - 1] - SKIP_PENALTY  # Persian couplet left untranslated
            better = c > cand
            cand[better], move[better] = c[better], len(moves)
        cand[~allowed[i]] = NEG
        # English skips along the row: score[j] = max_k (cand[k] - SKIP_PENALTY * (j - k))
        t = cand + SKIP_PENALTY * cols
        run = np.maximum.accumulate(t)
        start = np.maximum.accumulate(np.where(t >= run, cols, 0))
        score[i] = np.where(allowed[i], run - SKIP_PENALTY * cols, NEG)
        came[i], row_from[i] = move, start

    beads, i, j = [], n, m
    while i > 0 or j > 0:
        j0 = row_from[i, j]  # English units j0..j-1 were skipped
        j = j0
        if i == 0:
            break
        k = came[i, j]
        if k == len(moves):
            i -= 1
            continue
        di, dj = moves[k]
        beads.append((list(range(i - di, i)), list(range(j - dj, j))))
        i, j = i - di, j - dj
    return beads[::-1]


def joined_sims(p_emb: np.ndarray, english: list[dict], embed, sizes=(2, 3)) -> dict[tuple[int, int], np.ndarray]:
    """Similarity of each couplet to runs of 2 or 3 consecutive English lines."""
    out = {}
    texts = [r["english_text"] for r in english]
    for k in sizes:
        if len(texts) < k:
            continue
        runs = [" ".join(texts[j : j + k]) for j in range(len(texts) - k + 1)]
        out[(1, k)] = p_emb @ embed(runs).T
    return out


def persian_text(row: dict) -> str:
    return row["persian_text"].replace(" / ", " ")


def align_group(persian: list[dict], english: list[dict], embed, layout: str) -> list[dict]:
    p_emb = embed([persian_text(r) for r in persian])
    e_emb = embed([r["english_text"] for r in english])
    sim = p_emb @ e_emb.T
    if layout == "lines":
        merge, moves = joined_sims(p_emb, english, embed), LINE_MOVES
    else:
        merge, moves = {}, PARAGRAPH_MOVES
    band = None if layout == "lines" or max(sim.shape) < 400 else 300
    beads = monotonic_align(sim, merge, moves, band)
    scores = []
    for p_idx, e_idx in beads:
        key = (len(p_idx), len(e_idx))
        if key in merge:
            scores.append(float(merge[key][p_idx[0], e_idx[0]]))
        else:
            scores.append(float(sim[np.ix_(p_idx, e_idx)].mean()))
    keep = keep_beads(beads, scores, max_gap=(2, 4 if layout == "lines" else 2))
    out = []
    for (p_idx, e_idx), s, k in zip(beads, scores, keep):
        if not k:
            continue
        if layout == "lines" and len(e_idx) == 1 and len(english[e_idx[0]]["english_text"]) < HALF_LINE_CHARS:
            continue  # a single short line is only half a couplet; the spot-check found these incomplete
        base = dict(persian[p_idx[0]])
        if len(p_idx) > 1:  # two couplets share one English unit
            base["persian_text"] = " // ".join(persian[i]["persian_text"] for i in p_idx)
            base["hemistich_2"] = persian[p_idx[-1]]["hemistich_2"]
            base["verse_end"] = persian[p_idx[-1]]["verse_number"]
        eng = [english[j] for j in e_idx]
        sep = " / " if layout == "lines" else " "
        base.update(
            english_text=sep.join(e["english_text"] for e in eng),
            translator=eng[0]["translator"],
            translation_style=eng[0]["translation_style"],
            license_note=eng[0]["license_note"],
            edition=eng[0]["edition"],
            english_units=[e["unit_id"] for e in eng],
            align_score=round(s, 4),
            align_kept_by="score" if s >= MIN_SIM else "context",
            align_type=f"{len(p_idx)}:{len(e_idx)}",
        )
        if eng[0].get("translator_verse_est") is not None:
            base["translator_verse"] = eng[0].get("translator_verse")
            base["translator_verse_est"] = eng[0]["translator_verse_est"]
        out.append(base)
    return out


def keep_beads(beads, scores, max_gap=(2, 2)) -> list[bool]:
    """Which beads to keep.

    LaBSE is weak on classical Persian, so a correct pair often scores below
    MIN_SIM. A weak bead is kept when the confident beads just before and after
    it are close on both sides (at most max_gap Persian couplets and English
    units away): it is then boxed in, and its position alone makes it right.
    """
    strong = [s >= MIN_SIM for s in scores]
    keep = list(strong)
    prev = None
    nxt = [None] * len(beads)
    last = None
    for k in range(len(beads) - 1, -1, -1):
        nxt[k] = last
        if strong[k]:
            last = k
    for k, (p_idx, e_idx) in enumerate(beads):
        if not strong[k] and scores[k] >= CONTEXT_MIN_SIM and prev is not None and nxt[k] is not None:
            a, b = beads[prev], beads[nxt[k]]
            keep[k] = (
                p_idx[0] - a[0][-1] <= max_gap[0]
                and e_idx[0] - a[1][-1] <= max_gap[1]
                and b[0][0] - p_idx[-1] <= max_gap[0]
                and b[1][0] - e_idx[-1] <= max_gap[1]
            )
        if strong[k]:
            prev = k
    return keep


def find_divan_ghazals(divan: list[dict], english: list[dict], embed, min_votes: int = 3) -> list[int]:
    """Ganjoor ghazal numbers that the Divan selection translates, in book order.

    Every run of two English lines (about one couplet) votes for the ghazal of
    its most similar Persian couplet. Ghazals with enough votes are kept and
    ordered by where their votes fall in the English text.
    """
    p_emb = embed([persian_text(r) for r in divan])
    texts = [r["english_text"] for r in english]
    pairs = [" ".join(texts[j : j + 2]) for j in range(len(texts) - 1)]
    sims = embed(pairs) @ p_emb.T
    best = sims.argmax(axis=1)
    votes: dict[int, list[int]] = defaultdict(list)
    for j, b in enumerate(best):
        if sims[j, b] >= 0.5:
            votes[divan[b]["poem_number"]].append(j)
    kept = [g for g, js in votes.items() if len(js) >= min_votes]
    return sorted(kept, key=lambda g: float(np.median(votes[g])))


def group_key(row: dict) -> tuple:
    return (row["source"], row.get("book"))


def offset_consistency(rows: list[dict], window: int = 20, tol: int = 3) -> float | None:
    """For Nicholson: share of rows whose Ganjoor-minus-Nicholson verse offset
    agrees with its neighbours'. A correct alignment keeps the offset nearly
    constant; a wrong pair jumps away from it."""
    pts = [r for r in rows if r.get("translator_verse_est") is not None and r["source"] == "Masnavi"]
    if not pts:
        return None
    good = 0
    for k, r in enumerate(pts):
        nb = pts[max(0, k - window) : k + window + 1]
        offs = [x["verse_number"] - x["translator_verse_est"] for x in nb if x["book"] == r["book"]]
        if abs((r["verse_number"] - r["translator_verse_est"]) - float(np.median(offs))) <= tol:
            good += 1
    return good / len(pts)


def summarize(name: str, rows: list[dict], english: list[dict], persian_by_key: dict) -> dict:
    scores = np.array([r["align_score"] for r in rows]) if rows else np.zeros(1)
    used_units = {u for r in rows for u in r["english_units"]}
    keys = {group_key(r) for r in english}
    n_persian = sum(len(persian_by_key[k]) for k in keys if k in persian_by_key)
    return {
        "source": name,
        "aligned_rows": len(rows),
        "english_units": len(english),
        "english_units_used": round(len(used_units) / max(len(english), 1), 3),
        "persian_couplets_in_scope": n_persian,
        "align_types": dict(Counter(r["align_type"] for r in rows).most_common()),
        "score_median": round(float(np.median(scores)), 3),
        "score_p10": round(float(np.percentile(scores, 10)), 3),
        "offset_consistency": offset_consistency(rows),
    }


def main() -> None:
    from data.embed import Embedder

    ap = argparse.ArgumentParser()
    ap.add_argument("--persian", type=Path, required=True)
    ap.add_argument("--english", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    args = ap.parse_args()

    embed = Embedder()
    persian = defaultdict(list)
    for line in args.persian.open(encoding="utf-8"):
        r = json.loads(line)
        persian[group_key(r)].append(r)
    english = [json.loads(line) for line in args.english.open(encoding="utf-8")]
    layout = english[0]["layout"]

    groups = defaultdict(list)
    for r in english:
        groups[group_key(r)].append(r)

    out = []
    for key, eng_rows in groups.items():
        if key == ("Divan", None):
            ghazals = find_divan_ghazals(persian[key], eng_rows, embed)
            by_num = defaultdict(list)
            for r in persian[key]:
                by_num[r["poem_number"]].append(r)
            target = [r for g in ghazals for r in by_num[g]]
            print(f"Divan: matched {len(ghazals)} Ganjoor ghazals ({len(target)} couplets)")
        else:
            target = persian[key]
        print(f"aligning {key}: {len(target)} couplets x {len(eng_rows)} English units")
        out += align_group(target, eng_rows, embed, layout)

    args.out.parent.mkdir(parents=True, exist_ok=True)
    with args.out.open("w", encoding="utf-8") as f:
        for row in out:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")
    summary = summarize(args.english.stem, out, english, persian)
    if ("Divan", None) in groups:
        summary["divan_ghazals_matched"] = len({r["poem_number"] for r in out})
    args.out.with_suffix(".summary.json").write_text(json.dumps(summary, indent=2, ensure_ascii=False))
    print(json.dumps(summary, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
