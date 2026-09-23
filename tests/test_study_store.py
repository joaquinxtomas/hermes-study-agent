import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import init_db
import study_store as store


class StudyStoreTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.database = Path(self.temp_dir.name) / "study.db"
        init_db.initialize_database(self.database)
        self.database_patch = patch.object(store, "DATABASE_PATH", self.database)
        self.database_patch.start()
        self.addCleanup(self.database_patch.stop)
        self.addCleanup(self.temp_dir.cleanup)
        self.subject = store.add_subject("Física II", "problem_solving")

    def test_subject_crud_and_duplicate(self):
        self.assertEqual(store.list_subjects(), [self.subject])
        with self.assertRaises(store.StudyStoreError):
            store.add_subject("Física II")
        disabled = store.set_subject_active(self.subject["id"], False)
        self.assertFalse(disabled["active"])
        self.assertEqual(store.list_subjects(), [])
        self.assertEqual(store.list_subjects(active_only=False), [disabled])

    def test_connection_enables_foreign_keys_and_missing_database_is_clear(self):
        connection = store.get_connection()
        try:
            self.assertEqual(connection.execute("PRAGMA foreign_keys").fetchone()[0], 1)
        finally:
            connection.close()
        with patch.object(store, "DATABASE_PATH", self.database.with_name("missing.db")):
            with self.assertRaisesRegex(store.StudyStoreError, "init_db.py"):
                store.get_connection()

    def test_doubt_filters_state_and_resolution_timestamp(self):
        doubt = store.add_doubt(self.subject["id"], "¿Por qué cambia el flujo?")
        other_subject = store.add_subject("Algoritmos", "programming")
        other_doubt = store.add_doubt(other_subject["id"], "¿Cómo cuesta esta operación?")
        self.assertEqual(store.list_pending_doubts(self.subject["id"]), [doubt])
        self.assertEqual(store.list_pending_doubts(999), [])
        self.assertEqual(store.list_pending_doubts(), [doubt, other_doubt])
        studying = store.update_doubt_status(doubt["id"], "studying")
        self.assertEqual(studying["status"], "studying")
        resolved = store.resolve_doubt(doubt["id"])
        self.assertEqual(resolved["status"], "resolved")
        self.assertTrue(resolved["resolved_at"])

    def test_session_validation_lifecycle_and_checkpoints(self):
        with self.assertRaises(ValueError):
            store.start_session(self.subject["id"], 0, 10)
        with self.assertRaises(ValueError):
            store.start_session(self.subject["id"], 20, 10)

        session = store.start_session(self.subject["id"], 75, 90)
        self.assertEqual(store.get_active_session(self.subject["id"]), session)
        first = store.create_checkpoint(session["id"], current_exercise="7")
        latest = store.create_checkpoint(session["id"], current_exercise="8")
        self.assertEqual(store.get_latest_checkpoint(session["id"]), latest)
        self.assertEqual(store.get_latest_checkpoint_for_subject(self.subject["id"]), latest)
        self.assertNotEqual(first["id"], latest["id"])

        self.assertEqual(store.pause_session(session["id"])["status"], "paused")
        self.assertIsNone(store.get_active_session(self.subject["id"]))
        self.assertEqual(store.resume_session(session["id"])["status"], "active")
        closed = store.close_session(session["id"])
        self.assertEqual(closed["status"], "completed")
        self.assertTrue(closed["ended_at"])
        with self.assertRaises(store.NotFoundError):
            store.close_session(999)


if __name__ == "__main__":
    unittest.main()
