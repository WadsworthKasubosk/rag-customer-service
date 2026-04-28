"""
RAG Customer Service - Setup (no Docker)
Run: python setup.py
"""
import subprocess
import sys
import os
import shutil

os.chdir(os.path.dirname(os.path.abspath(__file__)))
print(f"\n{'='*50}")
print(f"  RAG Customer Service Setup")
print(f"  Dir: {os.getcwd()}")
print(f"{'='*50}\n")


def run(cmd, desc, shell=True, check=True):
    print(f"  > {cmd}")
    r = subprocess.run(cmd, shell=shell)
    if check and r.returncode != 0:
        print(f"  [FAIL] {desc}")
        return False
    return True


def find_mysql():
    if shutil.which("mysql"):
        return "mysql"
    paths = [
        r"C:\Program Files\MySQL\MySQL Server 8.0\bin\mysql.exe",
        r"C:\Program Files\MySQL\MySQL Server 8.4\bin\mysql.exe",
        r"C:\Program Files\MySQL\MySQL Server 5.7\bin\mysql.exe",
        r"D:\MySQL\bin\mysql.exe",
        r"E:\MySQL\bin\mysql.exe",
        r"C:\mysql\bin\mysql.exe",
        r"D:\Program Files\MySQL\MySQL Server 8.0\bin\mysql.exe",
    ]
    for p in paths:
        if os.path.exists(p):
            print(f"  [OK] Found: {p}")
            return f'"{p}"'
    print("  [!] Cannot find mysql.exe automatically.")
    p = input("  Enter full path to mysql.exe: ").strip().strip('"')
    if os.path.exists(p):
        return f'"{p}"'
    print("  [FAIL] Invalid path")
    return None


# ── Step 1: pip install ──
print("="*50)
print("[1/4] Installing Python packages...")
print("="*50)
run(f"{sys.executable} -m pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple", "pip install requirements.txt")
run(f'{sys.executable} -m pip install "sqlalchemy>=2.0.36" -i https://pypi.tuna.tsinghua.edu.cn/simple', "upgrade sqlalchemy")
print("[OK] Packages done\n")


# ── Step 2: MySQL ──
print("="*50)
print("[2/4] MySQL setup...")
print("="*50)
mc = find_mysql()
if mc:
    sqls = [
        "CREATE DATABASE IF NOT EXISTS rag_customer_service CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci",
        "CREATE USER IF NOT EXISTS 'rag_user'@'localhost' IDENTIFIED BY 'rag_pass'",
        "GRANT ALL PRIVILEGES ON rag_customer_service.* TO 'rag_user'@'localhost'",
        "FLUSH PRIVILEGES",
    ]

    # Try up to 3 times with different passwords
    for attempt in range(3):
        pw = input(f"\n  Enter MySQL root password (Enter if none): ")
        pw_flag = f"-p{pw}" if pw else ""

        # Test connection first
        test = subprocess.run(f'{mc} -u root {pw_flag} -e "SELECT 1;"',
                              shell=True, capture_output=True)
        if test.returncode == 0:
            print("  [OK] MySQL root login success")
            ok = True
            for sql in sqls:
                cmd = f'{mc} -u root {pw_flag} -e "{sql};"'
                if not run(cmd, sql, check=False):
                    ok = False
                    break
            if ok:
                print("[OK] MySQL ready\n")
            else:
                print("[!] MySQL setup had errors. If you set it up manually, press Enter to continue.")
                input()
            break
        else:
            print("  [FAIL] Wrong password, try again" if attempt < 2
                  else "  [FAIL] 3 attempts failed")

    else:
        print("[!] Could not login to MySQL. Set it up manually, then press Enter.")
        print("    Run these SQL commands in MySQL:")
        for sql in sqls:
            print(f"      {sql};")
        input()
else:
    print("[!] Skipping MySQL auto-setup. Set it up manually, then press Enter.")
    input()


# ── Step 3: Init database ──
print("="*50)
print("[3/4] Init database tables...")
print("="*50)
if not run(f"{sys.executable} -m app.scripts.init_db", "init_db"):
    print("[FAIL] Database init failed")
    input("Press Enter to exit...")
    sys.exit(1)
print("[OK] Database ready\n")


# ── Step 4: Start app ──
print("="*50)
print("[4/4] Starting app...")
print("="*50)
print()
print("  Open browser: http://127.0.0.1:8000")
print("  API docs:     http://127.0.0.1:8000/docs")
print("  Press Ctrl+C to stop")
print()
run(f"{sys.executable} -m uvicorn app.main:app --host 0.0.0.0 --port 8000", "uvicorn", check=False)
