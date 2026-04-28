"""
KG 查询路由 — 根据分类和关键词将问题路由到对应的知识图谱查询函数
"""
from __future__ import annotations

from typing import Optional

import logging
from app.core.knowledge_graph import (
    query_product_price, query_stock, query_spec_comparison,
    query_repair_cost, query_warranty, query_product_specs,
    query_accessories, query_issues,
)

logger = logging.getLogger(__name__)

# 关键词 → 查询函数映射
_PRICE_KW = ["价格", "多少钱", "售价", "报价", "费用", "元"]
_STOCK_KW = ["库存", "有货", "缺货", "现货", "补货", "到货"]
_COMPARE_KW = ["对比", "区别", "差别", "比较", "vs", "pro"]
_REPAIR_COST_KW = ["维修费", "修多少钱", "换屏", "换电池", "维修价", "修理费"]
_WARRANTY_KW = ["保修", "保修期", "三包", "退货", "换货", "退换"]
_SPEC_KW = ["规格", "参数", "配置", "处理器", "芯片", "屏幕", "电池", "摄像头",
            "内存", "存储", "防水", "尺寸", "重量", "充电"]
_ACCESSORY_KW = ["配件", "充电器", "数据线", "手机壳", "贴膜", "保护膜", "转接"]
_ISSUE_KW = ["故障", "失灵", "坏了", "不工作", "无法", "异常", "卡顿", "发热"]


def _has_keyword(question: str, keywords: list[str]) -> bool:
    return any(kw in question.lower() for kw in keywords)


def kg_query(category: str, question: str) -> Optional[str]:
    """
    根据分类和问题内容路由到合适的 KG 查询。
    返回结构化知识文本，或 None（无匹配）。
    """
    results = []

    try:
        if category == "ecommerce":
            if _has_keyword(question, _PRICE_KW):
                r = query_product_price(question)
                if r:
                    results.append(r)
            if _has_keyword(question, _STOCK_KW):
                r = query_stock(question)
                if r:
                    results.append(r)
            if _has_keyword(question, _COMPARE_KW):
                r = query_spec_comparison()
                if r:
                    results.append(r)
            if _has_keyword(question, _ACCESSORY_KW):
                r = query_accessories()
                if r:
                    results.append(r)

        elif category == "after_sales":
            if _has_keyword(question, _REPAIR_COST_KW):
                r = query_repair_cost(question)
                if r:
                    results.append(r)
            if _has_keyword(question, _WARRANTY_KW):
                r = query_warranty(question)
                if r:
                    results.append(r)
            if _has_keyword(question, _ISSUE_KW):
                r = query_issues(question)
                if r:
                    results.append(r)

        elif category == "product_qa":
            if _has_keyword(question, _SPEC_KW):
                r = query_product_specs(question)
                if r:
                    results.append(r)
            if _has_keyword(question, _COMPARE_KW):
                r = query_spec_comparison()
                if r:
                    results.append(r)
            if _has_keyword(question, _ACCESSORY_KW):
                r = query_accessories()
                if r:
                    results.append(r)

        # 兜底：任何分类下的价格/库存/维修费查询
        if not results:
            if _has_keyword(question, _PRICE_KW):
                r = query_product_price(question)
                if r:
                    results.append(r)
            elif _has_keyword(question, _STOCK_KW):
                r = query_stock(question)
                if r:
                    results.append(r)
            elif _has_keyword(question, _REPAIR_COST_KW + ["修", "维修"]):
                r = query_repair_cost(question)
                if r:
                    results.append(r)
                r2 = query_warranty(question)
                if r2:
                    results.append(r2)

    except Exception as e:
        logger.warning(f"KG查询异常: {e}")
        return None

    return "\n\n".join(results) if results else None
