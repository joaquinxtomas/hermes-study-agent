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
        other_subject = store.add_subject("Algoritmos", "programming")
        first = store.create_checkpoint(session["id"], current_exercise="7")
        latest = store.create_checkpoint(session["id"], current_exercise="8")
        self.assertEqual(store.get_latest_checkpoint(session["id"]), latest)
        self.assertEqual(store.get_latest_checkpoint_for_subject(self.subject["id"]), latest)
        self.assertNotEqual(first["id"], latest["id"])

        self.assertEqual(store.pause_session(session["id"])["status"], "paused")
        self.assertIsNone(store.get_active_session(self.subject["id"]))
        self.assertEqual(store.get_latest_session("paused")["id"], session["id"])
        other_session = store.start_session(other_subject["id"], 15, 20)
        self.assertEqual(store.get_session(session["id"])["close_reason"], "replaced")
        self.assertIn("checkpoint", store.get_latest_checkpoint(session["id"])["next_action"])
        with self.assertRaisesRegex(store.StudyStoreError, "No se puede reanudar"):
            store.resume_session(session["id"])
        closed = store.close_session(other_session["id"])
        self.assertEqual(closed["status"], "completed")
        self.assertTrue(closed["ended_at"])
        with self.assertRaises(store.NotFoundError):
            store.close_session(999)

    def test_session_timer_excludes_pauses_and_hard_limit_checkpoints_once(self):
        clock = ["2026-01-01T00:00:00+00:00"]
        with patch.object(store, "_now", side_effect=lambda: clock[0]):
            session = store.start_session(self.subject["id"], 1, 2)
            clock[0] = "2026-01-01T00:00:35+00:00"
            paused = store.pause_session(session["id"])
            self.assertEqual(paused["elapsed_seconds"], 35)

            clock[0] = "2026-01-01T00:05:00+00:00"
            timer = store.session_timer(session["id"])
            self.assertEqual(timer["target_remaining_seconds"], 25)
            self.assertIsNone(timer["target_at"])
            store.resume_session(session["id"])

            clock[0] = "2026-01-01T00:05:25+00:00"
            first_target = store.fire_session_timer(session["id"], "target")
            self.assertTrue(first_target["notify"])
            self.assertEqual(first_target["timer"]["elapsed_seconds"], 60)
            duplicate = store.fire_session_timer(session["id"], "target")
            self.assertFalse(duplicate["notify"])
            self.assertEqual(duplicate["reason"], "already_notified")

            clock[0] = "2026-01-01T00:06:25+00:00"
            hard_stop = store.fire_session_timer(session["id"], "hard_limit")
            self.assertTrue(hard_stop["notify"])
            self.assertEqual(hard_stop["timer"]["status"], "paused")
            self.assertEqual(hard_stop["timer"]["elapsed_seconds"], 120)
            self.assertIn("Límite de sesión", hard_stop["checkpoint"]["next_action"])
            self.assertFalse(store.fire_session_timer(session["id"], "hard_limit")["notify"])
            with self.assertRaisesRegex(store.StudyStoreError, "límite máximo"):
                store.resume_session(session["id"])

            next_session = store.start_session(self.subject["id"], 1, 2)
            clock[0] = "2026-01-01T00:08:25+00:00"
            paused_at_limit = store.pause_session(next_session["id"])
            self.assertEqual(paused_at_limit["status"], "paused")
            self.assertTrue(paused_at_limit["hard_limit_notified_at"])
            self.assertIn("Límite de sesión", store.get_latest_checkpoint(next_session["id"])["next_action"])

            last_session = store.start_session(self.subject["id"], 1, 2)
            clock[0] = "2026-01-01T00:10:25+00:00"
            closed_at_limit = store.close_session(last_session["id"])
            self.assertEqual(closed_at_limit["status"], "completed")
            self.assertTrue(closed_at_limit["hard_limit_notified_at"])
            self.assertIsNotNone(store.get_latest_checkpoint(last_session["id"]))

    def test_study_timer_is_independent_and_preserves_remaining_time_on_pause(self):
        clock = ["2026-01-01T00:00:00+00:00"]
        with patch.object(store, "_now", side_effect=lambda: clock[0]):
            session = store.start_session(self.subject["id"], 75, 90)
            timer = store.start_study_timer(session["id"], 2)
            clock[0] = "2026-01-01T00:00:30+00:00"
            self.assertEqual(store.get_current_study_timer(session["id"])["remaining_seconds"], 90)
            paused = store.pause_study_timer(session["id"])
            self.assertEqual(paused["remaining_seconds"], 90)
            self.assertEqual(store.get_session(session["id"])["status"], "active")
            clock[0] = "2026-01-01T00:05:30+00:00"
            self.assertEqual(store.get_current_study_timer(session["id"])["remaining_seconds"], 90)
            store.resume_study_timer(session["id"])
            clock[0] = "2026-01-01T00:05:40+00:00"
            self.assertEqual(store.get_current_study_timer(session["id"])["remaining_seconds"], 80)
            self.assertEqual(store.list_study_timers(session["id"])[0]["id"], timer["id"])


if __name__ == "__main__":
    unittest.main()
