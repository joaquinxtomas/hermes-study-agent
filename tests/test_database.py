import sqlite3
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import init_db


class DatabaseTests(unittest.TestCase):
    def test_init_db_creates_schema_and_enforces_foreign_keys(self):
        with tempfile.TemporaryDirectory() as directory:
            database = Path(directory) / "nested" / "study.db"
            init_db.initialize_database(database)

            with sqlite3.connect(database) as connection:
                tables = {
                    row[0]
                    for row in connection.execute(
                        "SELECT name FROM sqlite_master WHERE type = 'table'"
                    )
                }
                self.assertTrue(
                    {"subjects", "doubts", "study_sessions", "checkpoints"}
                    <= tables
                )
                connection.execute("PRAGMA foreign_keys = ON")
                with self.assertRaises(sqlite3.IntegrityError):
                    connection.execute(
                        "INSERT INTO doubts (subject_id, text) VALUES (999, 'test')"
                    )

            init_db.initialize_database(database)


if __name__ == "__main__":
    unittest.main()
