"""Extract PDF page text with the locally installed Poppler pdftotext command."""

from pathlib import Path
import shutil
import subprocess

import source_store
import study_store


PROJECT_ROOT = Path(__file__).resolve().parent.parent
MATERIALS_DIR = PROJECT_ROOT / "materials"


def ingest_source(source_id: int) -> dict:
    source = source_store.get_source_by_id(source_id)
    if source is None:
        raise study_store.NotFoundError(f"No existe la fuente {source_id}.")

    path = (PROJECT_ROOT / source["path"]).resolve()
    if not path.is_relative_to(MATERIALS_DIR.resolve()):
        raise ValueError("El archivo de la fuente debe estar dentro de materials/.")
    if not path.is_file():
        raise FileNotFoundError(f"No se encuentra el archivo de la fuente: {path}")
    if path.suffix.casefold() != ".pdf":
        raise ValueError(f"La fuente registrada no es un PDF: {source['path']}")

    pdftotext = shutil.which("pdftotext")
    if pdftotext is None:
        raise RuntimeError("Falta pdftotext (Poppler); instálalo para ingerir PDFs.")
    try:
        result = subprocess.run(
            [pdftotext, "-enc", "UTF-8", "-layout", str(path), "-"],
            check=True,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=120,
        )
    except subprocess.CalledProcessError as error:
        detail = (error.stderr or "").strip()[:500]
        raise RuntimeError(f"pdftotext no pudo extraer {source['path']}: {detail}") from error
    except subprocess.TimeoutExpired as error:
        raise RuntimeError(f"La extracción del PDF excedió 120 segundos: {source['path']}") from error

    pages = result.stdout.split("\f")
    if pages and not pages[-1].strip():
        pages.pop()
    if not any(page.strip() for page in pages):
        raise RuntimeError(
            f"No se extrajo texto de {source['path']}; PDFs escaneados requieren OCR, no implementado."
        )
    source_store.replace_source_pages(source_id, [page.strip() for page in pages])
    return {"source_id": source_id, "pages_ingested": len(pages)}
