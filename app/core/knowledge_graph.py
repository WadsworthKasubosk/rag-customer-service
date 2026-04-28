"""
知识图谱加载与查询 — 单例模式
从 data/kg/graph.pkl 加载 NetworkX 图，提供结构化查询函数
同时接入 db_service（MySQL + Redis）支持电商类实时数据查询
"""
from __future__ import annotations

from typing import Optional

import os
import pickle
import networkx as nx

_BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
_KG_PATH = os.path.join(_BASE_DIR, "data", "kg", "graph.pkl")

_graph: Optional[nx.DiGraph] = None


def get_graph() -> nx.DiGraph:
    global _graph
    if _graph is None:
        if not os.path.exists(_KG_PATH):
            import logging
            logging.getLogger(__name__).warning(
                f"知识图谱文件不存在: {_KG_PATH}，将使用空图谱。请运行 python -m app.scripts.build_graph"
            )
            _graph = nx.DiGraph()
        else:
            with open(_KG_PATH, "rb") as f:
                _graph = pickle.load(f)
    return _graph


def graph_stats() -> dict:
    G = get_graph()
    type_counts = {}
    for _, data in G.nodes(data=True):
        t = data.get("type", "unknown")
        type_counts[t] = type_counts.get(t, 0) + 1
    return {"nodes": G.number_of_nodes(), "edges": G.number_of_edges(), "types": type_counts}


def _neighbors(node: str, relation: Optional[str] = None) -> list[tuple[str, dict]]:
    """获取节点的出边邻居，可按关系类型过滤"""
    G = get_graph()
    if node not in G:
        return []
    results = []
    for _, target, edata in G.out_edges(node, data=True):
        if relation is None or edata.get("relation") == relation:
            results.append((target, G.nodes[target]))
    return results


# ── 查询函数 ──


def query_product_price(question: str) -> Optional[str]:
    """
    查询产品价格，支持按SKU精确匹配
    优先从 MySQL 数据库实时查询（db_service），
    数据库不可用时回退到知识图谱数据。
    """
    # ── 优先：真实数据库查询 ──
    try:
        from app.services.db_service import get_product
        # 从问题中解析 SKU
        sku_map = {
            "8+256": 1001, "8gb256": 1001,
            "12+256": 1002, "12gb256": 1002,
            "16+512": 1003, "16gb512": 1003,
            "16+1t": 1004, "16gb1tb": 1004, "1tb": 1004,
            "pro": None,          # 需要返回 Pro 系列
        }
        q = question.lower().replace(" ", "").replace("gb", "").replace("g", "")
        matched_id = None
        is_pro = "pro" in question.lower()
        for pat, sid in sku_map.items():
            if pat in q:
                if sid:
                    matched_id = sid
                    break
                # "pro" 关键词继续走后续逻辑
        if matched_id is None and not is_pro:
            # 没有指定 SKU，默认返回最低价
            products = _db_list_all_products()
            if products:
                lines = [f"星辰S14 系列价格（实时数据库查询）："]
                for p in products:
                    promo = f" → 促销价 {p['promo_price']}元" if p.get("promo_price") else ""
                    lines.append(f"  {p['product_name']}：官方价 {p['current_price']}元{promo}")
                return "\n".join(lines)
        if matched_id:
            p = get_product(matched_id)
            if p:
                promo_str = f"，限时促销 {p['promo_price']}元" if p.get("promo_price") else ""
                return (f"星辰S14 {p['product_name']}：\n"
                        f"  官方价 {p['current_price']}元{promo_str}\n"
                        f"  实时库存 {p['stock_num']} 件")
        if is_pro:
            pro_products = [p for p in _db_list_all_products() if "pro" in p["product_name"].lower()]
            if pro_products:
                lines = ["星辰S14 Pro 系列价格（实时数据库查询）："]
                for p in pro_products:
                    promo = f" → 促销价 {p['promo_price']}元" if p.get("promo_price") else ""
                    lines.append(f"  {p['product_name']}：官方价 {p['current_price']}元{promo}")
                return "\n".join(lines)
    except Exception:
        pass  # 数据库不可用，回退到图谱

    # ── 回退：知识图谱查询 ──
    G = get_graph()
    lines = []

    sku_patterns = {"8+256": "8+256", "12+256": "12+256", "16+512": "16+512",
                    "16+1t": "16+1TB", "16+1tb": "16+1TB", "1tb": "16+1TB"}
    matched_sku = None
    q = question.lower().replace(" ", "").replace("gb", "").replace("g", "")
    for pat, sku_id in sku_patterns.items():
        if pat in q:
            matched_sku = sku_id
            break

    if matched_sku:
        node_id = f"SKU_{matched_sku}"
        if node_id in G:
            d = G.nodes[node_id]
            lines.append(f"星辰S14 {matched_sku}：官方价 {d['price']}元，促销价 {d['promo_price']}元")
    else:
        for _, target, edata in G.out_edges("星辰S14", data=True):
            if edata.get("relation") == "HAS_SKU":
                d = G.nodes[target]
                lines.append(f"{d['name']}：官方价 {d['price']}元，促销价 {d['promo_price']}元")

    for _, target, edata in G.out_edges("星辰S14", data=True):
        if edata.get("relation") == "HAS_PROMOTION":
            d = G.nodes[target]
            end = f"（截止{d['end_date']}）" if d.get("end_date") else ""
            lines.append(f"促销：{d['description']}{end}")

    return "\n".join(lines) if lines else None


