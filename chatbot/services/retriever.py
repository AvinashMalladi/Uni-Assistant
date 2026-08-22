"""
Minimal, dependency-free RAG retriever over the student handbook.

Uses simple term-frequency overlap scoring (no sklearn/numpy required) so
the demo works even when the embedding API is unavailable. It also uses
Google AI Studio embeddings when GOOGLE_API_KEY is set.
"""
import math
import re
from collections import Counter
from pathlib import Path

from django.conf import settings

_chunks_cache = None
_embedding_cache = None  # list[(chunk_text, embedding_vector)]


def _load_chunks():
    global _chunks_cache
    if _chunks_cache is not None:
        return _chunks_cache
    path = Path(settings.STUDENT_HANDBOOK_PATH)
    text = path.read_text(encoding='utf-8')
    raw_blocks = re.split(r'\n(?==== )', text)
    chunks = [b.strip() for b in raw_blocks if len(b.strip()) > 30]
    _chunks_cache = chunks
    return chunks


def _tokenize(s):
    return re.findall(r"[a-z0-9]+", s.lower())


def _tf(tokens):
    c = Counter(tokens)
    total = sum(c.values()) or 1
    return {k: v / total for k, v in c.items()}


def _keyword_retrieve(query, top_k=3):
    chunks = _load_chunks()
    q_tokens = _tokenize(query)
    if not q_tokens:
        return []
    q_tf = _tf(q_tokens)
    scored = []
    for chunk in chunks:
        c_tokens = _tokenize(chunk)
        c_tf = _tf(c_tokens)
        common = set(q_tf) & set(c_tf)
        score = sum(q_tf[t] * c_tf[t] for t in common)
        score += sum(1 for t in q_tokens if t in c_tokens) * 0.02
        if score > 0:
            scored.append((score, chunk))
    scored.sort(key=lambda x: x[0], reverse=True)
    return [c for _, c in scored[:top_k]]


def _cosine(a, b):
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(y * y for y in b))
    return dot / (na * nb) if na and nb else 0.0


def _embed_retrieve(query, top_k=3):
    """Semantic retrieval using Google AI Studio's embedding model. Falls
    back to keyword retrieval on any failure (missing key, network, etc.)."""
    global _embedding_cache
    from google import genai

    client = genai.Client(api_key=settings.GOOGLE_API_KEY)

    if _embedding_cache is None:
        chunks = _load_chunks()
        result = client.models.embed_content(
            model=settings.GEMINI_EMBEDDING_MODEL,
            contents=chunks,
        )
        _embedding_cache = list(zip(chunks, [item.values for item in result.embeddings]))

    q_emb = client.models.embed_content(
        model=settings.GEMINI_EMBEDDING_MODEL,
        contents=query,
    ).embeddings[0].values
    scored = [(_cosine(q_emb, emb), chunk) for chunk, emb in _embedding_cache]
    scored.sort(key=lambda x: x[0], reverse=True)
    return [c for _, c in scored[:top_k]]


def retrieve_context(query, top_k=3):
    if settings.GOOGLE_API_KEY:
        try:
            embedded_chunks = _embed_retrieve(query, top_k=top_k)
            if embedded_chunks:
                return embedded_chunks
        except Exception:
            pass  # graceful degradation to keyword search
    return _keyword_retrieve(query, top_k=top_k)
