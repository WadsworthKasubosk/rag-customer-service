import json
import time
from datetime import datetime
from typing import Optional

from sqlalchemy import select

from app.store.cache import (
    cache_stats as redis_cache_stats,
    clear_cache as redis_clear_cache,
    get_json,
    set_json,
)
from app.store.database import session_scope
from app.store.models import EcommerceLogistics, Product


def _product_to_dict(product: Product) -> dict:
    return {
        "sku_id": product.sku_id,
        "product_name": product.product_name,
        "current_price": float(product.current_price),
        "promo_price": float(product.promo_price) if product.promo_price is not None else None,
        "stock_num": product.stock_num,
        "specs": json.loads(product.specs_json) if product.specs_json else {},
        "is_on_sale": bool(product.is_on_sale),
    }


def _logistics_to_dict(order: EcommerceLogistics) -> dict:
    return {
        "order_id": order.order_id,
        "sku_id": order.sku_id,
        "carrier": order.carrier,
        "status": order.status,
        "address": order.address,
        "created_at": order.created_at.isoformat(),
    }


def get_product(sku_id: int) -> Optional[dict]:
    cache_key = f"product:{sku_id}"
    cached = get_json(cache_key)
    if cached is not None:
        return cached

    with session_scope() as session:
        product = session.get(Product, sku_id)
        if product is None or not product.is_on_sale:
            return None
        result = _product_to_dict(product)

    set_json(cache_key, result)
    return result


def get_stock(sku_id: int) -> Optional[dict]:
    cache_key = f"stock:{sku_id}"
    cached = get_json(cache_key)
    if cached is not None:
        return cached

    product = get_product(sku_id)
    if product is None:
        return None

    stock_num = product["stock_num"]
    if stock_num == 0:
        stock_status = "暂时缺货"
    elif stock_num < 50:
        stock_status = "少量库存"
    elif stock_num < 200:
        stock_status = "库存正常"
    else:
        stock_status = "现货充足"

    result = {
        "sku_id": product["sku_id"],
        "product_name": product["product_name"],
        "stock_num": stock_num,
        "stock_status": stock_status,
    }
    set_json(cache_key, result)
    return result


def list_products(keyword: str = "") -> list[dict]:
    cache_key = f"products:{keyword}"
    cached = get_json(cache_key)
    if cached is not None:
        return cached

    with session_scope() as session:
        stmt = select(Product).where(Product.is_on_sale.is_(True)).order_by(Product.sku_id)
        if keyword:
            stmt = stmt.where(Product.product_name.like(f"%{keyword}%"))
        products = session.scalars(stmt).all()
        result = [_product_to_dict(product) for product in products]

    set_json(cache_key, result)
    return result


def get_logistics(order_id: str) -> Optional[dict]:
    cache_key = f"db-logistics:{order_id}"
    cached = get_json(cache_key)
    if cached is not None:
        return cached

    with session_scope() as session:
        order = session.get(EcommerceLogistics, order_id)
        if order is None:
            return None
        result = _logistics_to_dict(order)

    set_json(cache_key, result)
    return result


def create_logistics_order(sku_id: int, carrier: str, address: str) -> dict:
    order_id = f"ORD{int(time.time() * 1000)}"
    with session_scope() as session:
        order = EcommerceLogistics(
            order_id=order_id,
            sku_id=sku_id,
            carrier=carrier,
            status="已发货",
            address=address,
            created_at=datetime.now(),
        )
        session.add(order)
        session.flush()
        result = _logistics_to_dict(order)

    set_json(f"db-logistics:{order_id}", result)
    return result


def clear_cache():
    redis_clear_cache()


def cache_stats() -> dict:
    return redis_cache_stats()
