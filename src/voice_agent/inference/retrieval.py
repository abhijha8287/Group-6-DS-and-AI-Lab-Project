"""Lexical retrieval (BM25) over knowledge chunks.

Chosen over embeddings for M3 because each business has only ~15 short rows:
BM25 needs no model download or API call, is deterministic and is easy to debug.
An embedding index can replace it later behind the same ``search`` method.
"""

from __future__ import annotations

import math
import re
from collections import Counter

TOKEN = re.compile(r"[a-z0-9]+")
STOP = set("a an and are as at be by can do does for from has have i if in is it its me my no not of on or "
           "our so that the this to was we what when which will with you your".split())


def tokenize(text: str) -> list[str]:
    return [t for t in TOKEN.findall(text.lower()) if t not in STOP]


class BM25Index:
    def __init__(self, chunks: list[dict], k1: float = 1.5, b: float = 0.75):
        self.chunks = chunks
        self.docs = [tokenize(c["fact_id"] + " " + c["text"]) for c in chunks]
        self.k1, self.b = k1, b
        self.avg_len = sum(map(len, self.docs)) / max(1, len(self.docs))
        df = Counter(t for doc in self.docs for t in set(doc))
        n = len(self.docs)
        self.idf = {t: math.log(1 + (n - f + 0.5) / (f + 0.5)) for t, f in df.items()}

    def search(self, query: str, k: int = 3, kind: str | None = None) -> list[dict]:
        terms = tokenize(query)
        scored = []
        for chunk, doc in zip(self.chunks, self.docs):
            if kind and chunk["kind"] != kind:
                continue
            tf = Counter(doc)
            score = 0.0
            for t in terms:
                if t in tf:
                    num = tf[t] * (self.k1 + 1)
                    den = tf[t] + self.k1 * (1 - self.b + self.b * len(doc) / self.avg_len)
                    score += self.idf[t] * num / den
            if score > 0:
                scored.append((score, chunk))
        scored.sort(key=lambda x: -x[0])
        return [{"id": c["fact_id"], "text": c["text"], "score": round(s, 3)} for s, c in scored[:k]]
