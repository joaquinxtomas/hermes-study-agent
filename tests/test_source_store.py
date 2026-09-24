import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import init_db
import source_store
import study_store


class SourceStoreTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        root = Path(self.temp_dir.name) / "repo"
        materials = root / "materials"
        materials.mkdir(parents=True)
        self.database = Path(self.temp_dir.name) / "study.db"
        init_db.initialize_database(self.database)
        patches = (
            patch.object(study_store, "DATABASE_PATH", self.database),
            patch.object(source_store, "PROJECT_ROOT", root),
            patch.object(source_store, "MATERIALS_DIR", materials),
        )
        for item in patches:
            item.start()
            self.addCleanup(item.stop)
        self.addCleanup(self.temp_dir.cleanup)
        self.subject = study_store.add_subject("Física II")
        self.other_subject = study_store.add_subject("Algoritmos")

    def test_topics_sources_and_path_deduplication(self):
        topic = source_store.add_topic(self.subject["id"], "Electrostática")
        child = source_store.add_topic(
            self.subject["id"], "Flujo", parent_topic_id=topic["id"]
        )
        self.assertEqual(child["parent_topic_id"], topic["id"])
        self.assertEqual(len(source_store.list_topics(self.subject["id"])), 2)
        with self.assertRaises(study_store.StudyStoreError):
            source_store.add_topic(
                self.other_subject["id"], "Cruce", parent_topic_id=topic["id"]
            )

        source = source_store.add_source(
            self.subject["id"], "Guía Unidad 2", "guide",
            "materials/fisica/guides/unidad-2.pdf", topic_id=child["id"], author="Cátedra",
        )
        self.assertEqual(source["topic_id"], child["id"])
        self.assertEqual(source["path"], "materials/fisica/guides/unidad-2.pdf")
        self.assertEqual(source_store.get_source_by_id(source["id"]), source)
        self.assertEqual(source_store.find_sources_by_title("unidad 2"), [source])
        self.assertEqual(source_store.list_sources(self.subject["id"]), [source])

        with self.assertRaises(study_store.StudyStoreError):
            source_store.add_source(
                self.other_subject["id"], "Copia", "guide",
                source_store.MATERIALS_DIR / "fisica/guides/unidad-2.pdf",
            )
        inactive = source_store.set_source_active(source["id"], False)
        self.assertFalse(inactive["active"])
        self.assertEqual(source_store.list_sources(), [])

    def test_page_insert_updates_same_page_instead_of_duplicating(self):
        source = source_store.add_source(
            self.subject["id"], "Apunte", "notes", "materials/fisica/apunte.txt"
        )
        source_store.add_source_page(source["id"], 1, "texto inicial")
        source_store.add_source_page(source["id"], 1, "texto actualizado")
        self.assertEqual(source_store.get_source_pages(source["id"]), [{
            "source_id": source["id"],
            "page_number": 1,
            "text": "texto actualizado",
        }])


if __name__ == "__main__":
    unittest.main()
