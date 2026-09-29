import copy
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from layout_roadmap import analyze_roadmap, layout_roadmap, variant_for_width
from roadmap_visual_spec import RoadmapVisualSpec
import visual_router


def fixture(name="a_simple"):
    return json.loads((ROOT / f"tests/fixtures/roadmap/{name}.json").read_text())


def spec(name="a_simple"):
    request = fixture(name)
    return RoadmapVisualSpec.from_dict({**request["data"], "type": "roadmap", "title": request["title"]})


class RoadmapTests(unittest.TestCase):
    def test_schema_rejects_broken_topology(self):
        base = fixture()["data"]
        changes = [
            (lambda data: data["nodes"][0].update(section="missing"), "Section desconocida"),
            (lambda data: data["nodes"][0].update(importance="critical"), "Importancia"),
            (lambda data: data["main_path"].append(data["main_path"][0]), "repetir"),
            (lambda data: data["branches"][0].update(**{"from": "unknown"}), "Branch.from"),
            (lambda data: data["branches"][0].update(rejoin="variables"), "Branch.rejoin"),
            (lambda data: data["branches"][0].update(nodes=["unknown"]), "Branch.nodes"),
            (lambda data: data["branches"].pop(), "huérfanos"),
        ]
        for change, error in changes:
            with self.subTest(error=error):
                data = copy.deepcopy(base)
                change(data)
                with self.assertRaisesRegex(ValueError, error):
                    RoadmapVisualSpec.from_dict({**data, "type": "roadmap", "title": "Prueba"})

    def test_section_order_packing_and_modes_are_deterministic(self):
        roadmap = spec("c_data_engineering")
        first = layout_roadmap(roadmap, 3)
        self.assertEqual(first, layout_roadmap(roadmap, 3))
        self.assertEqual([section["section"]["id"] for section in first],
                         ["fundamentals", "storage", "pipelines", "scale", "specialize"])
        self.assertTrue(all(len(row) <= 3 for section in first for row in section["rows"]))
        self.assertEqual([branch["kind"] for branch in first[-1]["rows"][0][0]["branches"]],
                         ["optional", "specialization"])
        self.assertEqual([variant_for_width(width)[2] for width in (390, 520, 650, 768, 900, 1100, 1366, 1600)],
                         [1, 1, 2, 2, 3, 4, 4, 5])
        self.assertEqual((analyze_roadmap(roadmap)["node_count"], analyze_roadmap(roadmap)["edge_count"]), (22, 22))

    def test_router_generates_portable_html_and_presentation(self):
        with tempfile.TemporaryDirectory() as folder:
            output = Path(folder) / "generated"
            with patch.object(visual_router, "OUTPUT_DIR", output), patch.object(visual_router, "ROOT", Path(folder)):
                small = visual_router.render_request(visual_router.VisualRequest.from_dict(fixture()))
                medium = visual_router.render_request(visual_router.VisualRequest.from_dict(fixture("b_physics")))
                large = visual_router.render_request(visual_router.VisualRequest.from_dict(fixture("c_data_engineering")))
            self.assertEqual([(item["complexity"], item["preferred_presentation"]) for item in (small, medium, large)],
                             [("small", "inline"), ("medium", "inline"), ("large", "expanded")])
            self.assertEqual(large["renderer"], "native-roadmap")
            html = (Path(folder) / large["presentation_artifact"]).read_text()
            self.assertEqual(html.count('class="roadmap-view'), 5)
            self.assertIn('class="section-map"', html)
            self.assertIn('data-rejoin="quality"', html)
            self.assertIn('ResizeObserver', html)
            self.assertNotIn('https://', html)
            self.assertEqual(large["artifacts"], [large["presentation_artifact"]])

    def test_top_level_shape_and_html_escaping(self):
        request = fixture()
        request.update(request.pop("data"))
        request["title"] = "Ruta <script>alert(1)</script>"
        request["nodes"][0]["title"] = "Variables <img src=x>"
        with tempfile.TemporaryDirectory() as folder:
            output = Path(folder) / "generated"
            with patch.object(visual_router, "OUTPUT_DIR", output), patch.object(visual_router, "ROOT", Path(folder)):
                result = visual_router.render_request(visual_router.VisualRequest.from_dict(request))
            html = (Path(folder) / result["presentation_artifact"]).read_text()
            self.assertIn("Ruta &lt;script&gt;alert(1)&lt;/script&gt;", html)
            self.assertIn("Variables &lt;img src=x&gt;", html)
            self.assertNotIn("<script>alert(1)</script>", html)
        with self.assertRaisesRegex(ValueError, "únicamente output_format html"):
            visual_router.VisualRequest.from_dict({**fixture(), "output_format": "source"})


if __name__ == "__main__":
    unittest.main()
