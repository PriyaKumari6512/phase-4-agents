"""TF-IDF cosine similarity in numpy: finds reference tickets for estimation by analogy and near-duplicate
tasks. Deterministic and offline (no embedding model to download)."""

from __future__ import annotations

import math
import re
from collections import Counter

import numpy as np

_TOKEN = re.compile(r"[a-z0-9]+")
_STOP = frozenset("a an and are as at be by for from has have in is it of on or that the this to with will can "
                  "user users should must when then given system shall".split())


def tokens(text: str) -> list[str]:
    words = [w for w in _TOKEN.findall(text.lower()) if w not in _STOP and len(w) > 1]
    return words + [f"{a}_{b}" for a, b in zip(words, words[1:])]


def tfidf_matrix(docs: list[str]) -> np.ndarray:
    """Rows are L2-normalised TF-IDF vectors (sublinear tf, smoothed idf)."""
    toks = [Counter(tokens(d)) for d in docs]
    vocab = {t: i for i, t in enumerate(sorted({t for c in toks for t in c}))}
    if not vocab:
        return np.zeros((len(docs), 1))
    df = Counter(t for c in toks for t in c)
    n = len(docs)
    idf = np.array([math.log((1 + n) / (1 + df[t])) + 1 for t in sorted(vocab, key=vocab.get)])
    m = np.zeros((n, len(vocab)))
    for r, c in enumerate(toks):
        for t, f in c.items():
            m[r, vocab[t]] = 1 + math.log(f)
    m *= idf
    norms = np.linalg.norm(m, axis=1, keepdims=True)
    norms[norms == 0] = 1
    return m / norms


def similarities(queries: list[str], corpus: list[str]) -> np.ndarray:
    """queries x corpus cosine similarities, with one shared vocabulary."""
    m = tfidf_matrix(queries + corpus)
    return m[: len(queries)] @ m[len(queries):].T
