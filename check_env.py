"""
Pre-flight environment check — 发给对方运行，截图结果即可诊断
用法: python check_env.py
"""

import os
import sys
import socket
import platform
import shutil
import subprocess

# Fix Windows console encoding
if sys.platform == "win32":
    os.system("chcp 65001 >nul 2>&1")
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

os.environ.setdefault("MOCK_RETRIEVAL", "true")

MYSQL_HOST = "127.0.0.1"
MYSQL_PORT = 3306
REDIS_HOST = "127.0.0.1"
REDIS_PORT = 6379

results = []

def ok(name, msg):
    results.append((True, name))
    print(f"  [OK]   {name}: {msg}")

def fail(name, msg):
    results.append((False, name))
    print(f"  [FAIL] {name}: {msg}")

def warn(name, msg):
    results.append((None, name))
    print(f"  [WARN] {name}: {msg}")


# ── 0. System info ──────────────────────────────────────────────────
print(f"\n{'='*55}")
print(f"  RAG Customer Service — 环境检查")
print(f"  {platform.system()} {platform.release()} | Python {platform.python_version()}")
print(f"  {platform.machine()} | CWD: {os.getcwd()}")
print(f"{'='*55}")


# ── 1. OS & Python ──────────────────────────────────────────────────
print("\n--- 1. Python ---")
ver = sys.version_info
if ver >= (3, 9):
    ok("Python 版本", f"{ver.major}.{ver.minor}.{ver.micro}")
else:
    fail("Python 版本", f"{ver.major}.{ver.minor} 太低，需要 >= 3.9")


# ── 2. Docker ────────────────────────────────────────────────────────
print("\n--- 2. Docker ---")
docker_path = shutil.which("docker")
if docker_path:
    try:
        r = subprocess.run(["docker", "info"], capture_output=True, text=True, timeout=10)
        if r.returncode == 0:
            # extract server version
            for line in r.stdout.splitlines():
                if "Server Version" in line:
                    ok("Docker daemon", line.strip())
                    break
            else:
                ok("Docker daemon", "running")
        else:
            fail("Docker daemon", "已安装但未运行 — 请启动 Docker Desktop")
    except Exception as e:
        fail("Docker daemon", str(e))
else:
    fail("Docker", "未安装 — deploy.bat 会自动安装")


# ── 3. Ports ─────────────────────────────────────────────────────────
print("\n--- 3. 端口检测 ---")
for label, host, port in [("MySQL", MYSQL_HOST, MYSQL_PORT), ("Redis", REDIS_HOST, REDIS_PORT)]:
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.settimeout(2)
    err = s.connect_ex((host, port))
    s.close()
    if err == 0:
        ok(f"{label} 端口", f"{host}:{port} 已开放")
    else:
        fail(f"{label} 端口", f"{host}:{port} 未开放 (需要 docker compose up -d)")


# ── 4. MySQL connection ─────────────────────────────────────────────
print("\n--- 4. MySQL 连接 ---")
try:
    import pymysql
    conn = pymysql.connect(
        host=MYSQL_HOST, port=MYSQL_PORT,
        user="rag_user", password="rag_pass",
        database="rag_customer_service",
        connect_timeout=3,
    )
    cur = conn.cursor()
    cur.execute("SELECT VERSION()")
    ver = cur.fetchone()[0]
    cur.execute("SHOW TABLES")
    tables = [r[0] for r in cur.fetchall()]
    conn.close()
    ok("MySQL 查询", f"v{ver}, {len(tables)} 张表")
except ImportError:
    fail("MySQL 查询", "pymysql 未安装 (pip install pymysql)")
except Exception as e:
    fail("MySQL 查询", str(e))


# ── 5. Redis connection ─────────────────────────────────────────────
print("\n--- 5. Redis 连接 ---")
try:
    import redis
    cli = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, db=0,
                      decode_responses=True, socket_connect_timeout=2)
    pong = cli.ping()
    info = cli.info("server")
    ver = info.get("redis_version", "?")
    keys = cli.dbsize()
    cli.close()
    ok("Redis 查询", f"v{ver}, keys={keys}")
except ImportError:
    fail("Redis 查询", "redis 包未安装 (pip install redis)")
except Exception as e:
    fail("Redis 查询", str(e))


# ── 6. Python dependencies ──────────────────────────────────────────
print("\n--- 6. Python 依赖 ---")
REQUIRED = {
    "fastapi": "fastapi",
    "uvicorn": "uvicorn",
    "sqlalchemy": "sqlalchemy",
    "pymysql": "pymysql",
    "redis": "redis",
    "langchain": "langchain",
    "langchain_openai": "langchain-openai",
    "langchain_huggingface": "langchain-huggingface",
    "jinja2": "jinja2",
    "pydantic": "pydantic",
    "openai": "openai",
}
missing = []
for mod, pip_name in REQUIRED.items():
    try:
        __import__(mod)
    except ImportError:
        missing.append(pip_name)

if missing:
    fail("pip 依赖", f"缺少: {', '.join(missing)}")
    print(f"         修复: pip install {' '.join(missing)}")
else:
    ok("pip 依赖", f"全部 {len(REQUIRED)} 个已安装")


# ── 7. FastAPI app import ────────────────────────────────────────────
print("\n--- 7. FastAPI 应用 ---")
try:
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from app.main import app
    routes = [r.path for r in app.routes if hasattr(r, "methods")]
    ok("应用导入", f"{len(routes)} 个路由")
except Exception as e:
    fail("应用导入", str(e))


# ── 8. Disk space ───────────────────────────────────────────────────
print("\n--- 8. 磁盘空间 ---")
try:
    usage = shutil.disk_usage(os.getcwd())
    free_gb = usage.free / (1024**3)
    if free_gb > 2:
        ok("磁盘空间", f"{free_gb:.1f} GB 可用")
    else:
        warn("磁盘空间", f"仅 {free_gb:.1f} GB 可用 (建议 > 2GB)")
except Exception as e:
    warn("磁盘空间", str(e))


# ── Summary ──────────────────────────────────────────────────────────
passed = sum(1 for s, _ in results if s is True)
failed = sum(1 for s, _ in results if s is False)
total  = len(results)

infra_items = {"mysql", "redis", "docker"}
code_ok = all(s is not False for s, n in results
              if not any(k in n.lower() for k in infra_items))

print(f"\n{'='*55}")
print(f"  {passed}/{total} 通过, {failed} 失败")

if failed == 0:
    print(f"  [OK]   一切就绪! 运行: python -m uvicorn app.main:app --port 8000")
elif code_ok:
    print(f"  [!]    代码和依赖没问题，基础设施 (MySQL/Redis/Docker) 未就绪")
    print(f"         运行 deploy.bat 会自动安装并启动一切")
else:
    print(f"  [FAIL] 请修复上面的错误后重试")
    print(f"         或直接运行 deploy.bat 进行自动部署")
print(f"{'='*55}\n")
