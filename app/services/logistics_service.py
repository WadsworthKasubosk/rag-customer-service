from __future__ import annotations

from typing import Optional

from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.orm import selectinload

from app.store.cache import delete_pattern, get_json, set_json
from app.store.database import session_scope
from app.store.models import TrackingEvent, TrackingOrder


def _carrier_prefix(carrier: str) -> str:
    if "顺丰" in carrier:
        return "SF"
    if "圆通" in carrier:
        return "YT"
    if "京东" in carrier:
        return "JD"
    return "KD"


def _event_to_dict(event: TrackingEvent) -> dict:
    return {
        "time": event.event_time.strftime("%Y-%m-%d %H:%M"),
        "location": event.location,
        "event": event.event_text,
    }


def _order_to_dict(order: TrackingOrder) -> dict:
    return {
        "order_id": order.order_id,
        "tracking_no": order.tracking_no,
        "carrier": order.carrier,
        "status": order.status,
        "items": order.items,
        "tracking_history": [_event_to_dict(event) for event in order.events],
    }


def _invalidate_order_cache():
    delete_pattern("tracking:*")


def _next_order_id(session) -> str:
    today = datetime.now().strftime("%Y%m%d")
    count = session.scalar(
        select(func.count()).select_from(TrackingOrder).where(TrackingOrder.order_id.like(f"DD{today}%"))
    ) or 0
    return f"DD{today}{count + 1:03d}"


def create_order(items: str, carrier: str = "顺丰速运") -> dict:
    with session_scope() as session:
        order_id = _next_order_id(session)
        prefix = _carrier_prefix(carrier)
        tracking_no = f"{prefix}{datetime.now().strftime('%H%M%S')}{(session.scalar(select(func.count()).select_from(TrackingOrder)) or 0) + 1:04d}"
        now = datetime.now()
        order = TrackingOrder(
            order_id=order_id,
            tracking_no=tracking_no,
            carrier=carrier,
            status="已发货",
            items=items,
            created_at=now,
            updated_at=now,
        )
        session.add(order)
        session.flush()
        order.events.append(
            TrackingEvent(
                event_time=now,
                location="深圳仓库",
                event_text="已发货",
            )
        )
        session.flush()
        result = _order_to_dict(order)

    _invalidate_order_cache()
    set_json(f"tracking:{order_id}", result)
    set_json(f"tracking:events:{order_id}", result["tracking_history"])
    return result


def get_order(order_id: str) -> Optional[dict]:
    cache_key = f"tracking:{order_id}"
    cached = get_json(cache_key)
    if cached is not None:
        return cached

    with session_scope() as session:
        stmt = (
            select(TrackingOrder)
            .where(TrackingOrder.order_id == order_id)
            .options(selectinload(TrackingOrder.events))
        )
        order = session.scalar(stmt)
        if order is None:
            return None
        result = _order_to_dict(order)

    set_json(cache_key, result)
    return result


def get_tracking(order_id: str) -> Optional[list[dict]]:
    cache_key = f"tracking:events:{order_id}"
    cached = get_json(cache_key)
    if cached is not None:
        return cached

    order = get_order(order_id)
    if order is None:
        return None

    set_json(cache_key, order["tracking_history"])
    return order["tracking_history"]


def list_orders() -> list[dict]:
    cache_key = "tracking:list"
    cached = get_json(cache_key)
    if cached is not None:
        return cached

    with session_scope() as session:
        stmt = select(TrackingOrder).order_by(TrackingOrder.created_at.desc()).options(selectinload(TrackingOrder.events))
        orders = session.scalars(stmt).all()
        result = [_order_to_dict(order) for order in orders]

    set_json(cache_key, result)
    return result


def search_orders_for_chat(query: str) -> str:
    lowered = query.lower()
    orders = list_orders()

    for order in orders:
        if order["order_id"].lower() in lowered or order["tracking_no"].lower() in lowered:
            return _format_order(order)

    if not orders:
        return "当前没有物流订单记录。"

    lines = ["当前物流订单："]
    for order in orders:
        lines.append(
            f"- {order['order_id']}（{order['tracking_no']}）：{order['items']} / {order['carrier']} / 状态：{order['status']}"
        )
    return "\n".join(lines)


def _format_order(order: dict) -> str:
    lines = [
        f"订单号：{order['order_id']}",
        f"快递单号：{order['tracking_no']}",
        f"承运商：{order['carrier']}",
        f"商品：{order['items']}",
        f"状态：{order['status']}",
        "物流轨迹：",
    ]
    for item in order["tracking_history"]:
        lines.append(f"  {item['time']} | {item['location']} | {item['event']}")
    return "\n".join(lines)
