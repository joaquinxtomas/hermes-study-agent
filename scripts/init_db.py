from pathlib import Path
import os
import sqlite3
from contextlib import closing


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
    with closing(sqlite3.connect(database_path)) as connection, connection:
        connection.execute("PRAGMA foreign_keys = ON")
        current_version = connection.execute("PRAGMA user_version").fetchone()[0]
        for migration in migrations:
            try:
                version = int(migration.name.split("_", 1)[0])
            except ValueError as error:
                raise RuntimeError(f"Nombre de migración inválido: {migration.name}") from error
            if version <= current_version:
                continue
            if version != current_version + 1:
                raise RuntimeError(f"Falta la migración {current_version + 1:03d} antes de {migration.name}")

            print(f"Aplicando migración: {migration.name}")
            sql = migration.read_text(encoding="utf-8")
            try:
                connection.executescript(
                    f"BEGIN IMMEDIATE;\n{sql}\n"
                    f"PRAGMA user_version = {version};\nCOMMIT;"
                )
            except sqlite3.Error:
                connection.rollback()
                raise
            current_version = version

    print(f"Base de datos inicializada en: {database_path} (schema {current_version})")


if __name__ == "__main__":
    initialize_database()
