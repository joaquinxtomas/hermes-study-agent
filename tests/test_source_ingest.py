import shutil
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import init_db
import source_ingest
import source_store
import study_store


def _write_pdf(path: Path, pages: list[str]) -> None:
    objects = [b"<< /Type /Catalog /Pages 2 0 R >>", b"", b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>"]
    page_refs = []
    for index, text in enumerate(pages):
        page_id, content_id = 4 + index * 2, 5 + index * 2
        page_refs.append(f"{page_id} 0 R".encode("ascii"))
        escaped = text.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")
        stream = f"BT /F1 12 Tf 50 750 Td ({escaped}) Tj ET".encode("ascii")
        objects.extend((
            f"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] "
            f"/Resources << /Font << /F1 3 0 R >> >> /Contents {content_id} 0 R >>".encode("ascii"),
            b"<< /Length " + str(len(stream)).encode("ascii") + b" >>\nstream\n"
            + stream + b"\nendstream",
        ))
    objects[1] = b"<< /Type /Pages /Kids [" + b" ".join(page_refs) + b"] /Count " + str(len(pages)).encode("ascii") + b" >>"

    output = bytearray(b"%PDF-1.4\n")
    offsets = [0]
    for number, obj in enumerate(objects, 1):
        offsets.append(len(output))
        output.extend(f"{number} 0 obj\n".encode("ascii") + obj + b"\nendobj\n")
    xref_offset = len(output)
    output.extend(f"xref\n0 {len(offsets)}\n0000000000 65535 f \n".encode("ascii"))
    for offset in offsets[1:]:
        output.extend(f"{offset:010d} 00000 n \n".encode("ascii"))
    output.extend(
        f"trailer\n<< /Size {len(offsets)} /Root 1 0 R >>\nstartxref\n{xref_offset}\n%%EOF\n".encode("ascii")
    )
    path.write_bytes(output)


@unittest.skipUnless(shutil.which("pdftotext"), "requires Poppler pdftotext")
class SourceIngestTests(unittest.TestCase):
    def test_ingests_page_text_and_replaces_pages_on_reingest(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "repo"
            materials = root / "materials"
            pdf = materials / "fisica" / "guia.pdf"
            pdf.parent.mkdir(parents=True)
            _write_pdf(pdf, ["Unidad dos, conceptos de flujo.", "Ejercicio 8: calcule el flujo electrico."])

            database = Path(directory) / "study.db"
            init_db.initialize_database(database)
            patches = (
                patch.object(study_store, "DATABASE_PATH", database),
                patch.object(source_store, "PROJECT_ROOT", root),
                patch.object(source_store, "MATERIALS_DIR", materials),
                patch.object(source_ingest, "PROJECT_ROOT", root),
                patch.object(source_ingest, "MATERIALS_DIR", materials),
            )
            for item in patches:
                item.start()
                self.addCleanup(item.stop)

            subject = study_store.add_subject("Física II")
            source = source_store.add_source(
                subject["id"], "Guía Unidad 2", "guide", pdf,
            )
            self.assertEqual(source_ingest.ingest_source(source["id"])["pages_ingested"], 2)
            self.assertEqual(source_ingest.ingest_source(source["id"])["pages_ingested"], 2)
            pages = source_store.get_source_pages(source["id"])
            self.assertEqual([page["page_number"] for page in pages], [1, 2])
            self.assertIn("Ejercicio 8", pages[1]["text"])


if __name__ == "__main__":
    unittest.main()
