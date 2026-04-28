import json
from datetime import datetime

from sqlalchemy import delete, select

from app.store.cache import clear_cache
from app.store.database import init_storage_schema, session_scope
from app.store.models import (
    ChatMessage,
    EcommerceLogistics,
    FeedbackRecord,
    Product,
    Promotion,
    RepairTicket,
    TrackingEvent,
    TrackingOrder,
)


DEMO_PRODUCTS = [
    {
        "sku_id": 1001,
        "product_name": "星辰S14 8GB+256GB",
        "current_price": 3999.00,
        "promo_price": 3699.00,
        "stock_num": 580,
        "specs": {"屏幕": "6.7英寸 AMOLED", "处理器": "骁龙8 Gen2", "电池": "5000mAh", "后摄": "5000万主摄", "前摄": "3200万", "内存": "8GB", "存储": "256GB", "5G": "支持", "防水": "IP68"},
    },
    {
        "sku_id": 1002,
        "product_name": "星辰S14 12GB+256GB",
        "current_price": 4299.00,
        "promo_price": 3999.00,
        "stock_num": 320,
        "specs": {"屏幕": "6.7英寸 AMOLED", "处理器": "骁龙8 Gen2", "电池": "5000mAh", "后摄": "5000万主摄", "前摄": "3200万", "内存": "12GB", "存储": "256GB", "5G": "支持", "防水": "IP68"},
    },
    {
        "sku_id": 1003,
        "product_name": "星辰S14 16GB+512GB",
        "current_price": 4999.00,
        "promo_price": 4599.00,
        "stock_num": 45,
        "specs": {"屏幕": "6.7英寸 AMOLED 120Hz", "处理器": "骁龙8 Gen2", "电池": "5000mAh", "后摄": "5000万主摄+OIS", "前摄": "3200万", "内存": "16GB", "存储": "512GB", "5G": "支持", "防水": "IP68"},
    },
    {
        "sku_id": 1004,
        "product_name": "星辰S14 16GB+1TB",
        "current_price": 5499.00,
        "promo_price": 5199.00,
        "stock_num": 12,
        "specs": {"屏幕": "6.7英寸 AMOLED 120Hz", "处理器": "骁龙8 Gen2", "电池": "5000mAh", "后摄": "5000万主摄+OIS", "前摄": "3200万", "内存": "16GB", "存储": "1TB", "5G": "支持", "防水": "IP68"},
    },
    {
        "sku_id": 1005,
        "product_name": "星辰S14 Pro 16GB+512GB",
        "current_price": 5999.00,
        "promo_price": 5599.00,
        "stock_num": 88,
        "specs": {"屏幕": "6.9英寸 AMOLED 144Hz", "处理器": "骁龙8 Gen3", "电池": "5500mAh 100W快充", "后摄": "2亿像素主摄", "前摄": "5000万", "内存": "16GB", "存储": "512GB", "5G": "支持", "防水": "IP69"},
    },
    {
        "sku_id": 1006,
        "product_name": "星辰S14 Pro 16GB+1TB",
        "current_price": 6499.00,
        "promo_price": 6099.00,
        "stock_num": 6,
        "specs": {"屏幕": "6.9英寸 AMOLED 144Hz", "处理器": "骁龙8 Gen3", "电池": "5500mAh 100W快充", "后摄": "2亿像素主摄", "前摄": "5000万", "内存": "16GB", "存储": "1TB", "5G": "支持", "防水": "IP69"},
    },
]

DEMO_PROMOTIONS = [
    {"sku_id": 1001, "description": "以旧换新补贴", "discount_rate": 0.1, "start_date": "2026-01-01", "end_date": "2026-12-31"},
    {"sku_id": 1002, "description": "分期免息", "discount_rate": 0.0, "start_date": "2026-01-01", "end_date": "2026-12-31"},
    {"sku_id": 1003, "description": "学生认证额外95折", "discount_rate": 0.05, "start_date": "2026-01-01", "end_date": "2026-06-30"},
    {"sku_id": 1005, "description": "限时满5000减300", "discount_rate": 300.0, "start_date": "2026-03-01", "end_date": "2026-03-31"},
]

