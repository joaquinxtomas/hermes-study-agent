from pathlib import Path
import os
import sqlite3


PROJECT_ROOT = Path(__file__).resolve().parent.parent
MIGRATIONS_DIR = PROJECT_ROOT / "migrations"
STORAGE_DIR = PROJECT_ROOT / "storage"
DATABASE_PATH = STORAGE_DIR / "study.db"


def initialize_database(database_path: Path | None = None) -> None:
    if database_path is None:
        database_path = Path(os.environ.get("STUDY_DB_PATH", DATABASE_PATH))
    else:
        database_path = Path(database_path)
    migrations = sorted(MIGRATIONS_DIR.glob("*.sql"))
    if not migrations:
        raise RuntimeError(f"No se encontraron migraciones en: {MIGRATIONS_DIR}")

    database_path.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(database_path) as connection:
        connection.execute("PRAGMA foreign_keys = ON")
        for migration in migrations:
            print(f"Aplicando migración: {migration.name}")
            connection.executescript(migration.read_text(encoding="utf-8"))

    print(f"Base de datos inicializada en: {database_path}")


if __name__ == "__main__":
    initialize_database()
