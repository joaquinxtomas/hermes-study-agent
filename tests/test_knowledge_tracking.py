"""Evidence-based topic knowledge tracking."""
import gc
import sys
import sqlite3
from contextlib import closing
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import init_db
import knowledge_rules as rules
import knowledge_store as store
import knowledge_service as service
import source_store
import study_store


class KnowledgeTrackingTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.db = Path(self.temp.name) / "study.db"
        init_db.initialize_database(self.db)
        patcher = patch.object(study_store, "DATABASE_PATH", self.db)
        patcher.start()
        self.addCleanup(patcher.stop)
        self.addCleanup(self._cleanup_temp)
        self.subject = study_store.add_subject("Física II")
        self.topic = source_store.add_topic(self.subject["id"], "Ley de Gauss")
        self.topic_id = self.topic["id"]
        self.assertEqual(len(store.list_knowledge_states(self.topic_id)), 4)

    def _cleanup_temp(self):
        gc.collect()
        self.temp.cleanup()

    def test_initialization_and_unique_topic_dimension(self):
        states = store.initialize_topic_states(self.topic_id)
        self.assertEqual(len(states), 4)
        self.assertEqual({state["status"] for state in states}, {"not_seen"})
        with closing(store.get_connection()) as db, self.assertRaises(sqlite3.IntegrityError):
            db.execute("INSERT INTO knowledge_states (topic_id, dimension, status) VALUES (?, 'conceptual', 'not_seen')", (self.topic_id,))

    def test_explanation_and_guided_do_not_claim_independence(self):
        event = service.record_learning_event(self.topic_id, "conceptual", "explanation", "correct", "Explicó la ley correctamente")
        self.assertEqual((event["previous_status"], event["new_status"]), ("not_seen", "understood"))
        event = service.record_learning_event(self.topic_id, "conceptual", "explanation", "correct", "La explicación fue correcta")
        self.assertEqual(event["new_status"], "understood")
        service.record_learning_event(self.topic_id, "procedural", "guided_exercise", "correct", "Resolvió con una pista")
        self.assertEqual(store.get_knowledge_state(self.topic_id, "procedural")["status"], "practicing")
        self.assertEqual(store.get_knowledge_state(self.topic_id, "independent_problem_solving")["status"], "not_seen")

    def test_independent_correct_and_incorrect_transitions(self):
        event = service.record_learning_event(self.topic_id, "independent_problem_solving", "independent_exercise", "correct", "Resolvió sin ayuda")
        self.assertEqual(event["new_status"], "independent")
        event = service.record_learning_event(self.topic_id, "procedural", "exam_question", "incorrect", "Usó la ecuación de descarga")
        self.assertEqual(event["new_status"], "needs_review")

    def test_review_improves_retention_and_doubt_does_not_downgrade(self):
        store.set_knowledge_state(self.topic_id, "retention", "independent")
        event = service.record_learning_event(self.topic_id, "retention", "review", "correct", "Recordó la relación")
        self.assertEqual(event["new_status"], "understood")
        store.set_knowledge_state(self.topic_id, "conceptual", "understood")
        event = service.record_learning_event(self.topic_id, "conceptual", "doubt", "observed", "Pregunta registrada")
        self.assertEqual(event["new_status"], "understood")

    def test_evidence_links_session_and_doubt(self):
        session = study_store.start_session(self.subject["id"], 20, 30)
        doubt = study_store.add_doubt(self.subject["id"], "¿Qué representa el flujo?", topic_id=self.topic_id)
        event = service.record_learning_event(self.topic_id, "conceptual", "doubt", "observed", "¿Qué representa el flujo?", session["id"], doubt["id"])
        evidence = next(row for row in store.list_evidence(self.topic_id) if row["id"] == event["evidence_id"])
        self.assertEqual(evidence["session_id"], session["id"])
        self.assertEqual(evidence["doubt_id"], doubt["id"])
        self.assertEqual(store.list_evidence_for_session(session["id"])[0]["id"], event["evidence_id"])

    def test_invalid_values_rejected(self):
        for args in (("bad", "correct", "x"), ("conceptual", "bad", "x"), ("conceptual", "explanation", "bad")):
            with self.assertRaises(ValueError):
                service.record_learning_event(self.topic_id, args[0], args[1], args[2], "x")
        with self.assertRaises(ValueError):
            store.set_knowledge_state(self.topic_id, "bad", "introduced")
        with self.assertRaises(ValueError):
            store.set_knowledge_state(self.topic_id, "conceptual", "bad")

    def test_misconception_occurrences_and_resolution(self):
        first = store.add_or_update_misconception(self.topic_id, "Confunde flujo eléctrico con campo eléctrico.")
        again = store.add_or_update_misconception(self.topic_id, " Confunde   flujo eléctrico con campo eléctrico. ")
        self.assertEqual(first["id"], again["id"])
        self.assertEqual(again["occurrences"], 2)
        self.assertEqual(store.resolve_misconception(first["id"])["status"], "resolved")

    def test_transitions_are_deterministic_and_conservative(self):
        self.assertEqual(rules.apply_evidence("independent", "procedural", "independent_exercise", "incorrect"), "practicing")
        self.assertEqual(rules.apply_evidence("introduced", "independent_problem_solving", "guided_exercise", "correct"), "introduced")
        service.record_learning_event(self.topic_id, "procedural", "exam_question", "incorrect", "Confundio las ecuaciones")
        self.assertEqual(store.list_topics_by_status("procedural", "needs_review")[0]["topic_id"], self.topic_id)


if __name__ == "__main__":
    unittest.main()
