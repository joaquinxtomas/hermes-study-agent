import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import visual_router


class MathArtifactTests(unittest.TestCase):
    def render(self, kind, data, **fields):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            request = visual_router.VisualRequest.from_dict(
                {"type": kind, "title": "Prueba matemática", "data": data, **fields})
            with patch.object(visual_router, "ROOT", root), patch.object(visual_router, "OUTPUT_DIR", root / "generated"):
                result = visual_router.render_request(request)
            return result, (root / result["presentation_artifact"]).read_text(encoding="utf-8")

    def test_function_uses_sympy_samples_and_native_jsxgraph(self):
        result, html = self.render("function", {"expression": "sin(x)", "domain": [-3, 3]})
        self.assertEqual(result["renderer"], "native-math")
        self.assertEqual(result["presentation_artifact"], result["artifact"])
        self.assertEqual(result["preferred_presentation"], "inline")
        self.assertIn('id="board"', html)
        self.assertIn('resize:{enabled:true,throttle:10}', html)
        self.assertNotIn("const responsiveHost=", html)
        self.assertIn("JXG.JSXGraph.initBoard", html)
        self.assertNotIn('src="http', html)
        self.assertNotIn('href="http', html)
        _, parameterized = self.render("function", {"expression": "a*x^2", "domain": [-3, 3],
                                                     "parameter": {"name": "a", "min": -2, "max": 2, "value": 1}})
        self.assertIn('id="parameter-slider"', parameterized)
        self.assertIn('"frames": [', parameterized)

    def test_geometry_field_and_circuit_are_distinct_native_artifacts(self):
        _, geometry = self.render("geometry", {"elements": [
            {"id": "p", "kind": "point", "at": [1, 2]},
            {"id": "v", "kind": "vector", "from": [0, 0], "to": [2, 3]}]})
        self.assertIn('"kind": "vector"', geometry)
        small_field, field = self.render("vector_field", {"fx": "-y", "fy": "x", "grid": 3})
        self.assertIn('"vectors": [', field)
        self.assertEqual(small_field["preferred_presentation"], "inline")
        dense_field, _ = self.render("vector_field", {"fx": "-y", "fy": "x", "grid": 9})
        self.assertEqual(dense_field["preferred_presentation"], "expanded")
        _, circuit = self.render("circuit", {"elements": [
            {"kind": "resistor", "label": "R"},
            {"kind": "capacitor", "direction": "down", "label": "C"}]})
        self.assertIn('<div class="circuit"', circuit)
        self.assertIn("<svg", circuit)
        self.assertNotIn("JXG.JSXGraph.initBoard", circuit)

    def test_math_labels_and_existing_native_artifacts(self):
        _, html = self.render("coordinate_system", {}, subtitle=r"\(F=ma\)")
        self.assertIn("katex.render", html)
        self.assertIn("MathJax.tex2svgPromise", html)
        _, ordinary = self.render("coordinate_system", {})
        self.assertNotIn("MathJax.tex2svgPromise", ordinary)
        _, flow = self.render("flow", {"nodes": [{"id": "a", "title": r"\(E=mc^2\)"}], "edges": []})
        self.assertIn("katex.render", flow)

    def test_rejects_python_execution_and_invalid_geometry(self):
        with self.assertRaisesRegex(ValueError, "Expresión no soportada"):
            self.render("function", {"expression": "__import__('os').system('true')"})
        with self.assertRaisesRegex(ValueError, "Expresión no soportada"):
            self.render("vector_field", {"fx": "x.__class__", "fy": "y"})
        with self.assertRaisesRegex(ValueError, "duplicado"):
            self.render("geometry", {"elements": [
                {"id": "a", "kind": "point", "at": [0, 0]},
                {"id": "a", "kind": "point", "at": [1, 1]}]})
        with self.assertRaisesRegex(ValueError, "Componente"):
            self.render("circuit", {"elements": [{"kind": "arbitrary_python"}]})


if __name__ == "__main__":
    unittest.main()
