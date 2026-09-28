import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import render_graphviz
import render_architecture_artifact
import render_mermaid
import render_plot
import render_math_artifact
import visual_router
from visual_presentation import choose_presentation


class VisualEngineTests(unittest.TestCase):
    def request(self, kind, data, output_format="source"):
        if kind in {"numeric_data", "study_metrics"} and output_format == "source":
            output_format = "png"
        return visual_router.VisualRequest.from_dict({
            "type": kind, "title": "Prueba visual", "data": data,
            "output_format": output_format,
        })

    def test_visual_request_validation_and_deterministic_routing(self):
        request = self.request("process", {
            "nodes": [{"id": "PDF"}, {"id": "Search"}],
            "edges": [{"from": "PDF", "to": "Search"}],
        })
        self.assertIs(visual_router.RENDERERS[request.type], visual_router.render_native_artifact)
        self.assertIs(visual_router.RENDERERS["architecture"], render_architecture_artifact)
        self.assertIs(visual_router.RENDERERS["dag"], render_graphviz)
        self.assertIs(visual_router.RENDERERS["function"], render_math_artifact)
        self.assertEqual(self.request("process", {"nodes": [{"id": "Legacy"}], "edges": []}).data["nodes"][0]["title"], "Legacy")
        with self.assertRaises(ValueError):
            self.request("physics_geometry", {})
        with self.assertRaises(ValueError):
            self.request("process", {}, "png")

    def test_mermaid_and_graphviz_write_safe_structured_source(self):
        with tempfile.TemporaryDirectory() as folder:
            mermaid_path = Path(folder) / "x.mmd"
            request = self.request("process", {
                "nodes": [{"id": "A", "label": "PDF"}, {"id": "B", "label": "Search"}],
                "edges": [{"from": "A", "to": "B"}],
            })
            with patch.object(render_mermaid, "has_mmdc", return_value=None):
                render_mermaid.render(request, mermaid_path)
            self.assertIn("A[\"PDF\"]", mermaid_path.read_text())
            graph_path = Path(folder) / "x.dot"
            graph = self.request("dag", {"nodes": [{"id": "A"}, {"id": "B"}], "edges": [{"from": "A", "to": "B"}]})
            render_graphviz.render(graph, graph_path)
            self.assertIn("A -> B", graph_path.read_text())

    def test_native_artifact_is_primary_and_mermaid_is_export(self):
        with tempfile.TemporaryDirectory() as folder:
            output_dir = Path(folder) / "generated"

            def fake_mmdc(command, **kwargs):
                Path(command[command.index("-o") + 1]).write_text("<svg />", encoding="utf-8")

            with patch.object(visual_router, "OUTPUT_DIR", output_dir), \
                    patch.object(visual_router, "ROOT", Path(folder)), \
                    patch.object(render_mermaid, "has_mmdc", return_value="/usr/bin/mmdc"), \
                    patch.object(render_mermaid.subprocess, "run", side_effect=fake_mmdc) as run:
                request = self.request("process", {
                    "nodes": [{"id": "A", "label": "Inicio"}], "edges": [],
                }, "svg")
                result = visual_router.render_request(request)

            self.assertEqual(result["artifacts"], [
                "generated/prueba-visual.html", "generated/prueba-visual.mmd",
                "generated/prueba-visual.svg",
            ])
            self.assertEqual(result["technical_asset"], "generated/prueba-visual.svg")
            self.assertEqual(result["presentation_artifact"], "generated/prueba-visual.html")
            self.assertEqual((result["complexity"], result["preferred_presentation"]), ("small", "inline"))
            self.assertEqual(result["visual_type"], "process")
            self.assertTrue((output_dir / "prueba-visual.svg").exists())
            run.assert_called_once()

    def test_failed_optional_svg_render_keeps_the_mmd_source(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "diagram.mmd"
            request = self.request("process", {"nodes": [{"id": "A"}], "edges": []})
            failure = render_mermaid.subprocess.CalledProcessError(1, ["mmdc"], stderr="browser unavailable")
            with patch.object(render_mermaid, "has_mmdc", return_value="/usr/bin/mmdc"), \
                    patch.object(render_mermaid.subprocess, "run", side_effect=failure), \
                    self.assertWarnsRegex(RuntimeWarning, "source guardado"):
                self.assertIsNone(render_mermaid.render(request, path))
            self.assertTrue(path.exists())

    def test_mermaid_sequence_and_input_checks(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "sequence.mmd"
            request = self.request("sequence", {
                "participants": [{"id": "Hermes"}, {"id": "Store"}],
                "messages": [{"from": "Hermes", "to": "Store", "label": "query"}],
            })
            with patch.object(render_mermaid, "has_mmdc", return_value=None):
                render_mermaid.render(request, path)
            self.assertIn("Hermes->>Store: query", path.read_text())
            invalid = self.request("sequence", {"participants": [{"id": "A"}], "messages": [{"from": "B", "to": "A", "label": "x"}]})
            with self.assertRaises(ValueError):
                render_mermaid.render(invalid, Path(folder) / "bad.mmd")

    def test_artifact_names_are_safe_and_do_not_overwrite(self):
        with tempfile.TemporaryDirectory() as folder:
            output_dir = Path(folder)
            with patch.object(visual_router, "OUTPUT_DIR", output_dir), patch.object(visual_router, "ROOT", output_dir.parent), patch.object(render_mermaid, "has_mmdc", return_value=None):
                request = visual_router.VisualRequest.from_dict({
                    "type": "process", "title": "Prueba visual",
                    "data": {"nodes": [{"id": "A", "label": "A"}], "edges": []},
                })
                first = visual_router.render_request(request)
                second = visual_router.render_request(request)
            self.assertNotEqual(first["artifact"], second["artifact"])
            self.assertEqual(len(list(output_dir.iterdir())), 2)

    def test_plot_is_validated_and_missing_matplotlib_is_clear(self):
        request = self.request("numeric_data", {"series": [{"x": [0, 1], "y": [1, 2]}]})
        with patch.dict("sys.modules", {"matplotlib": None, "matplotlib.pyplot": None}):
            with self.assertRaisesRegex(RuntimeError, "Matplotlib no está instalado"):
                render_plot.render(request, Path("unused.png"))
        invalid = self.request("numeric_data", {"series": [{"x": [1], "y": [1, "bad"]}]})
        with self.assertRaisesRegex(ValueError, "pares x/y"):
            render_plot.render(invalid, Path("unused.png"))

    def test_intent_heuristic_does_not_force_unknown_requests(self):
        self.assertEqual(visual_router.classify_visual_intent("Mostrame un gráfico de función"), "function")
        self.assertEqual(visual_router.classify_visual_intent("Explicame la arquitectura"), "architecture")
        self.assertEqual(visual_router.classify_visual_intent("Mostrame un roadmap para estudiar física"), "roadmap")
        self.assertIsNone(visual_router.classify_visual_intent("Explicame el concepto"))

    def test_native_presentation_policy(self):
        def metrics(nodes, edges, levels, width=1, branching=1, groups=0):
            return {"node_count": nodes, "edge_count": edges, "number_of_levels": levels,
                    "max_nodes_per_level": width, "branching_factor": branching,
                    "number_of_groups": groups}

        cases = [
            ("pipeline", metrics(5, 4, 5), "small", "inline"),
            ("architecture", metrics(11, 13, 6, 3, 3, 3), "medium", "expanded"),
            ("architecture", metrics(19, 24, 8, 4, 3, 4), "large", "expanded"),
            ("pipeline", metrics(10, 9, 10), "medium", "inline"),
            ("architecture", metrics(7, 7, 4, 2, 2, 3), "medium", "expanded"),
        ]
        for kind, graph, complexity, presentation in cases:
            with self.subTest(kind=kind, graph=graph):
                decision = choose_presentation(kind, graph)
                self.assertEqual((decision["complexity"], decision["preferred_presentation"]),
                                 (complexity, presentation))

    @unittest.skipUnless(shutil.which("dot"), "Graphviz no está instalado")
    def test_native_router_generates_html_without_desktop_preview(self):
        with tempfile.TemporaryDirectory() as folder:
            output_dir = Path(folder) / "generated"
            with patch.object(visual_router, "OUTPUT_DIR", output_dir), \
                    patch.object(visual_router, "ROOT", Path(folder)):
                result = visual_router.render_request(self.request("architecture", {
                    "nodes": [{"id": str(i), "title": f"Stage {i}"} for i in range(11)],
                    "edges": [{"from": str(i), "to": str(i + 1)} for i in range(10)],
                    "groups": [{"title": "A", "nodes": [str(i) for i in range(4)]},
                               {"title": "B", "nodes": [str(i) for i in range(4, 8)]},
                               {"title": "C", "nodes": [str(i) for i in range(8, 11)]}],
                }, "html"))
            self.assertEqual(result["preferred_presentation"], "expanded")
            self.assertTrue((Path(folder) / result["presentation_artifact"]).is_file())


if __name__ == "__main__":
    unittest.main()
