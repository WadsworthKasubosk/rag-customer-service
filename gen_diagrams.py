"""Generate ER diagram, KG schema, processing flow, e2e mock screenshot via matplotlib."""
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch, Rectangle
import os

plt.rcParams["font.sans-serif"] = ["Microsoft YaHei", "SimHei"]
plt.rcParams["axes.unicode_minus"] = False

OUT = "thesis_assets"
os.makedirs(OUT, exist_ok=True)


# ============ Figure 3-2: Processing Flow ============
def gen_processing_flow():
    fig, ax = plt.subplots(figsize=(10, 11))
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 14)
    ax.axis("off")

    def box(x, y, w, h, text, color="#E8F1FF", ec="#2E5C8A"):
        ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.08",
                                     fc=color, ec=ec, lw=1.6))
        ax.text(x + w/2, y + h/2, text, ha="center", va="center",
                fontsize=11, wrap=True)

    def arrow(x1, y1, x2, y2):
        ax.add_patch(FancyArrowPatch((x1, y1), (x2, y2),
                                     arrowstyle="-|>", mutation_scale=18,
                                     color="#2E5C8A", lw=1.4))

    box(3.5, 12.6, 3, 0.9, "用户提问", "#FFF4E6", "#D97706")
    arrow(5, 12.6, 5, 12.0)
    box(3.0, 11.0, 4, 0.9, "本地关键词分类\n(< 1ms 不调 LLM)", "#E0F2FE", "#0369A1")
    arrow(5, 11.0, 5, 10.5)
    ax.text(5, 10.25, "并行检索", ha="center", fontsize=11, color="#475569")

    box(0.3, 8.4, 2.8, 1.3, "FAISS\n向量检索", "#DCFCE7", "#15803D")
    box(3.6, 8.4, 2.8, 1.3, "知识图谱\n查询", "#FCE7F3", "#BE185D")
    box(6.9, 8.4, 2.8, 1.3, "MySQL\n实时业务查询", "#FEF3C7", "#A16207")

    arrow(5, 10.1, 1.7, 9.8); arrow(5, 10.1, 5.0, 9.8); arrow(5, 10.1, 8.3, 9.8)
    arrow(1.7, 8.4, 4.0, 7.6); arrow(5.0, 8.4, 5.0, 7.6); arrow(8.3, 8.4, 6.0, 7.6)

    box(2.5, 6.2, 5, 1.4,
        "上下文组装\n结构化知识 → 实时数据 → 参考资料",
        "#EDE9FE", "#6D28D9")
    arrow(5, 6.2, 5, 5.6)
    box(2.5, 4.4, 5, 1.2, "按分类选择 Prompt 模板", "#FEE2E2", "#B91C1C")
    arrow(5, 4.4, 5, 3.8)
    box(2.5, 2.6, 5, 1.2, "LLM 流式生成\n(全流程仅此一次调用)", "#E0E7FF", "#3730A3")
    arrow(5, 2.6, 5, 2.0)
    box(2.5, 0.7, 5, 1.3, "SSE 逐 token 推送到前端", "#FEF3C7", "#A16207")

    plt.tight_layout()
    plt.savefig(f"{OUT}/fig_3_2_flow.png", dpi=180, bbox_inches="tight",
                facecolor="white")
    plt.close()
    print("OK: fig_3_2_flow.png")


# ============ Figure 3-3: ER Diagram ============
def gen_er_diagram():
    fig, ax = plt.subplots(figsize=(14, 9))
    ax.set_xlim(0, 14)
    ax.set_ylim(0, 9)
    ax.axis("off")

    def table(x, y, w, h, name, fields, color="#DBEAFE"):
        ax.add_patch(Rectangle((x, y), w, h, fc=color, ec="#1E40AF", lw=1.6))
        ax.add_patch(Rectangle((x, y + h - 0.5), w, 0.5,
                               fc="#1E40AF", ec="#1E40AF"))
        ax.text(x + w/2, y + h - 0.25, name, ha="center", va="center",
                color="white", fontsize=10, fontweight="bold")
        for i, f in enumerate(fields):
            ax.text(x + 0.15, y + h - 0.85 - i*0.32, f, ha="left",
                    va="center", fontsize=8.5)

    def link(p1, p2, label=""):
        ax.add_patch(FancyArrowPatch(p1, p2, arrowstyle="->",
                                     mutation_scale=14, color="#475569",
                                     lw=1.2, connectionstyle="arc3,rad=0.0"))
        if label:
            ax.text((p1[0]+p2[0])/2, (p1[1]+p2[1])/2 + 0.15, label,
                    fontsize=8, color="#475569", ha="center")

    # Center: products
    table(5.5, 4.5, 3, 3,
          "products",
          ["PK sku_id", "product_name", "current_price",
           "promo_price", "stock_num", "specs_json", "is_on_sale"],
          "#DBEAFE")

    # promotions (above-left)
    table(0.5, 5.5, 3, 2.5,
          "promotions",
          ["PK promo_id", "FK sku_id", "description",
           "discount_rate", "start_date", "end_date"], "#FEF3C7")

    # ecommerce_logistics (left)
    table(0.5, 1.5, 3, 2.6,
          "ecommerce_logistics",
          ["PK order_id", "FK sku_id", "carrier",
           "status", "address", "created_at"], "#DCFCE7")

    # tracking_orders (right)
    table(10.5, 5.0, 3, 2.6,
          "tracking_orders",
          ["PK order_id", "tracking_no", "carrier", "status",
           "items", "created_at", "updated_at"], "#FCE7F3")

    # tracking_events (far right)
    table(10.5, 1.0, 3, 2.6,
          "tracking_events",
          ["PK event_id", "FK order_id", "event_time",
           "location", "event"], "#FCE7F3")

    # repair_tickets (top right)
    table(10.5, 7.8, 3, 1.0,
          "repair_tickets",
          ["PK ticket_id, phone, product, status..."], "#E0E7FF")

    # chat_messages (bottom center)
    table(5.0, 0.5, 3, 1.5,
          "chat_messages",
          ["PK id", "session_id", "role", "content",
           "created_at"], "#F3E8FF")

    # feedback_records (bottom right)
    table(8.5, 0.5, 3, 1.5,
          "feedback_records",
          ["PK id", "session_id", "rating",
           "comment", "resolved", "created_at"], "#FEE2E2")

    # Foreign-key arrows
    link((3.5, 6.5), (5.5, 6.0), "sku_id")
    link((3.5, 2.8), (5.5, 5.0), "sku_id")
    link((11.5, 5.0), (11.5, 3.6), "order_id (1:N)")

    plt.tight_layout()
    plt.savefig(f"{OUT}/fig_3_3_er.png", dpi=180, bbox_inches="tight",
                facecolor="white")
    plt.close()
    print("OK: fig_3_3_er.png")


