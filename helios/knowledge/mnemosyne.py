"""Read-only MNEMOSYNE store — BM25 search over DIOSCURI's mnemosyne.json."""

from __future__ import annotations

import json
import math
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

TOKEN_RE = re.compile(r"[\w\d]{2,}", re.UNICODE)

SOURCE_BOOST = {
    "live": 1.2,
    "readme": 1.15,
    "release": 1.1,
    "doc": 1.05,
    "repo-meta": 1.0,
}

K1 = 1.4
B = 0.75


@dataclass(frozen=True)
class KnowledgeChunk:
    id: str
    repo: str
    source: str
    title: str
    url: str
    text: str
    updated_at: str

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> KnowledgeChunk:
        return cls(
            id=str(d["id"]),
            repo=str(d["repo"]),
            source=str(d["source"]),
            title=str(d["title"]),
            url=str(d["url"]),
            text=str(d["text"]),
            updated_at=str(d.get("updatedAt", "")),
        )


@dataclass(frozen=True)
class RetrievalHit:
    chunk: KnowledgeChunk
    score: float


def tokenize(text: str) -> list[str]:
    return [t.lower() for t in TOKEN_RE.findall(text)]


class MnemosyneReader:
    """Loads chunks from mnemosyne.json (v1/v2) and runs BM25 retrieval."""

    def __init__(self, path: Path) -> None:
        self.path = path
        self.chunks: list[KnowledgeChunk] = []
        self.demo_urls: dict[str, str] = {}
        self.seen_releases: list[str] = []
        self._postings: dict[str, dict[str, int]] = {}
        self._doc_len: dict[str, int] = {}
        self._avg_doc_len = 0.0
        self._dirty = True
        self._load()

    def _load(self) -> None:
        if not self.path.is_file():
            return
        data = json.loads(self.path.read_text(encoding="utf-8"))
        raw = data.get("chunks") or []
        self.chunks = [KnowledgeChunk.from_dict(c) for c in raw if isinstance(c, dict) and "id" in c]
        self.demo_urls = dict(data.get("demoUrls") or {})
        self.seen_releases = list(data.get("seenReleases") or [])
        self._dirty = True

    def reload(self) -> None:
        self._load()

    def stats(self) -> dict[str, Any]:
        repos = sorted({c.repo for c in self.chunks})
        return {
            "path": str(self.path),
            "chunks": len(self.chunks),
            "repos": repos,
            "demo_urls": len(self.demo_urls),
            "seen_releases": len(self.seen_releases),
            "loaded": self.path.is_file(),
        }

    def _rebuild_index(self) -> None:
        self._postings.clear()
        self._doc_len.clear()
        total = 0
        for chunk in self.chunks:
            terms = tokenize(chunk.text)
            self._doc_len[chunk.id] = len(terms)
            total += len(terms)
            seen: set[str] = set()
            for term in terms:
                if term in seen:
                    continue
                seen.add(term)
                self._postings.setdefault(term, {})[chunk.id] = terms.count(term)
        n = len(self.chunks) or 1
        self._avg_doc_len = total / n
        self._dirty = False

    def search(self, query: str, k: int = 6) -> list[RetrievalHit]:
        if self._dirty:
            self._rebuild_index()
        if k <= 0 or not self.chunks:
            return []
        terms = list(dict.fromkeys(tokenize(query)))
        if not terms:
            return []
        n = len(self.chunks)
        scores: dict[str, float] = {}
        for term in terms:
            posting = self._postings.get(term)
            if not posting:
                continue
            df = len(posting)
            idf = math.log(1 + (n - df + 0.5) / (df + 0.5))
            for doc_id, tf in posting.items():
                dl = self._doc_len.get(doc_id, 0)
                denom = tf + K1 * (1 - B + (B * dl) / (self._avg_doc_len or 1))
                scores[doc_id] = scores.get(doc_id, 0.0) + idf * (tf * (K1 + 1) / denom)
        by_id = {c.id: c for c in self.chunks}
        hits: list[RetrievalHit] = []
        for doc_id, raw in scores.items():
            chunk = by_id.get(doc_id)
            if not chunk:
                continue
            boost = SOURCE_BOOST.get(chunk.source, 1.0)
            hits.append(RetrievalHit(chunk=chunk, score=raw * boost))
        hits.sort(key=lambda h: h.score, reverse=True)
        return hits[:k]

    def corpus_for_query(self, query: str, *, k: int = 6) -> str:
        hits = self.search(query, k)
        lines: list[str] = []
        for h in hits:
            c = h.chunk
            lines.append(f"[{c.title}]({c.url}):\n{c.text}")
        return "\n\n".join(lines)

    def recent_releases(self, *, days_hint: int = 14, limit: int = 8) -> list[KnowledgeChunk]:
        releases = [c for c in self.chunks if c.source == "release"]
        releases.sort(key=lambda c: c.updated_at, reverse=True)
        return releases[:limit]

    def repos_with_demos(self) -> dict[str, str]:
        return dict(self.demo_urls)

    def list_repos(self) -> list[str]:
        return sorted({c.repo for c in self.chunks if c.repo})

    def repo_summary(self, repo: str, *, max_chunks: int = 3) -> str:
        """Short digest of a repo from readme/release chunks."""
        hits = [c for c in self.chunks if c.repo == repo]
        hits.sort(key=lambda c: (0 if c.source == "readme" else 1, c.updated_at), reverse=False)
        parts: list[str] = []
        for c in hits[:max_chunks]:
            parts.append(f"[{c.source}] {c.text[:400]}")
        return "\n".join(parts) if parts else "(no chunks)"
