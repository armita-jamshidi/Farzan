"""Push the processed splits and the dataset card to the Hugging Face Hub.

Usage:
    huggingface-cli login
    python data/push_to_hub.py --repo <hf-username>/rumi-persian-english
"""

from __future__ import annotations

import argparse
from pathlib import Path

from datasets import load_dataset
from huggingface_hub import HfApi


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", required=True)
    ap.add_argument("--processed", type=Path, default=Path("data/processed"))
    ap.add_argument("--card", type=Path, default=Path("data/DATASET_CARD.md"))
    ap.add_argument("--private", action="store_true")
    args = ap.parse_args()

    files = {s: str(args.processed / f"{s}.jsonl") for s in ("train", "validation", "test")}
    ds = load_dataset("json", data_files=files)
    ds.push_to_hub(args.repo, private=args.private)
    HfApi().upload_file(
        path_or_fileobj=str(args.card), path_in_repo="README.md", repo_id=args.repo, repo_type="dataset"
    )
    print(f"pushed {ds} to https://huggingface.co/datasets/{args.repo}")


if __name__ == "__main__":
    main()
