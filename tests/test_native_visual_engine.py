import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import layout_flow
import native_visual_spec
import render_native_artifact


def sample():
    return {"type": "flow", "title": "Source Engine",
            "nodes": [{"id": "pdf", "title": "PDF original", "subtitle": "materials/", "role": "input"},
                      {"id": "register", "title": "Registro", "subtitle": "source_cli", "role": "tool"},
                      {"id": "extract", "title": "Extracción", "subtitle": "pdftotext", "role": "process"},
                      {"id": "db", "title": "SQLite", "subtitle": "sources + source_pages", "role": "storage"},
                      {"id": "search", "title": "Búsqueda", "subtitle": "source_search", "role": "tool"},
                      {"id": "answer", "title": "Respuesta grounded", "subtitle": "página + fragmento", "role": "output"}],
            "edges": [{"from": "pdf", "to": "register", "label": "registrar"},
                      {"from": "register", "to": "extract", "label": "extraer"},
                      {"from": "extract", "to": "db", "label": "guardar páginas"},
                      {"from": "db", "to": "search", "label": "buscar"},
                      {"from": "search", "to": "answer", "label": "citar"}],
            "notes": ["Los PDF originales permanecen fuera de SQLite."],
            "source": {"title": "Manual", "chapter": "2", "section": "2.1", "page": 8}}


class NativeVisualTests(unittest.TestCase):
    def test_spec_validates_duplicates_missing_edges_and_cycles(self):
        with self.assertRaisesRegex(ValueError, "duplicado"):
            native_visual_spec.SemanticVisualSpec.from_dict({**sample(), "nodes": [sample()["nodes"][0]] * 2})
        with self.assertRaisesRegex(ValueError, "IDs de nodos"):
            native_visual_spec.SemanticVisualSpec.from_dict({**sample(), "edges": [{"from": "pdf", "to": "missing"}]})
        with self.assertRaisesRegex(ValueError, "acíclicos"):
            native_visual_spec.SemanticVisualSpec.from_dict({**sample(), "edges": [{"from": "pdf", "to": "register"}, {"from": "register", "to": "pdf"}]})

    def test_layout_assigns_linear_and_branching_dag_levels(self):
        linear = native_visual_spec.SemanticVisualSpec.from_dict(sample())
        self.assertEqual([[n["id"] for n in level] for level in layout_flow.flow_layout(linear)],
                         [["pdf"], ["register"], ["extract"], ["db"], ["search"], ["answer"]])
        spec = native_visual_spec.SemanticVisualSpec.from_dict({**sample(), "edges": [
            {"from": "pdf", "to": "register"}, {"from": "register", "to": "extract"},
            {"from": "register", "to": "db"}, {"from": "extract", "to": "search"},
            {"from": "db", "to": "search"}, {"from": "search", "to": "answer"}]})
        levels = layout_flow.flow_layout(spec)
        self.assertEqual([[n["id"] for n in level] for level in levels],
                         [["pdf"], ["register"], ["extract", "db"], ["search"], ["answer"]])

    def test_artifact_is_native_escaped_and_standalone(self):
        with tempfile.TemporaryDirectory() as folder:
            out = Path(folder) / "source.html"
            value = sample()
            value["title"] = "Source <Engine>"
            value["nodes"][0]["title"] = "PDF <script>alert(1)</script>"
            value["edges"][0]["label"] = "</script><img src=x>"
            render_native_artifact.render(value, out, Path(folder))
            html = out.read_text(encoding="utf-8")
            self.assertIn("Source &lt;Engine&gt;", html)
            self.assertIn("PDF &lt;script&gt;alert(1)&lt;/script&gt;", html)
            self.assertIn("\\u003c/script\\u003e\\u003cimg src=x\\u003e", html)
            self.assertNotIn("</script><img", html)
            self.assertIn("<article class='node", html)
            self.assertIn("createElementNS", html)
            self.assertIn("<svg class='links'", html)
            self.assertIn("Los PDF originales", html)
            self.assertIn("Manual · chapter: 2 · section: 2.1 · page: 8", html)
            self.assertNotIn("<script>alert(1)", html)
            self.assertGreater(out.stat().st_size, 1000)

    def test_renderer_rejects_output_outside_allowed_directory(self):
        with tempfile.TemporaryDirectory() as folder:
            with self.assertRaisesRegex(ValueError, "directorio permitido"):
                render_native_artifact.render(sample(), Path(folder) / "outside.html", Path(folder) / "generated")


if __name__ == "__main__":
    unittest.main()
