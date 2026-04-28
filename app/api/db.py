"""
电商数据 API — FastAPI 接口层
提供商品查询、库存查询、物流查询三个接口
接入 db_service（MySQL + Redis 缓存）
"""

import logging
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.services.db_service import (
    get_product, get_stock, list_products,
    get_logistics, create_logistics_order,
    cache_stats, clear_cache,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/db", tags=["电商数据库"])


# ── 请求模型 ────────────────────────────────────────────────

class ProductQuery(BaseModel):
    sku_id: int


class LogisticsCreate(BaseModel):
    sku_id: int
    carrier: str = "顺丰速运"
    address: str


# ── 商品接口 ────────────────────────────────────────────────

@router.get("/products")
async def api_list_products(keyword: str = ""):
    """商品列表，支持按名称模糊搜索"""
    return {"code": 200, "data": list_products(keyword)}


@router.get("/product/{sku_id}")
async def api_get_product(sku_id: int):
    """获取单个商品详情（价格、规格、库存）"""
    product = get_product(sku_id)
    if not product:
        raise HTTPException(status_code=404, detail="商品不存在")
    return {"code": 200, "data": product}


@router.get("/stock/{sku_id}")
async def api_get_stock(sku_id: int):
    """获取商品实时库存状态"""
    stock = get_stock(sku_id)
    if not stock:
        raise HTTPException(status_code=404, detail="商品不存在")
    return {"code": 200, "data": stock}


# ── 物流接口 ────────────────────────────────────────────────

@router.get("/logistics/{order_id}")
async def api_get_logistics(order_id: str):
    """查询物流状态"""
    info = get_logistics(order_id)
    if not info:
        raise HTTPException(status_code=404, detail="订单不存在")
    return {"code": 200, "data": info}


@router.post("/logistics")
async def api_create_logistics(req: LogisticsCreate):
    """创建物流订单"""
    result = create_logistics_order(req.sku_id, req.carrier, req.address)
    return {"code": 200, "message": "订单已创建", "data": result}


# ── 缓存管理接口 ────────────────────────────────────────────

@router.get("/cache/stats")
async def api_cache_stats():
    """查看缓存统计"""
    return {"code": 200, "data": cache_stats()}


@router.post("/cache/clear")
async def api_clear_cache():
    """清空缓存（数据更新后调用）"""
    clear_cache()
    return {"code": 200, "message": "缓存已清空"}