# ============ Figure 3-4: KG Schema ============
def gen_kg_schema():
    import math
    fig, ax = plt.subplots(figsize=(12, 9))
    ax.set_xlim(-6, 6)
    ax.set_ylim(-5, 5)
    ax.axis("off")

    # central node
    cx, cy = 0, 0
    ax.add_patch(plt.Circle((cx, cy), 0.9, fc="#1E40AF", ec="#1E3A8A", lw=2))
    ax.text(cx, cy, "星辰S14\n(Product)", ha="center", va="center",
            color="white", fontsize=11, fontweight="bold")

    # surrounding nodes (cluster, type, color, relation)
    groups = [
        ("SKU_8+256\n¥3999", "SKU", "#F59E0B", "HAS_SKU"),
        ("SKU_12+256\n¥4299", "SKU", "#F59E0B", "HAS_SKU"),
        ("SKU_16+512\n¥4799", "SKU", "#F59E0B", "HAS_SKU"),
        ("SKU_16+1TB\n¥5299", "SKU", "#F59E0B", "HAS_SKU"),
        ("处理器\n骁龙7Gen3", "Spec", "#10B981", "HAS_SPEC"),
        ("屏幕\n6.7寸OLED", "Spec", "#10B981", "HAS_SPEC"),
        ("电池\n5000mAh", "Spec", "#10B981", "HAS_SPEC"),
        ("双十一促销\n9折", "Promotion", "#8B5CF6", "HAS_PROMOTION"),
        ("屏幕保修\n1年", "Warranty", "#06B6D4", "HAS_WARRANTY"),
        ("电池保修\n1年", "Warranty", "#06B6D4", "HAS_WARRANTY"),
        ("屏幕碎裂\n¥499", "Issue", "#EF4444", "HAS_FAULT"),
        ("电池老化\n¥199", "Issue", "#EF4444", "HAS_FAULT"),
    ]

    n = len(groups)
    R = 3.6
    for i, (label, typ, color, rel) in enumerate(groups):
        ang = 2 * math.pi * i / n - math.pi / 2
        x, y = cx + R * math.cos(ang), cy + R * math.sin(ang)
        ax.add_patch(plt.Circle((x, y), 0.55, fc=color, ec="#374151", lw=1.2))
        ax.text(x, y, label, ha="center", va="center", color="white",
                fontsize=7.5, fontweight="bold")
        ax.plot([cx + 0.85*math.cos(ang), x - 0.55*math.cos(ang)],
                [cy + 0.85*math.sin(ang), y - 0.55*math.sin(ang)],
                color="#6B7280", lw=1.2)
        # relation label at midpoint
        mx, my = cx + (R/2)*math.cos(ang), cy + (R/2)*math.sin(ang)
        ax.text(mx, my, rel, fontsize=7, color="#374151",
                ha="center", va="center",
                bbox=dict(fc="white", ec="none", alpha=0.8, pad=1))

    # legend
    legend_handles = [
        mpatches.Patch(color="#1E40AF", label="Product"),
        mpatches.Patch(color="#F59E0B", label="SKU"),
        mpatches.Patch(color="#10B981", label="Spec"),
        mpatches.Patch(color="#8B5CF6", label="Promotion"),
        mpatches.Patch(color="#06B6D4", label="Warranty"),
        mpatches.Patch(color="#EF4444", label="Issue"),
    ]
    ax.legend(handles=legend_handles, loc="lower right", fontsize=9,
              frameon=True)

    plt.tight_layout()
    plt.savefig(f"{OUT}/fig_3_4_kg_schema.png", dpi=180, bbox_inches="tight",
                facecolor="white")
    plt.close()
    print("OK: fig_3_4_kg_schema.png")


if __name__ == "__main__":
    gen_processing_flow()
    gen_er_diagram()
    gen_kg_schema()
    print("All diagrams generated.")