def _db_list_all_products() -> list[dict]:
    """辅助：列出所有商品（db_service）"""
    try:
        from app.services.db_service import list_products
        return list_products()
    except Exception:
        return []


def query_stock(question: str) -> Optional[str]:
    """
    查询库存状态
    优先从 MySQL 数据库实时查询，没有数据库时回退到知识图谱。
    """
    # ── 优先：真实数据库查询 ──
    try:
        from app.services.db_service import get_stock, list_products

        q = question.lower()
        # 精确 SKU 匹配
        sku_map = {
            "8+256": 1001, "12+256": 1002, "16+512": 1003,
            "16+1t": 1004, "1tb": 1004, "pro": None,
        }
        matched_id = None
        is_pro = "pro" in q
        for pat, sid in sku_map.items():
            if pat in q.replace(" ", "").replace("gb", ""):
                if sid:
                    matched_id = sid
                    break

        if matched_id:
            stock = get_stock(matched_id)
            if stock:
                return (f"星辰S14 {stock['product_name']}：\n"
                        f"  实时库存 {stock['stock_num']} 件（{stock['stock_status']}）\n"
                        f"  [数据来源：实时商品数据库]")
        elif is_pro:
            pro_products = [p for p in list_products() if "pro" in p["product_name"].lower()]
            if pro_products:
                lines = ["星辰S14 Pro 系列实时库存："]
                for p in pro_products:
                    lines.append(f"  {p['product_name']}：{p['stock_num']} 件")
                lines.append("[数据来源：实时商品数据库]")
                return "\n".join(lines)
        else:
            # 无 SKU 关键词，返回全部
            products = list_products()
            lines = ["星辰S14 全系实时库存："]
            for p in products:
                promo = f" → 促销价 {p['promo_price']}元" if p.get("promo_price") else ""
                lines.append(f"  {p['product_name']}：{p['stock_num']} 件{promo}")
            lines.append("[数据来源：实时商品数据库]")
            return "\n".join(lines)
    except Exception:
        pass  # 数据库不可用，回退到图谱

    # ── 回退：知识图谱查询 ──
    G = get_graph()
    lines = []

    target_color = None
    target_sku = None
    for c in ["星空黑", "月光白", "山岩青", "樱花粉"]:
        if c in question:
            target_color = c
            break
    sku_patterns = {"8+256": "8+256", "12+256": "12+256", "16+512": "16+512",
                    "16+1t": "16+1TB", "1tb": "16+1TB"}
    q = question.lower().replace(" ", "").replace("gb", "").replace("g", "")
    for pat, sid in sku_patterns.items():
        if pat in q:
            target_sku = sid
            break

    for nid, data in G.nodes(data=True):
        if data.get("type") != "StockStatus":
            continue
        if target_sku and data.get("sku") != target_sku:
            continue
        if target_color and data.get("color") != target_color:
            continue
        restock = f"，{data['restock_date']}" if data.get("restock_date") else ""
        lines.append(f"S14 {data['sku']} {data['color']}：{data['status']}{restock}")

    return "\n".join(lines) if lines else None


def query_spec_comparison() -> Optional[str]:
    """S14 vs S14 Pro 规格对比"""
    G = get_graph()
    s14_specs = {}
    pro_specs = {}

    for _, target, edata in G.out_edges("星辰S14", data=True):
        if edata.get("relation") == "HAS_SPEC":
            d = G.nodes[target]
            s14_specs[d["category"]] = d["value"]

    for _, target, edata in G.out_edges("星辰S14 Pro", data=True):
        if edata.get("relation") == "HAS_SPEC":
            d = G.nodes[target]
            pro_specs[d["category"]] = d["value"]

    if not s14_specs:
        return None

    lines = ["| 项目 | 星辰S14 | 星辰S14 Pro |", "|------|---------|-------------|"]
    cat_names = {"processor": "处理器", "screen": "屏幕", "battery": "电池",
                 "camera_rear": "后摄", "body": "机身材质"}
    lines.append(f"| 价格 | 3999元起 | 4999元起 |")
    for cat, label in cat_names.items():
        s = s14_specs.get(cat, "—")
        p = pro_specs.get(cat, "—")
        lines.append(f"| {label} | {s} | {p} |")

    return "\n".join(lines)


