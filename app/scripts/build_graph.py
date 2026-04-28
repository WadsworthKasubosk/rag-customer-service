"""
解析 data/docs/*.txt 构建知识图谱，序列化为 data/kg/graph.pkl
用法: python -m app.scripts.build_graph
"""

import os
import re
import pickle
import networkx as nx

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DOCS_DIR = os.path.join(BASE_DIR, "data", "docs")
KG_DIR = os.path.join(BASE_DIR, "data", "kg")
KG_PATH = os.path.join(KG_DIR, "graph.pkl")


def _read(name: str) -> str:
    with open(os.path.join(DOCS_DIR, name), "r", encoding="utf-8") as f:
        return f.read()


def build_graph() -> nx.DiGraph:
    G = nx.DiGraph()

    # ── 产品节点 ──
    G.add_node("星辰S14", type="Product", name="星辰S14", start_price=3999)
    G.add_node("星辰S14 Pro", type="Product", name="星辰S14 Pro", start_price=4999)

    # ── SKU 节点 + 价格 ──
    skus = {
        "8+256":  {"ram": 8,  "storage": 256,  "price": 3999, "promo_price": 3799},
        "12+256": {"ram": 12, "storage": 256,  "price": 4299, "promo_price": 4099},
        "16+512": {"ram": 16, "storage": 512,  "price": 4599, "promo_price": 4399},
        "16+1TB": {"ram": 16, "storage": 1024, "price": 4999, "promo_price": 4799},
    }
    for sku_id, attrs in skus.items():
        node_id = f"SKU_{sku_id}"
        G.add_node(node_id, type="SKU", name=sku_id, **attrs)
        G.add_edge("星辰S14", node_id, relation="HAS_SKU")

    # ── 颜色节点 ──
    colors = ["星空黑", "月光白", "山岩青", "樱花粉"]
    for c in colors:
        G.add_node(f"Color_{c}", type="Color", name=c)
        for sku_id in skus:
            G.add_edge(f"SKU_{sku_id}", f"Color_{c}", relation="AVAILABLE_IN")

    # ── 库存状态 ──
    _parse_stock(G)

    # ── 规格节点 ──
    specs = [
        ("processor", "天玑9300", "4nm八核, CPU+32%, GPU+34%"),
        ("screen", "6.36英寸AMOLED", "2670×1200, 460PPI, 3000nit, 1-120Hz LTPO, 240Hz触控"),
        ("battery", "4610mAh", "90W有线(46min), 50W无线, 反充"),
        ("camera_rear", "5000万三摄", "主摄f/1.6 OIS + 超广角115° + 长焦75mm OIS"),
        ("camera_front", "3200万前摄", ""),
        ("network", "5G双卡", "WiFi 7, 蓝牙5.4"),
        ("port", "USB Type-C", "USB 3.2 Gen1, 5Gbps"),
        ("size", "152.8×71.5×8.2mm", "193g(玻璃)/188g(纳米皮)"),
        ("waterproof", "IP68", "防尘防水"),
    ]
    for cat, val, detail in specs:
        node_id = f"Spec_{cat}"
        G.add_node(node_id, type="Spec", category=cat, value=val, detail=detail)
        G.add_edge("星辰S14", node_id, relation="HAS_SPEC")

    # ── S14 Pro 规格（对比用） ──
    pro_specs = [
        ("processor", "天玑9300", "同S14"),
        ("screen", "6.73英寸曲面屏", "3200×1440 2K"),
        ("battery", "5000mAh", "120W有线"),
        ("camera_rear", "5000万三摄", "1英寸大底主摄 + 120mm 5倍潜望式长焦"),
        ("body", "陶瓷/素皮", ""),
    ]
    for cat, val, detail in pro_specs:
        node_id = f"ProSpec_{cat}"
        G.add_node(node_id, type="Spec", category=cat, value=val, detail=detail)
        G.add_edge("星辰S14 Pro", node_id, relation="HAS_SPEC")

    # ── 产品对比关系 ──
    G.add_edge("星辰S14", "星辰S14 Pro", relation="COMPARED_WITH")
    G.add_edge("星辰S14 Pro", "星辰S14", relation="COMPARED_WITH")

    # ── 配件节点 ──
    accessories = [
        ("原装90W充电器", 129),
        ("原装Type-C数据线", 49),
        ("官方手机壳(硅胶)", 79),
        ("官方手机壳(皮质)", 149),
        ("官方钢化膜", 39),
        ("原装无线充电器", 199),
        ("Type-C转3.5mm转接线", 39),
    ]
    for name, price in accessories:
        node_id = f"Acc_{name}"
        G.add_node(node_id, type="Accessory", name=name, price=price)
        G.add_edge("星辰S14", node_id, relation="HAS_ACCESSORY")

    # ── 常见故障 + 维修项 ──
    _parse_issues_and_repairs(G)

    # ── 售后政策 ──
    _parse_policies(G)

    # ── 促销活动 ──
    promos = [
        ("限时直降200", "全系列直降200元，截止2025-03-31", "2025-03-31"),
        ("以旧换新", "旧手机最高抵扣1500元", None),
        ("分期免息", "12期免息（银行信用卡及星辰白条）", None),
        ("购机赠品", "赠送原装无线充电器（价值199元）", None),
    ]
    for name, desc, end in promos:
        node_id = f"Promo_{name}"
        attrs = {"type": "Promotion", "name": name, "description": desc}
        if end:
            attrs["end_date"] = end
        G.add_node(node_id, **attrs)
        G.add_edge("星辰S14", node_id, relation="HAS_PROMOTION")

    return G


