"""
基于关键词规则的意图分类器
零延迟，不调用 LLM，将分类结果用于路由到不同的 Prompt 和处理逻辑
"""

import re

_RULES: dict[str, list[str]] = {
    "repair_track": [
        "维修进度", "工单", "修好了吗", "维修状态", "返修进度",
        "送修", "维修单", "取件", "修理进度", "维修记录",
        "报修", "返修", "维修查询", "工单状态", "工单号",
    ],
    "logistics_track": [
        "物流查询", "到哪了", "快递单号", "发货了吗", "物流进度",
        "快递进度", "运单", "物流状态", "派送", "订单状态",
        "订单查询", "快递查询", "物流信息", "运输状态", "配送进度",
        "订单号", "单号", "发到哪", "签收", "到了吗",
    ],
    "after_sales": [
        "退货", "换货", "退款", "退换", "保修", "维修", "售后",
        "故障", "坏了", "损坏", "不工作", "修理", "返修",
        "投诉", "质量问题", "保修期", "三包", "召回",
    ],
    "ecommerce": [
        "价格", "多少钱", "优惠", "打折", "促销", "券", "满减",
        "物流", "快递", "发货", "到货", "运费", "配送",
        "库存", "有货", "缺货", "预售", "补货", "现货",
        "规格", "参数", "尺寸", "重量", "颜色", "型号", "对比",
    ],
    "product_qa": [
        "怎么用", "如何使用", "操作", "步骤", "教程", "说明书",
        "功能", "特点", "支持", "兼容", "连接", "设置",
        "注意事项", "安装", "配置", "升级", "更新",
    ],
}

# Order/ticket ID patterns → auto-classify
_ID_PATTERNS = [
    (re.compile(r"DD\d{8,}", re.IGNORECASE), "logistics_track"),   # DD20260320001
    (re.compile(r"SF\d{8,}", re.IGNORECASE), "logistics_track"),   # SF1234567890
    (re.compile(r"YT\d{8,}", re.IGNORECASE), "logistics_track"),   # YT9876543210
    (re.compile(r"JD\d{8,}", re.IGNORECASE), "logistics_track"),   # JD0011223344
    (re.compile(r"KD\d{8,}", re.IGNORECASE), "logistics_track"),   # KD...
    (re.compile(r"ORD\d{8,}", re.IGNORECASE), "logistics_track"),  # ORD20260315001
    (re.compile(r"WX\d{8,}", re.IGNORECASE), "repair_track"),      # WX20260320001
]


def classify_question(question: str) -> str:
    """
    基于关键词匹配 + 订单号/工单号模式识别进行意图分类
    返回: product_qa / after_sales / ecommerce / logistics_track / repair_track / other
    """
    question_clean = question.lower().strip()

    # Phase 1: ID pattern match (highest priority)
    for pattern, category in _ID_PATTERNS:
        if pattern.search(question):
            return category

    # Phase 2: keyword match
    scores = {}
    for category, keywords in _RULES.items():
        score = sum(1 for kw in keywords if kw in question_clean)
        if score > 0:
            scores[category] = score

    if not scores:
        return "other"

    return max(scores, key=scores.get)
