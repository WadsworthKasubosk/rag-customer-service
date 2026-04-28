"""
API smoke test — verify MySQL read/write and Redis cache
Run: python test_api.py
"""
import json
import sys
try:
    from urllib.request import urlopen, Request
    from urllib.error import URLError
except ImportError:
    print("Need Python 3"); sys.exit(1)

BASE = "http://127.0.0.1:8000"
results = []


def test(name, method, path, body=None):
    url = BASE + path
    try:
        if body:
            data = json.dumps(body).encode()
            req = Request(url, data=data, headers={"Content-Type": "application/json"}, method=method)
        else:
            req = Request(url, method=method)
        resp = urlopen(req, timeout=10)
        result = json.loads(resp.read().decode())
        print(f"  [OK]   {name}")
        print(f"         {json.dumps(result, ensure_ascii=False)[:200]}")
        results.append(True)
        return result
    except URLError as e:
        print(f"  [FAIL] {name}: {e}")
        results.append(False)
        return None
    except Exception as e:
        print(f"  [FAIL] {name}: {e}")
        results.append(False)
        return None


print(f"\n{'='*55}")
print(f"  RAG Customer Service API Test")
print(f"{'='*55}")

# ── Health ──
print("\n--- Health ---")
test("Health check", "GET", "/health")

# ── MySQL: Products ──
print("\n--- MySQL: Products ---")
products = test("List products", "GET", "/api/db/products")

items = products.get("data", products) if isinstance(products, dict) else products
if items and isinstance(items, list) and len(items) > 0:
    sku = items[0].get("sku_id") or items[0].get("sku")
    if sku:
        test(f"Get product {sku}", "GET", f"/api/db/product/{sku}")
        test(f"Get stock {sku}", "GET", f"/api/db/stock/{sku}")

# ── MySQL: Repair tickets ──
print("\n--- MySQL: Repair Tickets ---")
test("List tickets", "GET", "/api/repair/list")
ticket = test("Create ticket", "POST", "/api/repair/create", {
    "phone": "13800001111",
    "product": "Test Product",
    "issue": "API smoke test"
})
if ticket and isinstance(ticket, dict):
    ticket = ticket.get("data", ticket) if "data" in ticket else ticket
if ticket and "ticket_id" in ticket:
    tid = ticket["ticket_id"]
    test(f"Get ticket {tid}", "GET", f"/api/repair/{tid}")
    test(f"Update status {tid}", "POST", f"/api/repair/{tid}/status", {"status": "processing"})

# ── MySQL: Logistics ──
print("\n--- MySQL: Logistics ---")
test("List logistics", "GET", "/api/logistics/list")
order = test("Create order", "POST", "/api/logistics/create", {
    "tracking_no": "TEST20260406001",
    "carrier": "Test Express",
    "status": "shipped",
    "items": "Test item x1"
})
if order and isinstance(order, dict):
    order = order.get("data", order) if "data" in order else order
if order and "order_id" in order:
    oid = order["order_id"]
    test(f"Get order {oid}", "GET", f"/api/logistics/{oid}")
    test(f"Track order {oid}", "GET", f"/api/logistics/track/{oid}")

# ── MySQL: Feedback ──
print("\n--- MySQL: Feedback ---")
test("Submit feedback", "POST", "/api/feedback/submit", {
    "session_id": "test-session",
    "rating": 5,
    "comment": "API smoke test"
})
test("Feedback stats", "GET", "/api/feedback/stats")
test("Chat history", "GET", "/api/feedback/history/test-session")

# ── Redis: Cache ──
print("\n--- Redis: Cache ---")
test("Cache stats", "GET", "/api/db/cache/stats")

# ── Knowledge base ──
print("\n--- Knowledge Base ---")
test("KB status", "GET", "/api/knowledge/status")

# ── Knowledge Graph ──
print("\n--- Knowledge Graph ---")
test("Graph stats", "GET", "/api/graph/stats")

# ── Demo data ──
print("\n--- Demo ---")
test("Demo status", "GET", "/api/demo/status")

# ── Summary ──
passed = sum(results)
total = len(results)
print(f"\n{'='*55}")
print(f"  {passed}/{total} tests passed")
if all(results):
    print(f"  [OK]   All API endpoints working!")
else:
    failed = total - passed
    print(f"  [!]    {failed} test(s) failed")
print(f"{'='*55}\n")