def _parse_stock(G: nx.DiGraph):
    """解析库存状态"""
    stock_data = {
        "8+256":  {"星空黑": "现货充足", "月光白": "现货充足", "山岩青": "现货充足", "樱花粉": "现货充足"},
        "12+256": {"星空黑": "现货充足", "月光白": "现货充足", "山岩青": "少量库存", "樱花粉": "现货充足"},
        "16+512": {"星空黑": "现货充足", "月光白": "少量库存", "山岩青": "暂时缺货", "樱花粉": "现货充足"},
        "16+1TB": {"星空黑": "少量库存", "月光白": "暂时缺货", "山岩青": "暂时缺货", "樱花粉": "少量库存"},
    }
    restock = {
        ("16+512", "山岩青"): "预计3月底补货",
        ("16+1TB", "月光白"): "预计4月初补货",
        ("16+1TB", "山岩青"): "预计4月初补货",
    }
    for sku, colors in stock_data.items():
        for color, status in colors.items():
            node_id = f"Stock_{sku}_{color}"
            attrs = {"type": "StockStatus", "sku": sku, "color": color, "status": status}
            rs = restock.get((sku, color))
            if rs:
                attrs["restock_date"] = rs
            G.add_node(node_id, **attrs)
            G.add_edge(f"SKU_{sku}", node_id, relation="HAS_STOCK")
            G.add_edge(node_id, f"Color_{color}", relation="FOR_COLOR")


def _parse_issues_and_repairs(G: nx.DiGraph):
    """故障 + 维修项"""
    issues = [
        ("触摸屏失灵", "屏幕"),
        ("屏幕显示异常", "屏幕"),
        ("无法充电", "充电"),
        ("充电速度慢", "充电"),
        ("电池续航短", "电池"),
        ("手机发热", "散热"),
        ("WiFi无法连接", "网络"),
        ("移动数据无法上网", "网络"),
        ("蓝牙连接问题", "网络"),
        ("指纹解锁失败率高", "指纹"),
        ("手机卡顿", "系统"),
        ("无法开机", "系统"),
        ("忘记锁屏密码", "系统"),
        ("相机无法打开", "相机"),
    ]
    for name, cat in issues:
        node_id = f"Issue_{name}"
        G.add_node(node_id, type="Issue", name=name, category=cat)
        G.add_edge("星辰S14", node_id, relation="MAY_HAVE_ISSUE")

    repairs = [
        ("屏幕更换", 699, "官方原装屏幕"),
        ("电池更换", 149, ""),
        ("后盖更换", 199, ""),
        ("主板维修", 899, "899-1299元，视具体故障"),
        ("摄像头模组更换", 399, ""),
    ]
    for name, cost, note in repairs:
        node_id = f"Repair_{name}"
        G.add_node(node_id, type="RepairItem", name=name, cost=cost, note=note)

    # 故障 → 维修项映射
    issue_repair_map = {
        "触摸屏失灵": ["屏幕更换"],
        "屏幕显示异常": ["屏幕更换"],
        "无法充电": ["主板维修"],
        "电池续航短": ["电池更换"],
        "相机无法打开": ["摄像头模组更换"],
    }
    for issue_name, repair_names in issue_repair_map.items():
        for rn in repair_names:
            G.add_edge(f"Issue_{issue_name}", f"Repair_{rn}", relation="RESOLVED_BY")


def _parse_policies(G: nx.DiGraph):
    """售后政策"""
    policies = [
        ("七天无理由退货", "退货", "7天", "签收次日起七日内，商品完好不影响二次销售"),
        ("质量问题退货", "退货", "7天", "非人为损坏性能故障，经检测确认"),
        ("十五日换货", "换货", "15天", "非人为损坏性能故障，同型号同规格"),
        ("主机保修", "保修", "12个月", "产品本身质量问题免费维修"),
        ("电池保修", "保修", "6个月", "电池充电异常等"),
        ("充电器保修", "保修", "6个月", "充电器/数据线"),
    ]
    for name, ptype, duration, conditions in policies:
        node_id = f"Policy_{name}"
        G.add_node(node_id, type="Policy", name=name, policy_type=ptype,
                   duration=duration, conditions=conditions)
        G.add_edge("星辰S14", node_id, relation="COVERED_BY")

    # 不保修情况
    G.add_node("Policy_不保修", type="Policy", name="不在保修范围",
               policy_type="排除", duration="",
               conditions="人为损坏(跌落/进液/挤压)、私自拆机、非原装配件损坏、自然灾害、超保修期、序列号涂改")
    G.add_edge("星辰S14", "Policy_不保修", relation="COVERED_BY")


def main():
    os.makedirs(KG_DIR, exist_ok=True)
    G = build_graph()
    with open(KG_PATH, "wb") as f:
        pickle.dump(G, f)
    print(f"图谱构建完成: {G.number_of_nodes()} 节点, {G.number_of_edges()} 条边")
    # 统计各类型节点
    type_counts = {}
    for _, data in G.nodes(data=True):
        t = data.get("type", "unknown")
        type_counts[t] = type_counts.get(t, 0) + 1
    for t, c in sorted(type_counts.items()):
        print(f"  {t}: {c}")


if __name__ == "__main__":
    main()
