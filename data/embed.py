"""LaBSE sentence embeddings with an on-disk cache.

Alignment embeds the same Persian couplets once per translation, and a whole
Masnavi book takes minutes on a CPU, so vectors are cached in a small SQLite
file keyed by the text's SHA-1.
"""

from __future__ import annotations

import hashlib
import sqlite3
from pathlib import Path
from typing import Sequence

import numpy as np

MODEL_NAME = "sentence-transformers/LaBSE"
DEFAULT_CACHE = Path("data/interim/labse_cache.sqlite")


class Embedder:
    def __init__(self, cache: Path = DEFAULT_CACHE, model_name: str = MODEL_NAME):
        self.model_name = model_name
        self._model = None
        cache.parent.mkdir(parents=True, exist_ok=True)
        self.db = sqlite3.connect(cache)
        self.db.execute("CREATE TABLE IF NOT EXISTS emb (key TEXT PRIMARY KEY, vec BLOB)")

    @property
    def model(self):
        if self._model is None:
            from sentence_transformers import SentenceTransformer

            self._model = SentenceTransformer(self.model_name)
        return self._model

    @staticmethod
    def _key(text: str) -> str:
        return hashlib.sha1(text.encode("utf-8")).hexdigest()

    def __call__(self, texts: Sequence[str]) -> np.ndarray:
        keys = [self._key(t) for t in texts]
        found: dict[str, np.ndarray] = {}
        for i in range(0, len(keys), 900):  # SQLite caps bound parameters
            chunk = keys[i : i + 900]
            q = f"SELECT key, vec FROM emb WHERE key IN ({','.join('?' * len(chunk))})"
            for k, v in self.db.execute(q, chunk):
                found[k] = np.frombuffer(v, dtype=np.float16)
        todo = sorted({k: t for k, t in zip(keys, texts) if k not in found}.items())
        if todo:
            vecs = self.model.encode(
                [t for _, t in todo], batch_size=64, normalize_embeddings=True, show_progress_bar=len(todo) > 500
            ).astype(np.float16)
            self.db.executemany("INSERT OR REPLACE INTO emb VALUES (?, ?)", [(k, v.tobytes()) for (k, _), v in zip(todo, vecs)])
            self.db.commit()
            found.update({k: v for (k, _), v in zip(todo, vecs)})
        return np.stack([found[k] for k in keys]).astype(np.float32)