DEMO_ECOM_LOGISTICS = [
    {"order_id": "ORD20260315001", "sku_id": 1001, "carrier": "顺丰速运", "status": "已发货", "address": "北京市朝阳区建国路88号", "created_at": "2026-03-15T10:00:00"},
    {"order_id": "ORD20260315002", "sku_id": 1003, "carrier": "京东物流", "status": "运输中", "address": "上海市浦东新区世纪大道100号", "created_at": "2026-03-15T12:30:00"},
    {"order_id": "ORD20260315003", "sku_id": 1005, "carrier": "顺丰速运", "status": "派送中", "address": "广州市天河区天河路123号", "created_at": "2026-03-15T17:20:00"},
]

DEMO_REPAIR_TICKETS = [
    {"ticket_id": "WX20260320001", "phone": "138****1234", "product": "星辰S14 8GB+256GB", "issue": "屏幕闪烁，触控失灵", "status": "维修中", "created_at": "2026-03-18T10:00:00", "updated_at": "2026-03-20T14:00:00", "estimated_days": 3},
    {"ticket_id": "WX20260320002", "phone": "139****5678", "product": "星辰S14 Pro 16GB+512GB", "issue": "电池鼓包，续航下降", "status": "已完成", "created_at": "2026-03-15T09:00:00", "updated_at": "2026-03-19T16:00:00", "estimated_days": 5},
    {"ticket_id": "WX20260321003", "phone": "137****9999", "product": "星辰S14 12GB+256GB", "issue": "扬声器无声音", "status": "待受理", "created_at": "2026-03-21T08:30:00", "updated_at": "2026-03-21T08:30:00", "estimated_days": 2},
    {"ticket_id": "WX20260322004", "phone": "136****0001", "product": "星辰S14 16GB+1TB", "issue": "摄像头对焦异常，拍照模糊", "status": "检测中", "created_at": "2026-03-22T09:00:00", "updated_at": "2026-03-22T11:00:00", "estimated_days": 4},
]

DEMO_TRACKING_ORDERS = [
    {
        "order_id": "DD20260320001",
        "tracking_no": "SF1234567890",
        "carrier": "顺丰速运",
        "status": "运输中",
        "items": "星辰S14 深空黑 8GB+256GB",
        "created_at": "2026-03-18T10:00:00",
        "updated_at": "2026-03-21T14:00:00",
        "events": [
            {"time": "2026-03-18 10:00", "location": "深圳星辰仓库", "event": "已揽收，准备发货"},
            {"time": "2026-03-19 08:00", "location": "深圳顺丰分拨中心", "event": "已发出"},
            {"time": "2026-03-20 06:30", "location": "武汉顺丰中转站", "event": "运输中"},
            {"time": "2026-03-21 14:00", "location": "北京顺丰分拨中心", "event": "到达目的地城市"},
        ],
    },
    {
        "order_id": "DD20260320002",
        "tracking_no": "YT9876543210",
        "carrier": "圆通速递",
        "status": "已签收",
        "items": "星辰S14 Pro 星河银 16GB+512GB",
        "created_at": "2026-03-15T14:00:00",
        "updated_at": "2026-03-17T15:30:00",
        "events": [
            {"time": "2026-03-15 14:00", "location": "上海星辰仓库", "event": "已揽收，准备发货"},
            {"time": "2026-03-16 09:00", "location": "南京圆通中转站", "event": "运输中"},
            {"time": "2026-03-17 07:00", "location": "北京圆通分拨中心", "event": "到达派送站"},
            {"time": "2026-03-17 10:00", "location": "北京朝阳配送站", "event": "派送中"},
            {"time": "2026-03-17 15:30", "location": "北京市朝阳区建国路88号", "event": "已签收"},
        ],
    },
    {
        "order_id": "DD20260322003",
        "tracking_no": "JD0011223344",
        "carrier": "京东物流",
        "status": "派送中",
        "items": "星辰S14 月光白 12GB+256GB",
        "created_at": "2026-03-21T16:00:00",
        "updated_at": "2026-03-22T20:00:00",
        "events": [
            {"time": "2026-03-21 16:00", "location": "广州星辰仓库", "event": "已揽收，准备发货"},
            {"time": "2026-03-22 08:00", "location": "广州京东华南仓", "event": "已发出"},
            {"time": "2026-03-22 20:00", "location": "上海京东分拨中心", "event": "运输中"},
        ],
    },
    {
        "order_id": "DD20260322004",
        "tracking_no": "SF5566778899",
        "carrier": "顺丰速运",
        "status": "已发货",
        "items": "星辰S14 Pro 深空黑 16GB+1TB",
        "created_at": "2026-03-22T11:00:00",
        "updated_at": "2026-03-22T14:30:00",
        "events": [
            {"time": "2026-03-22 11:00", "location": "深圳星辰仓库", "event": "已揽收，准备发货"},
            {"time": "2026-03-22 14:30", "location": "深圳顺丰分拨中心", "event": "已发出"},
        ],
    },
]


