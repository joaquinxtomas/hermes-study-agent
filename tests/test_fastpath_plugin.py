import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "hermes_plugins"))

import init_db
import study_store
from study_fastpath import _handler, _timer_command, register


class FakeContext:
    def __init__(self):
        self.tools = {}

    def register_tool(self, **kwargs):
        self.tools[kwargs["name"]] = kwargs

    def register_command(self, *args, **kwargs):
        self.command = (args, kwargs)


class FastPathTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.database = Path(self.temp_dir.name) / "study.db"
        init_db.initialize_database(self.database)
        self.database_patch = patch.object(study_store, "DATABASE_PATH", self.database)
        self.database_patch.start()
        self.addCleanup(self.database_patch.stop)
        self.addCleanup(self.temp_dir.cleanup)
        self.subject = study_store.add_subject("Física", "problem_solving")
        self.clear_audit_env = patch.dict(os.environ, {"HERMES_LATENCY": "0"})
        self.clear_audit_env.start()
        self.addCleanup(self.clear_audit_env.stop)

    def call_tool(self, name, **args):
        return json.loads(_handler(name)(args))

    def test_registers_seven_small_explicit_tools(self):
        context = FakeContext()
        register(context)
        self.assertEqual(set(context.tools), {
            "study_timer_start", "study_timer_pause", "study_timer_resume", "study_timer_stop",
            "study_session_start", "study_session_end", "study_session_status",
        })
        self.assertEqual(context.command[0][0], "study-timer")
        self.assertIn("minutos", context.command[1]["args_hint"])
        self.assertIn("Do not use cron", context.tools["study_timer_start"]["schema"]["description"])

    def test_direct_timer_command_starts_without_a_model_tool_loop(self):
        result = json.loads(_timer_command("2m"))
        self.assertTrue(result["ok"])
        self.assertEqual(result["timer"]["duration_seconds"], 120)

    def test_timer_rounds_share_session_and_do_not_close_it(self):
        invalid = self.call_tool("study_timer_start", duration_minutes=0, subject="Física")
        self.assertFalse(invalid["ok"])
        self.assertIsNone(study_store.get_latest_session())

        started = self.call_tool("study_timer_start", duration_minutes=25, subject="Física")
        session_id = started["timer"]["session_id"]
        self.assertTrue(started["ok"])
        self.assertEqual(started["session"]["status"], "active")
        self.assertEqual(started["session"]["hard_limit_minutes"], 90)
        self.assertEqual(started["timer"]["status"], "running")

        duplicate = self.call_tool("study_timer_start", duration_minutes=5, subject="Física")
        self.assertFalse(duplicate["ok"])
        self.assertEqual(study_store.get_latest_session()["id"], session_id)

        paused = self.call_tool("study_timer_pause")
        self.assertTrue(paused["ok"])
        self.assertEqual(paused["session"]["status"], "active")
        self.assertEqual(paused["timer"]["status"], "paused")
        resumed = self.call_tool("study_timer_resume")
        self.assertTrue(resumed["ok"])
        self.assertEqual(resumed["timer"]["status"], "running")
        stopped = self.call_tool("study_timer_stop")
        self.assertTrue(stopped["ok"])
        self.assertEqual(stopped["session"]["status"], "active")
        self.assertEqual(stopped["timer"]["status"], "cancelled")

        second = self.call_tool("study_timer_start", duration_minutes=10, subject="Física")
        self.assertTrue(second["ok"])
        self.assertEqual(second["session"]["id"], session_id)
        self.assertEqual(len(second["timers"]), 2)
        self.assertEqual(study_store.get_active_session()["id"], session_id)

    def test_no_active_or_paused_timer_returns_clear_error(self):
        self.assertIn("No hay un timer activo", self.call_tool("study_timer_pause")["error"])
        self.assertIn("No hay un timer pausado", self.call_tool("study_timer_resume")["error"])
        self.assertIn("No existe la sesión", self.call_tool("study_session_status", session_id=999)["error"])

    def test_timer_infers_the_only_active_subject_but_rejects_ambiguity(self):
        inferred = self.call_tool("study_timer_start", duration_minutes=4)
        self.assertTrue(inferred["ok"])
        self.assertEqual(inferred["session"]["subject_id"], self.subject["id"])
        self.call_tool("study_timer_stop")
        self.call_tool("study_session_end")
        study_store.add_subject("Algoritmos", "programming")
        ambiguous = self.call_tool("study_timer_start", duration_minutes=4)
        self.assertFalse(ambiguous["ok"])
        self.assertIn("Indicá la materia", ambiguous["error"])

    def test_session_defaults_topic_status_and_end(self):
        started = self.call_tool("study_session_start", subject="Física", topic="Ley de Gauss")
        self.assertTrue(started["ok"])
        self.assertEqual(started["session"]["target_minutes"], 75)
        self.assertEqual(started["session"]["hard_limit_minutes"], 90)
        self.assertEqual(study_store.get_latest_checkpoint(started["session"]["id"])["current_topic"],
                         "Ley de Gauss")
        status = self.call_tool("study_session_status")
        self.assertEqual(status["session"]["id"], started["session"]["id"])
        ended = self.call_tool("study_session_end")
        self.assertTrue(ended["ok"])
        self.assertEqual(ended["session"]["status"], "completed")

    def test_starting_new_session_checkpoints_and_replaces_the_open_one(self):
        first = self.call_tool("study_session_start", subject="Física", topic="Campo eléctrico")
        second = self.call_tool("study_session_start", subject="Física", topic="Ley de Gauss")
        self.assertNotEqual(first["session"]["id"], second["session"]["id"])
        closed = study_store.get_session(first["session"]["id"])
        self.assertEqual(closed["status"], "cancelled")
        self.assertEqual(closed["close_reason"], "replaced")
        self.assertIn("checkpoint", study_store.get_latest_checkpoint(closed["id"])["next_action"])


if __name__ == "__main__":
    unittest.main()
