"""
Download and start Redis for Windows (portable, no install needed)
Run: python install_redis.py
"""
import os
import sys
import zipfile
import subprocess
import urllib.request
import socket

REDIS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "redis-win")
REDIS_EXE = os.path.join(REDIS_DIR, "redis-server.exe")

# tporadowski Redis 5.0.14.1 for Windows (portable zip)
URLS = [
    "https://github.com/tporadowski/redis/releases/download/v5.0.14.1/Redis-x64-5.0.14.1.zip",
    "https://ghfast.top/https://github.com/tporadowski/redis/releases/download/v5.0.14.1/Redis-x64-5.0.14.1.zip",
    "https://gh-proxy.com/https://github.com/tporadowski/redis/releases/download/v5.0.14.1/Redis-x64-5.0.14.1.zip",
]


def port_open(port=6379):
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.settimeout(1)
    r = s.connect_ex(("127.0.0.1", port))
    s.close()
    return r == 0


def download_redis():
    if os.path.exists(REDIS_EXE):
        print(f"[OK] Redis already downloaded: {REDIS_EXE}")
        return True

    os.makedirs(REDIS_DIR, exist_ok=True)
    zip_path = os.path.join(REDIS_DIR, "redis.zip")

    for url in URLS:
        print(f"  Downloading from: {url[:60]}...")
        try:
            urllib.request.urlretrieve(url, zip_path)
            print(f"  [OK] Downloaded")
            break
        except Exception as e:
            print(f"  [FAIL] {e}")
            continue
    else:
        print("\n[FAIL] All download URLs failed.")
        print("  Please manually download Redis for Windows:")
        print("  https://github.com/tporadowski/redis/releases")
        print(f"  Extract to: {REDIS_DIR}")
        return False

    # Extract
    print("  Extracting...")
    with zipfile.ZipFile(zip_path, "r") as zf:
        zf.extractall(REDIS_DIR)
    os.remove(zip_path)

    if not os.path.exists(REDIS_EXE):
        # might be in a subfolder
        for root, dirs, files in os.walk(REDIS_DIR):
            for f in files:
                if f == "redis-server.exe":
                    # move all files to REDIS_DIR
                    import shutil
                    for item in os.listdir(root):
                        src = os.path.join(root, item)
                        dst = os.path.join(REDIS_DIR, item)
                        if not os.path.exists(dst):
                            shutil.move(src, dst)
                    break

    if os.path.exists(REDIS_EXE):
        print(f"  [OK] Extracted to {REDIS_DIR}")
        return True
    else:
        print(f"  [FAIL] redis-server.exe not found after extraction")
        return False


def start_redis():
    if port_open():
        print("[OK] Redis already running on :6379")
        return True

    if not os.path.exists(REDIS_EXE):
        print("[FAIL] redis-server.exe not found")
        return False

    print("  Starting Redis...")
    subprocess.Popen(
        [REDIS_EXE, "--port", "6379", "--appendonly", "yes"],
        cwd=REDIS_DIR,
        creationflags=subprocess.CREATE_NEW_CONSOLE if sys.platform == "win32" else 0,
    )

    import time
    for i in range(10):
        time.sleep(1)
        if port_open():
            print("[OK] Redis started on :6379")
            return True
        print("  waiting...", end=" ", flush=True)

    print("\n[FAIL] Redis did not start")
    return False


if __name__ == "__main__":
    print(f"\n{'='*50}")
    print(f"  Redis for Windows - Portable Install")
    print(f"{'='*50}\n")

    if port_open():
        print("[OK] Redis already running on :6379, nothing to do!")
    else:
        if download_redis():
            start_redis()

    print()
    input("Press Enter to exit...")
