from __future__ import annotations

from typing import Optional

from sqlalchemy import desc, select

from app.store.cache import delete_pattern, get_json, set_json
from app.store.database import session_scope
from app.store.models import ChatMessage, FeedbackRecord


def add_message(session_id: str, role: str, content: str):
    with session_scope() as session:
        session.add(ChatMessage(session_id=session_id, role=role, content=content))
    delete_pattern(f"chat:history:{session_id}:*")


def get_history(session_id: str, limit: int = 20) -> list[dict]:
    cache_key = f"chat:history:{session_id}:{limit}"
    cached = get_json(cache_key)
    if cached is not None:
        return cached

    with session_scope() as session:
        stmt = (
            select(ChatMessage)
            .where(ChatMessage.session_id == session_id)
            .order_by(desc(ChatMessage.id))
            .limit(limit)
        )
        rows = list(session.scalars(stmt).all())
        rows.reverse()
        result = [
            {
                "role": row.role,
                "content": row.content,
                "timestamp": row.created_at.isoformat(),
            }
            for row in rows
        ]

    set_json(cache_key, result)
    return result


def format_history(session_id: str, limit: int = 5) -> str:
    history = get_history(session_id, limit)
    if not history:
        return ""
    lines = []
    for msg in history:
        role = "用户" if msg["role"] == "user" else "客服"
        lines.append(f"{role}: {msg['content']}")
    return "\n".join(lines)


def add_feedback(session_id: str, rating: int, comment: str = "", resolved: Optional[bool] = None):
    with session_scope() as session:
        session.add(
            FeedbackRecord(
                session_id=session_id,
                rating=rating,
                comment=comment,
                resolved=resolved,
            )
        )
    delete_pattern("feedback:*")


def get_feedback_stats() -> dict:
    cache_key = "feedback:stats"
    cached = get_json(cache_key)
    if cached is not None:
        return cached

    with session_scope() as session:
        feedbacks = session.scalars(select(FeedbackRecord).order_by(FeedbackRecord.id.desc())).all()

    if not feedbacks:
        result = {"total": 0, "avg_rating": 0, "satisfaction_rate": 0}
        set_json(cache_key, result)
        return result

    total = len(feedbacks)
    avg_rating = sum(item.rating for item in feedbacks) / total
    satisfied = sum(1 for item in feedbacks if item.rating >= 4)
    resolved_feedbacks = [item for item in feedbacks if item.resolved is not None]
    resolved_total = len(resolved_feedbacks)
    resolved_count = sum(1 for item in resolved_feedbacks if item.resolved)

    result = {
        "total": total,
        "avg_rating": round(avg_rating, 2),
        "satisfaction_rate": round(satisfied / total * 100, 2),
        "resolution_rate": round(resolved_count / resolved_total * 100, 2) if resolved_total else None,
        "resolved_total": resolved_total,
    }
    set_json(cache_key, result)
    return result
