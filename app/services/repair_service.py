from __future__ import annotations

from typing import Optional

from datetime import datetime

from sqlalchemy import func, select

from app.store.cache import delete_pattern, get_json, set_json
from app.store.database import session_scope
from app.store.models import RepairTicket


def _ticket_to_dict(ticket: RepairTicket) -> dict:
    return {
        "ticket_id": ticket.ticket_id,
        "phone": ticket.phone,
        "product": ticket.product,
        "issue": ticket.issue,
        "status": ticket.status,
        "created_at": ticket.created_at.isoformat(),
        "updated_at": ticket.updated_at.isoformat(),
        "estimated_days": ticket.estimated_days,
    }


def _invalidate_ticket_cache():
    delete_pattern("repair:*")


def _next_id(session) -> str:
    today = datetime.now().strftime("%Y%m%d")
    count = session.scalar(
        select(func.count()).select_from(RepairTicket).where(RepairTicket.ticket_id.like(f"WX{today}%"))
    ) or 0
    return f"WX{today}{count + 1:03d}"


def create_ticket(phone: str, product: str, issue: str) -> dict:
    with session_scope() as session:
        ticket = RepairTicket(
            ticket_id=_next_id(session),
            phone=phone,
            product=product,
            issue=issue,
            status="待受理",
            created_at=datetime.now(),
            updated_at=datetime.now(),
            estimated_days=3,
        )
        session.add(ticket)
        session.flush()
        result = _ticket_to_dict(ticket)

    _invalidate_ticket_cache()
    set_json(f"repair:{result['ticket_id']}", result)
    return result


def get_ticket(ticket_id: str) -> Optional[dict]:
    cache_key = f"repair:{ticket_id}"
    cached = get_json(cache_key)
    if cached is not None:
        return cached

    with session_scope() as session:
        ticket = session.get(RepairTicket, ticket_id)
        if ticket is None:
            return None
        result = _ticket_to_dict(ticket)

    set_json(cache_key, result)
    return result


def update_status(ticket_id: str, status: str) -> Optional[dict]:
    with session_scope() as session:
        ticket = session.get(RepairTicket, ticket_id)
        if ticket is None:
            return None
        ticket.status = status
        ticket.updated_at = datetime.now()
        session.flush()
        result = _ticket_to_dict(ticket)

    _invalidate_ticket_cache()
    set_json(f"repair:{ticket_id}", result)
    return result


def list_tickets(phone: Optional[str] = None) -> list[dict]:
    cache_key = f"repair:list:{phone or 'all'}"
    cached = get_json(cache_key)
    if cached is not None:
        return cached

    with session_scope() as session:
        stmt = select(RepairTicket).order_by(RepairTicket.created_at.desc())
        if phone:
            stmt = stmt.where(RepairTicket.phone == phone)
        tickets = session.scalars(stmt).all()
        result = [_ticket_to_dict(ticket) for ticket in tickets]

    set_json(cache_key, result)
    return result


def search_tickets_for_chat(query: str) -> str:
    lowered = query.lower()

    with session_scope() as session:
        tickets = session.scalars(select(RepairTicket).order_by(RepairTicket.created_at.desc())).all()
        matched = None
        for ticket in tickets:
            if ticket.ticket_id.lower() in lowered or ticket.phone.lower() in lowered:
                matched = ticket
                break

        if matched is not None:
            return _format_ticket(_ticket_to_dict(matched))

        if not tickets:
            return "当前没有维修工单记录。"

        lines = ["当前维修工单："]
        for ticket in tickets:
            lines.append(f"- {ticket.ticket_id}：{ticket.product} / {ticket.issue} / 状态：{ticket.status}")
        return "\n".join(lines)


def _format_ticket(ticket: dict) -> str:
    return (
        f"工单号：{ticket['ticket_id']}\n"
        f"产品：{ticket['product']}\n"
        f"问题：{ticket['issue']}\n"
        f"状态：{ticket['status']}\n"
        f"创建时间：{ticket['created_at']}\n"
        f"最近更新：{ticket['updated_at']}\n"
        f"预计维修天数：{ticket['estimated_days']}天"
    )