def _parse_dt(value: str) -> datetime:
    if "T" in value:
        return datetime.fromisoformat(value)
    return datetime.strptime(value, "%Y-%m-%d %H:%M")


def _ensure_reference_data(session):
    if session.scalar(select(Product).limit(1)) is None:
        for item in DEMO_PRODUCTS:
            session.add(
                Product(
                    sku_id=item["sku_id"],
                    product_name=item["product_name"],
                    current_price=item["current_price"],
                    promo_price=item["promo_price"],
                    stock_num=item["stock_num"],
                    specs_json=json.dumps(item["specs"], ensure_ascii=False),
                    is_on_sale=True,
                )
            )
    if session.scalar(select(Promotion).limit(1)) is None:
        for item in DEMO_PROMOTIONS:
            session.add(Promotion(**item))
    if session.scalar(select(EcommerceLogistics).limit(1)) is None:
        for item in DEMO_ECOM_LOGISTICS:
            session.add(
                EcommerceLogistics(
                    order_id=item["order_id"],
                    sku_id=item["sku_id"],
                    carrier=item["carrier"],
                    status=item["status"],
                    address=item["address"],
                    created_at=_parse_dt(item["created_at"]),
                )
            )


def _reset_runtime_demo_tables(session):
    session.execute(delete(TrackingEvent))
    session.execute(delete(TrackingOrder))
    session.execute(delete(RepairTicket))
    session.execute(delete(ChatMessage))
    session.execute(delete(FeedbackRecord))

    for item in DEMO_REPAIR_TICKETS:
        session.add(
            RepairTicket(
                ticket_id=item["ticket_id"],
                phone=item["phone"],
                product=item["product"],
                issue=item["issue"],
                status=item["status"],
                created_at=_parse_dt(item["created_at"]),
                updated_at=_parse_dt(item["updated_at"]),
                estimated_days=item["estimated_days"],
            )
        )

    for item in DEMO_TRACKING_ORDERS:
        order = TrackingOrder(
            order_id=item["order_id"],
            tracking_no=item["tracking_no"],
            carrier=item["carrier"],
            status=item["status"],
            items=item["items"],
            created_at=_parse_dt(item["created_at"]),
            updated_at=_parse_dt(item["updated_at"]),
        )
        session.add(order)
        session.flush()
        for event in item["events"]:
            session.add(
                TrackingEvent(
                    order_id=order.order_id,
                    event_time=_parse_dt(event["time"]),
                    location=event["location"],
                    event_text=event["event"],
                )
            )


def init_demo_data(reset_runtime: bool = False) -> dict:
    init_storage_schema()
    with session_scope() as session:
        _ensure_reference_data(session)
        has_runtime_data = session.scalar(select(RepairTicket).limit(1)) is not None
        if reset_runtime or not has_runtime_data:
            _reset_runtime_demo_tables(session)
    clear_cache()
    return demo_status()


def demo_status() -> dict:
    with session_scope() as session:
        repair_ids = session.scalars(select(RepairTicket.ticket_id).order_by(RepairTicket.ticket_id)).all()
        order_ids = session.scalars(select(TrackingOrder.order_id).order_by(TrackingOrder.order_id)).all()
        return {
            "repair_tickets": len(repair_ids),
            "logistics_orders": len(order_ids),
            "repair_ids": repair_ids,
            "order_ids": order_ids,
        }
