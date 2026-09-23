from pathlib import Path
import shutil
import sqlite3
import sys


ROOT = Path(__file__).resolve().parent.parent


def main() -> None:
    print(f"[OK] Python {sys.version.split()[0]}")
    try:
        sqlite3.connect(":memory:").close()
        print("[OK] SQLite")
    except sqlite3.Error as error:
        print(f"[ERROR] SQLite: {error}")
        raise SystemExit(1) from error

    for name, path in (
        ("config", ROOT / "config" / "study.example.yaml"),
        ("migrations", ROOT / "migrations"),
    ):
        if path.exists() and (path.is_file() or any(path.glob("*.sql"))):
            print(f"[OK] {name}")
        else:
            print(f"[ERROR] {name} missing or empty")
            raise SystemExit(1)

    if shutil.which("hermes"):
        print("[OK] Hermes installed")
    else:
        print("[INFO] Hermes not installed")


if __name__ == "__main__":
    main()
