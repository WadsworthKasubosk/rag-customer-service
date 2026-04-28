from __future__ import annotations

from typing import Optional

import os
import re
import math
import numpy as np
from collections import Counter
from langchain_community.vectorstores import FAISS
from langchain_core.documents import Document
from app.config import FAISS_INDEX_DIR, DOCS_DIR, CHUNK_SIZE, CHUNK_OVERLAP, MOCK_RETRIEVAL

# ── 关键词检索（Mock 模式，无需嵌入模型）──────────────────────────

_docs_cache: Optional[list[dict]] = None
_faq_cache: Optional[list[str]] = None


def _load_docs() -> list[dict]:
    global _docs_cache
    if _docs_cache is not None:
        return _docs_cache
    docs = []
    if not os.path.isdir(DOCS_DIR):
        return docs
    for fname in os.listdir(DOCS_DIR):
        if not fname.endswith(".txt"):
            continue
        fpath = os.path.join(DOCS_DIR, fname)
        with open(fpath, "r", encoding="utf-8") as f:
            text = f.read()
        paragraphs = [p.strip() for p in re.split(r"\n{2,}", text) if p.strip()]
        for para in paragraphs:
            if len(para) <= CHUNK_SIZE:
                docs.append({"content": para, "metadata": {"source": fname}})
            else:
                for i in range(0, len(para), CHUNK_SIZE - CHUNK_OVERLAP):
                    chunk = para[i: i + CHUNK_SIZE]
                    if chunk.strip():
                        docs.append({"content": chunk, "metadata": {"source": fname}})
    _docs_cache = docs
    return docs


def _load_faq_lines() -> list[str]:
    global _faq_cache
    if _faq_cache is not None:
        return _faq_cache
    faq_path = os.path.join(DOCS_DIR, "faq.txt")
    if not os.path.exists(faq_path):
        _faq_cache = []
        return []
    with open(faq_path, "r", encoding="utf-8") as f:
        lines = [l.strip() for l in f if l.strip()]
    _faq_cache = lines
    return lines


def _tokenize(text: str) -> list[str]:
    tokens = list(text)
    bigrams = [text[i: i + 2] for i in range(len(text) - 1)]
    return tokens + bigrams


def _bm25_score(query: str, doc: str, avg_len: float, k1: float = 1.5, b: float = 0.75) -> float:
    q_tokens = Counter(_tokenize(query))
    d_tokens = Counter(_tokenize(doc))
    dl = len(doc)
    score = 0.0
    for token, _ in q_tokens.items():
        tf = d_tokens.get(token, 0)
        if tf == 0:
            continue
        idf = math.log(2.0)
        tf_norm = tf * (k1 + 1) / (tf + k1 * (1 - b + b * dl / avg_len))
        score += idf * tf_norm
    return score


def _keyword_search(query: str, top_k: int = 5) -> list[dict]:
    docs = _load_docs()
    if not docs:
        return []
    avg_len = sum(len(d["content"]) for d in docs) / len(docs)
    scored = [(d, _bm25_score(query, d["content"], avg_len)) for d in docs]
    scored.sort(key=lambda x: x[1], reverse=True)
    results = []
    for d, score in scored[:top_k]:
        if score > 0:
            similarity = round(min(score / 10.0, 1.0), 4)
            results.append({
                "content": d["content"],
                "similarity": similarity,
                "l2_distance": round(1.0 - similarity, 4),
                "metadata": d["metadata"],
            })
    return results


def _keyword_search_faq(query: str, top_k: int = 3) -> list[str]:
    faqs = _load_faq_lines()
    if not faqs:
        return []
    scored = [(q, _bm25_score(query, q, 15.0)) for q in faqs]
    scored.sort(key=lambda x: x[1], reverse=True)
    results = []
    for q, score in scored:
        if q.strip() == query.strip():
            continue
        if score > 0:
            results.append(q)
        if len(results) >= top_k:
            break
    if not results:
        results = [q for q in faqs if q.strip() != query.strip()][:top_k]
    return results


# ── 向量检索（真实模式）────────────────────────────────────────────

_vector_store = None
_faq_questions: list[str] = []
_faq_embeddings: Optional[np.ndarray] = None


def get_vector_store() -> Optional[FAISS]:
    global _vector_store
    if MOCK_RETRIEVAL:
        return None
    if _vector_store is None:
        from app.core.embeddings import get_embeddings
        index_path = os.path.join(FAISS_INDEX_DIR, "index.faiss")
        if os.path.exists(index_path):
            _vector_store = FAISS.load_local(
                FAISS_INDEX_DIR,
                get_embeddings(),
                allow_dangerous_deserialization=True,
            )
    return _vector_store


def add_documents(chunks: list[str], metadata: dict = None) -> int:
    global _vector_store, _docs_cache
    _docs_cache = None
    if MOCK_RETRIEVAL:
        return len(chunks)
    from app.core.embeddings import get_embeddings
    documents = [
        Document(page_content=chunk, metadata=metadata or {})
        for chunk in chunks
    ]
    embeddings = get_embeddings()
    if _vector_store is None:
        _vector_store = FAISS.from_documents(documents, embeddings)
    else:
        _vector_store.add_documents(documents)
    os.makedirs(FAISS_INDEX_DIR, exist_ok=True)
    _vector_store.save_local(FAISS_INDEX_DIR)
    return len(chunks)


def delete_all():
    global _vector_store, _docs_cache
    _vector_store = None
    _docs_cache = None
    if not MOCK_RETRIEVAL:
        for fname in ("index.faiss", "index.pkl"):
            fpath = os.path.join(FAISS_INDEX_DIR, fname)
            if os.path.exists(fpath):
                os.remove(fpath)


def l2_to_cosine_similarity(l2_distance: float) -> float:
    similarity = 1.0 - (l2_distance ** 2) / 2.0
    return max(0.0, min(1.0, similarity))


def search(query: str, top_k: int = 5) -> list[dict]:
    if MOCK_RETRIEVAL:
        return _keyword_search(query, top_k)
    vs = get_vector_store()
    if vs is None:
        return _keyword_search(query, top_k)
    results = vs.similarity_search_with_score(query, k=top_k)
    return [
        {
            "content": doc.page_content,
            "similarity": round(l2_to_cosine_similarity(float(score)), 4),
            "l2_distance": round(float(score), 4),
            "metadata": doc.metadata,
        }
        for doc, score in results
    ]


def load_faq():
    """加载 FAQ（兼容旧调用）"""
    global _faq_questions, _faq_embeddings
    if MOCK_RETRIEVAL:
        return
    from app.core.embeddings import get_embeddings
    questions = _load_faq_lines()
    if not questions:
        return
    _faq_questions = questions
    embeddings = get_embeddings()
    _faq_embeddings = np.array(embeddings.embed_documents(questions))


def search_faq(query: str, top_k: int = 3) -> list[str]:
    if MOCK_RETRIEVAL:
        return _keyword_search_faq(query, top_k)
    global _faq_questions, _faq_embeddings
    if _faq_embeddings is None or len(_faq_questions) == 0:
        load_faq()
    if _faq_embeddings is None or len(_faq_questions) == 0:
        return _keyword_search_faq(query, top_k)
    from app.core.embeddings import get_embeddings
    embeddings = get_embeddings()
    query_vec = np.array(embeddings.embed_query(query))
    similarities = _faq_embeddings @ query_vec
    top_indices = np.argsort(similarities)[::-1][:top_k + 1]
    results = []
    for idx in top_indices:
        q = _faq_questions[idx]
        if q.strip() == query.strip():
            continue
        results.append(q)
        if len(results) >= top_k:
            break
    return results
