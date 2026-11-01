"""Split the aligned couplets into train / validation / test.

Splits are made by poem unit (a Masnavi section or a Divan ghazal), so couplets
from the same passage never land on both sides. The test split is fixed by a
hash of the unit id plus a list of famous passages that are always held out,
and must contain at least --min-test parallel couplets. It is never used for
training.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from collections import defaultdict
from pathlib import Path

# Passages always held out for the README's before/after table.
FAMOUS_UNITS = {
    ("Masnavi", 1, 1),  # The Song of the Reed (بشنو این نی)
}


def unit_of(row: dict) -> tuple:
    return (row["source"], row.get("book"), row["poem_number"])


def bucket(unit: tuple) -> float:
    h = hashlib.sha256(json.dumps(unit).encode()).hexdigest()
    return int(h[:8], 16) / 0xFFFFFFFF


def assign(rows: list[dict], test_frac: float, val_frac: float, min_test: int) -> dict[str, list[dict]]:
    units = defaultdict(list)
    for r in rows:
        units[unit_of(r)].append(r)
    order = sorted(units, key=bucket)
    splits = {"train": [], "validation": [], "test": []}
    test_units = [u for u in order if u in FAMOUS_UNITS]
    test_units += [u for u in order if bucket(u) < test_frac and u not in FAMOUS_UNITS]
    # keep adding units (in hash order) until the test split is big enough
    rest = [u for u in order if u not in test_units]
    while sum(len(units[u]) for u in test_units) < min_test and rest:
        test_units.append(rest.pop(0))
    test_set = set(test_units)
    for u in order:
        if u in test_set:
            splits["test"] += units[u]
        elif bucket(u) < test_frac + val_frac:
            splits["validation"] += units[u]
        else:
            splits["train"] += units[u]
    return splits


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--aligned", type=Path, nargs="+", required=True)
    ap.add_argument("--out-dir", type=Path, default=Path("data/processed"))
    ap.add_argument("--test-frac", type=float, default=0.1)
    ap.add_argument("--val-frac", type=float, default=0.05)
    ap.add_argument("--min-test", type=int, default=200)
    args = ap.parse_args()

    rows = [json.loads(l) for p in args.aligned for l in p.open(encoding="utf-8")]
    splits = assign(rows, args.test_frac, args.val_frac, args.min_test)
    args.out_dir.mkdir(parents=True, exist_ok=True)
    for name, part in splits.items():
        with (args.out_dir / f"{name}.jsonl").open("w", encoding="utf-8") as f:
            for r in part:
                f.write(json.dumps(r, ensure_ascii=False) + "\n")
        print(f"{name}: {len(part)} couplets")
    assert len(splits["test"]) >= args.min_test, "test split is smaller than --min-test"


if __name__ == "__main__":
    main()
