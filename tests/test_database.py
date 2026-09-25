import sqlite3
from contextlib import closing
import tempfile
import unittest
from pathlib import Path

import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import init_db


class DatabaseTests(unittest.TestCase):
    def test_init_db_creates_schema_and_enforces_foreign_keys(self):
        with tempfile.TemporaryDirectory() as directory:
            database = Path(directory) / "nested" / "study.db"
            init_db.initialize_database(database)

            with closing(sqlite3.connect(database)) as connection, connection:
                tables = {
                    row[0]
                    for row in connection.execute(
                        "SELECT name FROM sqlite_master WHERE type = 'table'"
                    )
                }
                self.assertTrue(
                    {
                        "subjects", "doubts", "study_sessions", "checkpoints",
                        "topics", "sources", "source_pages", "knowledge_states",
                        "knowledge_evidence", "misconceptions",
                    }
                    <= tables
                )
                self.assertEqual(connection.execute("PRAGMA user_version").fetchone()[0], 3)
                doubt_columns = {
                    row[1] for row in connection.execute("PRAGMA table_info(doubts)")
                }
                self.assertIn("topic_id", doubt_columns)
                connection.execute("PRAGMA foreign_keys = ON")
                with self.assertRaises(sqlite3.IntegrityError):
                    connection.execute(
                        "INSERT INTO doubts (subject_id, text) VALUES (999, 'test')"
                    )

            init_db.initialize_database(database)

    def test_existing_foundation_database_upgrades_and_migrations_are_repeatable(self):
        with tempfile.TemporaryDirectory() as directory:
            database = Path(directory) / "legacy.db"
            connection = sqlite3.connect(database)
            connection.executescript(
                (Path(__file__).resolve().parents[1] / "migrations" / "001_initial_schema.sql")
                .read_text(encoding="utf-8")
            )
            connection.close()

            init_db.initialize_database(database)
            init_db.initialize_database(database)
            with closing(sqlite3.connect(database)) as connection, connection:
                self.assertEqual(connection.execute("PRAGMA user_version").fetchone()[0], 3)
                self.assertEqual(
                    sum(row[1] == "topic_id" for row in connection.execute("PRAGMA table_info(doubts)")),
                    1,
                )


if __name__ == "__main__":
    unittest.main()
