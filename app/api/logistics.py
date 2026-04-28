import logging
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from app.services.logistics_service import create_order, get_order, get_tracking, list_orders

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/logistics", tags=["物流跟踪"])


class CreateOrderRequest(BaseModel):
    items: str
    carrier: str = "顺丰速运"


@router.post("/create")
async def api_create_order(req: CreateOrderRequest):
    order = create_order(req.items, req.carrier)
    return {"message": "订单已创建", "order": order}


@router.get("/list")
async def api_list_orders():
    return {"orders": list_orders()}


@router.get("/track/{order_id}")
async def api_track_order(order_id: str):
    tracking = get_tracking(order_id)
    if tracking is None:
        raise HTTPException(status_code=404, detail="订单不存在")
    return {"order_id": order_id, "tracking": tracking}


@router.get("/{order_id}")
async def api_get_order(order_id: str):
    order = get_order(order_id)
    if not order:
        raise HTTPException(status_code=404, detail="订单不存在")
    return order
