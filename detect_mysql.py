"""
MySQL password detector - try common passwords and config files
Run: python detect_mysql.py
"""
import subprocess
import shutil
import os
import re
import glob

COMMON_PASSWORDS = [
    "",           # no password
    "root",
    "123456",
    "12345678",
    "password",
    "mysql",
    "admin",
    "admin123",
    "root123",
    "123456789",
    "1234",
    "test",
    "000000",
    "111111",
    "toor",
    "abc123",
    "qwerty",
]


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
            return f'"{p}"'
    return None


def try_password(mc, pw):
    pw_flag = f"-p{pw}" if pw else ""
    r = subprocess.run(
        f'{mc} -u root {pw_flag} -e "SELECT 1;"',
        shell=True, capture_output=True, text=True, timeout=5
    )
    return r.returncode == 0


def scan_config_files():
    """Scan common locations for MySQL passwords in config files."""
    found = []
    patterns = [
        os.path.expanduser("~/.my.cnf"),
        r"C:\ProgramData\MySQL\MySQL Server *\my.ini",
        r"C:\Program Files\MySQL\MySQL Server *\my.ini",
        r"D:\MySQL\my.ini",
        r"E:\MySQL\my.ini",
    ]
    # Also scan project directories for .env files
    for drive in ["C:", "D:", "E:"]:
        patterns.append(f"{drive}\\**\\.env")

    config_files = []
    for pat in patterns:
        config_files.extend(glob.glob(pat, recursive=False))

    # Search .env in common project locations
    for base in [os.path.expanduser("~"), "D:\\", "E:\\"]:
        for root, dirs, files in os.walk(base):
            depth = root.replace(base, "").count(os.sep)
            if depth > 2:
                dirs.clear()
                continue
            for f in files:
                if f in (".env", ".env.local", "config.py", "settings.py", "application.yml", "application.properties"):
                    config_files.append(os.path.join(root, f))
            # Skip node_modules, .git etc
            dirs[:] = [d for d in dirs if d not in ("node_modules", ".git", "__pycache__", "venv", ".venv")]

    pw_patterns = [
        r"MYSQL_PASSWORD\s*=\s*['\"]?([^'\"\s]+)",
        r"MYSQL_ROOT_PASSWORD\s*=\s*['\"]?([^'\"\s]+)",
        r"DB_PASSWORD\s*=\s*['\"]?([^'\"\s]+)",
        r"DATABASE_PASSWORD\s*=\s*['\"]?([^'\"\s]+)",
        r"password\s*=\s*['\"]?([^'\"\s]+)",
        r"spring\.datasource\.password\s*=\s*['\"]?([^'\"\s]+)",
    ]

    for f in config_files:
        try:
            with open(f, "r", encoding="utf-8", errors="ignore") as fh:
                content = fh.read()
            for pat in pw_patterns:
                for m in re.finditer(pat, content, re.IGNORECASE):
                    pw = m.group(1).strip("'\"")
                    if pw and pw not in ("your-password", "your_password", "xxx", "***"):
                        found.append((pw, f, m.group(0).strip()))
        except Exception:
            pass

    return found


print(f"\n{'='*50}")
print(f"  MySQL Password Detector")
print(f"{'='*50}\n")

mc = find_mysql()
if not mc:
    print("[FAIL] mysql.exe not found")
    input("Press Enter to exit...")
    exit(1)

print(f"[OK] mysql: {mc}\n")

# Phase 1: Scan config files
print("--- Phase 1: Scanning config files ---")
config_passwords = scan_config_files()
if config_passwords:
    print(f"  Found {len(config_passwords)} password(s) in config files:")
    seen = set()
    for pw, src, line in config_passwords:
        if pw not in seen:
            seen.add(pw)
            print(f"    '{pw}' <- {src}")
            print(f"      ({line})")
    # Add config passwords to front of try list
    extra = [pw for pw, _, _ in config_passwords if pw not in COMMON_PASSWORDS]
    trial_passwords = extra + COMMON_PASSWORDS
else:
    print("  No passwords found in config files")
    trial_passwords = COMMON_PASSWORDS

# Phase 2: Try passwords
print(f"\n--- Phase 2: Trying {len(trial_passwords)} passwords ---")
for pw in trial_passwords:
    display = f"'{pw}'" if pw else "(empty)"
    print(f"  Trying {display}...", end=" ", flush=True)
    try:
        if try_password(mc, pw):
            print("SUCCESS!")
            print(f"\n{'='*50}")
            print(f"  [OK] MySQL root password: {display}")
            print(f"{'='*50}\n")

            # Show existing databases
            pw_flag = f"-p{pw}" if pw else ""
            r = subprocess.run(
                f'{mc} -u root {pw_flag} -e "SHOW DATABASES;"',
                shell=True, capture_output=True, text=True
            )
            if r.returncode == 0:
                print("  Databases:")
                for line in r.stdout.strip().split("\n")[1:]:
                    print(f"    - {line.strip()}")

            # Check if rag database exists
            r2 = subprocess.run(
                f'{mc} -u root {pw_flag} -e "SELECT User,Host FROM mysql.user WHERE User=\'rag_user\';"',
                shell=True, capture_output=True, text=True
            )
            if "rag_user" in (r2.stdout or ""):
                print("\n  [OK] rag_user already exists")
            else:
                print("\n  [!] rag_user not created yet")

            print(f"\n  To use in setup.py, enter this password: {display}")
            input("\nPress Enter to exit...")
            exit(0)
        else:
            print("no")
    except Exception:
        print("error")

print(f"\n[FAIL] None of the {len(trial_passwords)} passwords worked")
print("  Ask the person who installed MySQL for the root password")
input("\nPress Enter to exit...")
