from __future__ import annotations

from typing import Generator, Optional
from app.core.vector_store import search, search_faq
from app.core.classifier import classify_question
from app.core.prompt_templates import get_prompt_by_category
from app.models.llm import get_llm
from app.config import TOP_K
from app.services.kg_service import kg_query

_EMPTY_ANSWER = "抱歉，知识库中暂无相关信息，请联系人工客服获取帮助。"


def _get_service_context(category: str, question: str) -> Optional[str]:
    """对于维修/物流跟踪类问题，从对应服务获取上下文"""
    if category == "repair_track":
        from app.services.repair_service import search_tickets_for_chat
        return search_tickets_for_chat(question)
    if category == "logistics_track":
        from app.services.logistics_service import search_orders_for_chat
        return search_orders_for_chat(question)
    return None


def _build_prompt_and_sources(question: str, chat_history: str):
    """公共逻辑：分类 → KG查询 → 检索 → 拼 Prompt，返回 (category, sources, prompt_or_None, kg_used)"""
    category = classify_question(question)

    # KG 结构化查询
    kg_context = None
    try:
        kg_context = kg_query(category, question)
    except Exception:
        pass
    kg_used = kg_context is not None

    # 维修/物流跟踪：优先从服务获取上下文
    service_ctx = _get_service_context(category, question)
    if service_ctx:
        results = search(question, top_k=TOP_K)
        rag_context = "\n\n---\n\n".join([r["content"] for r in results]) if results else ""
        parts = []
        if kg_context:
            parts.append(f"【结构化知识】\n{kg_context}")
        parts.append(f"【实时查询结果】\n{service_ctx}")
        if rag_context:
            parts.append(f"【参考资料】\n{rag_context}")
        context = "\n\n---\n\n".join(parts)
        prompt_template = get_prompt_by_category(category)
        prompt = prompt_template.format(
            context=context,
            question=question,
            chat_history=chat_history or "无",
        )
        sources = [
            {"content": r["content"][:200], "similarity": r["similarity"], "metadata": r["metadata"]}
            for r in results
        ] if results else []
        return category, sources, prompt, kg_used

    results = search(question, top_k=TOP_K)

    if not results and not kg_context:
        return category, [], None, False

    # 合并 KG + RAG 上下文
    parts = []
    if kg_context:
        parts.append(f"【结构化知识】\n{kg_context}")
    if results:
        rag_text = "\n\n---\n\n".join([r["content"] for r in results])
        parts.append(f"【参考资料】\n{rag_text}")

    context = "\n\n---\n\n".join(parts)
    prompt_template = get_prompt_by_category(category)
    prompt = prompt_template.format(
        context=context,
        question=question,
        chat_history=chat_history or "无",
    )
    sources = [
        {
            "content": r["content"][:200],
            "similarity": r["similarity"],
            "metadata": r["metadata"],
        }
        for r in results
    ] if results else []
    return category, sources, prompt, kg_used


def rag_query(question: str, chat_history: str = "") -> dict:
    """非流式问答（保留备用）"""
    category, sources, prompt, kg_used = _build_prompt_and_sources(question, chat_history)

    if prompt is None:
        return {"answer": _EMPTY_ANSWER, "sources": [], "category": category, "kg_used": False}

    llm = get_llm()
    response = llm.invoke(prompt)
    return {"answer": response.content, "sources": sources, "category": category, "kg_used": kg_used}


def rag_query_stream(question: str, chat_history: str = "") -> Generator:
    """
    流式问答生成器，依次 yield 三种事件：
      {"type": "meta",  "category": "...", "sources": [...], "kg_used": bool}
      {"type": "token", "content": "..."}   (多次)
      {"type": "done",  "answer": "..."}
    """
    category, sources, prompt, kg_used = _build_prompt_and_sources(question, chat_history)

    # 异步获取相似问题推荐
    similar_questions = search_faq(question, top_k=3)

    if prompt is None:
        yield {"type": "meta", "category": category, "sources": [], "similar_questions": similar_questions, "kg_used": False}
        yield {"type": "token", "content": _EMPTY_ANSWER}
        yield {"type": "done", "answer": _EMPTY_ANSWER}
        return

    yield {"type": "meta", "category": category, "sources": sources, "similar_questions": similar_questions, "kg_used": kg_used}

    llm = get_llm()
    full_answer = ""
    for chunk in llm.stream(prompt):
        token = chunk.content
        if token:
            full_answer += token
            yield {"type": "token", "content": token}

    yield {"type": "done", "answer": full_answer}
