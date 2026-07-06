import re
from typing import Dict, Iterable, List


def tokenize(text: str) -> List[str]:
    return re.findall(r"[a-z0-9]+", text.lower())


def _snippet(text: str, terms: Iterable[str], size: int = 180) -> str:
    lower = text.lower()
    first = min((lower.find(term) for term in terms if lower.find(term) >= 0), default=0)
    start = max(0, first - 40)
    snippet = text[start : start + size].strip()
    return snippet.replace("\n", " ")


def search_chunks(chunks: List[Dict[str, object]], query: str, limit: int = 10) -> List[Dict[str, object]]:
    terms = tokenize(query)
    if not terms:
        return []
    hits = []
    for chunk in chunks:
        haystack = " ".join(
            str(chunk.get(key) or "")
            for key in ["title", "heading", "text"]
        ).lower()
        score = 0.0
        for term in terms:
            score += haystack.count(term)
        if score <= 0:
            score = 0.0
        text = str(chunk.get("text") or "")
        hit = dict(chunk)
        hit["score"] = score
        hit["snippet"] = _snippet(text, terms)
        hits.append(hit)
    hits.sort(key=lambda item: (-float(item["score"]), str(item.get("chunk_id", ""))))
    return hits[:limit]

