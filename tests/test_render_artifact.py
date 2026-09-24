import base64
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import render_artifact


class ArtifactTests(unittest.TestCase):
    def test_standalone_html_escapes_metadata_and_embeds_assets(self):
        with tempfile.TemporaryDirectory() as folder:
            directory = Path(folder)
            (directory / "diagram.svg").write_text('<svg xmlns="http://www.w3.org/2000/svg"><text>ok</text></svg>', encoding="utf-8")
            (directory / "plot.png").write_bytes(b"\x89PNG\r\n\x1a\nsmall")
            output = directory / "out.html"
            render_artifact.render_artifact({
                "title": "A < B", "subtitle": "Sub", "description": "Description",
                "visuals": [
                    {"kind": "svg", "path": "diagram.svg", "caption": "Diagram"},
                    {"kind": "png", "path": "plot.png", "alt_text": "plot"},
                ],
                "notes": ["note"], "source": {"title": "Book", "chapter": "2", "page": 7},
            }, output)
            html = output.read_text(encoding="utf-8")
            self.assertIn("A &lt; B", html)
            self.assertIn("Sub", html)
            self.assertIn("Diagram", html)
            self.assertIn("data:image/png;base64," + base64.b64encode(b"\x89PNG\r\n\x1a\nsmall").decode(), html)
            self.assertIn("Book · 2 · 7", html)
            self.assertIn("note", html)
            self.assertNotIn("<script", html)

    def test_rejects_paths_outside_directory_and_invalid_svg(self):
        with tempfile.TemporaryDirectory() as folder:
            directory = Path(folder) / "generated"
            directory.mkdir()
            output = directory / "out.html"
            with self.assertRaisesRegex(ValueError, "fuera"):
                render_artifact.render_artifact({"title": "x", "visuals": [{"kind": "svg", "path": "../secret.svg"}]}, output)
            (directory / "bad.svg").write_text('<svg><script>bad</script></svg>', encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "no es seguro"):
                render_artifact.render_artifact({"title": "x", "visuals": [{"kind": "svg", "path": "bad.svg"}]}, output)


if __name__ == "__main__":
    unittest.main()
