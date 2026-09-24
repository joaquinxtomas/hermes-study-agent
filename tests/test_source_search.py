import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import init_db
import source_search
import source_store
import study_store


class SourceSearchTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        database = Path(self.temp_dir.name) / "study.db"
        init_db.initialize_database(database)
        database_patch = patch.object(study_store, "DATABASE_PATH", database)
        database_patch.start()
        self.addCleanup(database_patch.stop)
        self.addCleanup(self.temp_dir.cleanup)

        self.physics = study_store.add_subject("Física II")
        self.algorithms = study_store.add_subject("Algoritmos")
        self.topic = source_store.add_topic(self.physics["id"], "Flujo eléctrico")
        self.guide = source_store.add_source(
            self.physics["id"], "Guía Unidad 2", "guide",
            "materials/fisica/guides/unidad-2.pdf", topic_id=self.topic["id"],
        )
        self.other = source_store.add_source(
            self.algorithms["id"], "Guía de ejercicios", "guide",
            "materials/algoritmos/ejercicios.pdf",
        )
        source_store.replace_source_pages(self.guide["id"], [
            "Física II. La ley de Gauss relaciona el flujo eléctrico y la carga encerrada.",
            "Ejercicio 8. Calcule el flujo eléctrico a través de una superficie cerrada.",
        ])
        source_store.replace_source_pages(self.other["id"], [
            "Ejercicio 8: calcule la complejidad del algoritmo de búsqueda.",
        ])

    def test_lexical_ranking_and_filters_include_source_and_page(self):
        result = source_search.search_sources("flujo ejercicio 8")
        self.assertEqual(result[0]["source_id"], self.guide["id"])
        self.assertEqual(result[0]["source_title"], "Guía Unidad 2")
        self.assertEqual(result[0]["page_number"], 2)
        self.assertIn("Ejercicio 8", result[0]["snippet"])
        self.assertGreater(result[0]["relevance"], 0)

        self.assertEqual(
            [hit["source_id"] for hit in source_search.search_sources(
                "algoritmo ejercicio 8", source_id=self.other["id"]
            )],
            [self.other["id"]],
        )
        self.assertTrue(all(
            hit["source_id"] == self.guide["id"]
            for hit in source_search.search_sources(
                "flujo", subject_id=self.physics["id"]
            )
        ))
        topic_hits = source_search.search_sources("flujo", topic_id=self.topic["id"])
        self.assertTrue(topic_hits)
        self.assertTrue(all(hit["source_id"] == self.guide["id"] for hit in topic_hits))
        accent_match = source_search.search_sources(
            "fisica electrico", source_id=self.guide["id"]
        )
        self.assertEqual(accent_match[0]["page_number"], 1)
        self.assertIn("Física II", accent_match[0]["snippet"])

    def test_invalid_query_and_limit_fail_clearly(self):
        with self.assertRaises(ValueError):
            source_search.search_sources(" !!! ")
        with self.assertRaises(ValueError):
            source_search.search_sources("ejercicio", limit=0)


if __name__ == "__main__":
    unittest.main()
