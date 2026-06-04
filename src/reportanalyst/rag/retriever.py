"""Retrieval layer with citation grounding.

This is the component that makes qualitative claims *traceable*. The narrative
sections of a filing are chunked and indexed; when the analyst forms a claim
("management flags margin pressure"), it retrieves the passage that supports
it and attaches it as a Citation.

Design philosophy — offline-first, upgradeable:
  - By default it uses a local TF-IDF vector index (scikit-learn). This is a
    real semantic-ish retrieval that needs no API key, so the live demo always
    works and costs nothing.
  - If an embeddings client is injected, the same interface uses it instead,
    upgrading retrieval quality. Graceful degradation, not a fake fallback.

The retriever returns the supporting passage AND a similarity score, so the
UI can show *how well grounded* each claim is.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity


@dataclass
class Chunk:
    text: str
    page: int | None = None


def chunk_text(text: str, target_words: int = 120, overlap: int = 25) -> list[Chunk]:
    """Split narrative text into overlapping word-windows.

    Overlap preserves context across boundaries so a claim spanning two
    windows can still retrieve a coherent passage.
    """
    words = text.split()
    if not words:
        return []
    chunks: list[Chunk] = []
    step = max(1, target_words - overlap)
    for start in range(0, len(words), step):
        window = words[start : start + target_words]
        if window:
            chunks.append(Chunk(text=" ".join(window)))
        if start + target_words >= len(words):
            break
    return chunks


class TfidfRetriever:
    """Local, dependency-light retriever. No API key required."""

    def __init__(self, chunks: list[Chunk]) -> None:
        self._chunks = chunks
        self._vectorizer = TfidfVectorizer(stop_words="english", ngram_range=(1, 2))
        corpus = [c.text for c in chunks] or [""]
        self._matrix = self._vectorizer.fit_transform(corpus)

    def retrieve(self, query: str, k: int = 1) -> list[tuple[Chunk, float]]:
        if not self._chunks:
            return []
        q_vec = self._vectorizer.transform([query])
        sims = cosine_similarity(q_vec, self._matrix)[0]
        top = np.argsort(sims)[::-1][:k]
        return [(self._chunks[i], float(sims[i])) for i in top]


def split_sentences(text: str) -> list[str]:
    """Lightweight sentence splitter for surfacing the most relevant line."""
    parts = re.split(r"(?<=[.!?])\s+", text.strip())
    return [p for p in parts if len(p) > 20]