def query_repair_cost(question: str) -> Optional[str]:
    """查询维修费用"""
    G = get_graph()
    lines = []
    keywords = {"屏幕": "屏幕更换", "屏": "屏幕更换", "电池": "电池更换",
                "后盖": "后盖更换", "主板": "主板维修", "摄像头": "摄像头模组更换", "相机": "摄像头模组更换"}
    matched = None
    for kw, repair_name in keywords.items():
        if kw in question:
            matched = repair_name
            break

    for nid, data in G.nodes(data=True):
        if data.get("type") != "RepairItem":
            continue
        if matched and data["name"] != matched:
            continue
        note = f"（{data['note']}）" if data.get("note") else ""
        lines.append(f"{data['name']}：{data['cost']}元{note}")

    return "\n".join(lines) if lines else None


def query_warranty(question: str) -> Optional[str]:
    """查询保修政策"""
    G = get_graph()
    lines = []
    for _, target, edata in G.out_edges("星辰S14", data=True):
        if edata.get("relation") != "COVERED_BY":
            continue
        d = G.nodes[target]
        dur = f"（{d['duration']}）" if d.get("duration") else ""
        lines.append(f"{d['name']}{dur}：{d['conditions']}")
    return "\n".join(lines) if lines else None


def query_product_specs(question: str) -> Optional[str]:
    """查询产品规格"""
    G = get_graph()
    lines = []
    cat_keywords = {"处理器": "processor", "芯片": "processor", "cpu": "processor",
                    "屏幕": "screen", "屏": "screen", "电池": "battery", "续航": "battery",
                    "充电": "battery", "摄像": "camera_rear", "拍照": "camera_rear",
                    "相机": "camera_rear", "前摄": "camera_front", "自拍": "camera_front",
                    "网络": "network", "5g": "network", "wifi": "network",
                    "接口": "port", "usb": "port", "尺寸": "size", "重量": "size",
                    "防水": "waterproof"}
    target_cat = None
    q = question.lower()
    for kw, cat in cat_keywords.items():
        if kw in q:
            target_cat = cat
            break

    for _, target, edata in G.out_edges("星辰S14", data=True):
        if edata.get("relation") != "HAS_SPEC":
            continue
        d = G.nodes[target]
        if target_cat and d["category"] != target_cat:
            continue
        detail = f"（{d['detail']}）" if d.get("detail") else ""
        lines.append(f"{d['value']}{detail}")

    return "\n".join(lines) if lines else None


def query_accessories() -> Optional[str]:
    """查询配件信息"""
    G = get_graph()
    lines = []
    for _, target, edata in G.out_edges("星辰S14", data=True):
        if edata.get("relation") != "HAS_ACCESSORY":
            continue
        d = G.nodes[target]
        lines.append(f"{d['name']}：{d['price']}元")
    return "\n".join(lines) if lines else None


def query_issues(question: str) -> Optional[str]:
    """查询常见故障"""
    G = get_graph()
    lines = []
    cat_keywords = {"屏幕": "屏幕", "触摸": "屏幕", "充电": "充电", "电池": "电池",
                    "发热": "散热", "wifi": "网络", "网络": "网络", "蓝牙": "网络",
                    "指纹": "指纹", "卡顿": "系统", "开机": "系统", "密码": "系统",
                    "相机": "相机"}
    target_cat = None
    q = question.lower()
    for kw, cat in cat_keywords.items():
        if kw in q:
            target_cat = cat
            break

    for _, target, edata in G.out_edges("星辰S14", data=True):
        if edata.get("relation") != "MAY_HAVE_ISSUE":
            continue
        d = G.nodes[target]
        if target_cat and d["category"] != target_cat:
            continue
        repairs = []
        for _, rt, re in G.out_edges(target, data=True):
            if re.get("relation") == "RESOLVED_BY":
                rd = G.nodes[rt]
                repairs.append(f"{rd['name']}({rd['cost']}元)")
        repair_str = f" → 维修：{'、'.join(repairs)}" if repairs else ""
        lines.append(f"{d['name']}（{d['category']}类）{repair_str}")

    return "\n".join(lines) if lines else None


def get_subgraph_data() -> dict:
    """返回完整图谱数据用于前端可视化"""
    G = get_graph()
    nodes = []
    for nid, data in G.nodes(data=True):
        nodes.append({"id": nid, "label": data.get("name", nid), "type": data.get("type", "unknown"), **data})
    edges = []
    for src, tgt, data in G.edges(data=True):
        edges.append({"from": src, "to": tgt, "label": data.get("relation", "")})
    return {"nodes": nodes, "edges": edges}
