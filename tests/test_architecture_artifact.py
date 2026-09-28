import json
from pathlib import Path
import shutil
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import render_architecture_artifact
from native_visual_spec import SemanticVisualSpec
import visual_router


def overview():
    return json.loads((ROOT / "tests/fixtures/architecture/study_overview.json").read_text())


class ArchitectureArtifactTests(unittest.TestCase):
    @unittest.skipUnless(shutil.which("dot"), "Graphviz no está instalado")
    def test_architecture_cycle_renders_standalone_html(self):
        request = overview()
        spec = SemanticVisualSpec.from_dict({**request["data"], "type": "architecture", "title": request["title"]})
        self.assertEqual(len(spec.nodes), 8)
        with tempfile.TemporaryDirectory() as folder:
            output_dir = Path(folder) / "generated"
            with patch.object(visual_router, "OUTPUT_DIR", output_dir), patch.object(visual_router, "ROOT", Path(folder)):
                result = visual_router.render_request(visual_router.VisualRequest.from_dict(request))
            html = (Path(folder) / result["presentation_artifact"]).read_text()
            self.assertEqual(result["renderer"], "native-graphviz")
            self.assertEqual((result["node_count"], result["edge_count"]), (8, 11))
            self.assertEqual(result["number_of_levels"], 0)
            self.assertEqual(result["preferred_presentation"], "expanded")
            self.assertEqual(result["artifacts"], [result["presentation_artifact"]])
            self.assertEqual(html.count("<svg "), 2)
            self.assertEqual(html.count("class='card'"), 8)
            self.assertIn('href="#component-1"', html)
            self.assertIn("evidencia citada", html)
            self.assertNotIn("https://fonts.googleapis.com", html)
            self.assertNotIn("<script", html)

    def test_architecture_quality_gate_and_missing_graphviz(self):
        value = overview()
        value["data"]["nodes"] += [{"id": f"extra{i}", "title": f"Extra {i}"} for i in range(5)]
        spec = SemanticVisualSpec.from_dict({**value["data"], "type": "architecture", "title": value["title"]})
        with tempfile.TemporaryDirectory() as folder:
            out = Path(folder) / "map.html"
            with self.assertRaisesRegex(ValueError, "vista general"):
                render_architecture_artifact.render(spec, out, Path(folder))
            self.assertFalse(out.exists())
            small = overview()
            spec = SemanticVisualSpec.from_dict({**small["data"], "type": "architecture", "title": small["title"]})
            with patch.object(render_architecture_artifact.shutil, "which", return_value=None), self.assertRaisesRegex(RuntimeError, "Graphviz"):
                render_architecture_artifact.render(spec, out, Path(folder))
            self.assertFalse(out.exists())

    @unittest.skipUnless(shutil.which("dot"), "Graphviz no está instalado")
    def test_escaped_text_and_source_metadata(self):
        request = overview()
        request["title"] = "Mapa <script>alert(1)</script>"
        request["data"]["nodes"][0]["title"] = "Estudiante <img src=x>"
        request["source"] = {"title": "Guía", "page": 4}
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "safe.html"
            spec = SemanticVisualSpec.from_dict({**request["data"], "type": "architecture", "title": request["title"], "source": request["source"]})
            render_architecture_artifact.render(spec, path, Path(folder))
            html = path.read_text()
            self.assertIn("Mapa &lt;script&gt;alert(1)&lt;/script&gt;", html)
            self.assertIn("Estudiante &lt;img src=x&gt;", html)
            self.assertNotIn("<script>alert(1)</script>", html)
            self.assertIn("Guía · page: 4", html)


if __name__ == "__main__":
    unittest.main()
