"""Wrap rendered visual assets in a portable, standalone HTML page."""

from datetime import datetime, timezone
from html import escape
from pathlib import Path
import base64
import re
import xml.etree.ElementTree as ET


ROOT = Path(__file__).resolve().parents[1]
OUTPUT_DIR = ROOT / "diagrams" / "generated"


def render_artifact(metadata: dict, output_path: Path | None = None) -> dict:
    if not isinstance(metadata, dict) or not isinstance(metadata.get("visuals"), list) or not metadata["visuals"]:
        raise ValueError("metadata debe incluir al menos un visual.")
    output_dir = Path(output_path).parent.resolve() if output_path else OUTPUT_DIR.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    title = _text(metadata.get("title"), "title", required=True)
    parts = ["<!doctype html><html lang=\"es\"><head><meta charset=\"utf-8\"><meta name=\"viewport\" content=\"width=device-width,initial-scale=1\"><meta http-equiv=\"Content-Security-Policy\" content=\"default-src 'none'; style-src 'unsafe-inline'; img-src data:\">"]
    parts += [f"<title>{escape(title)}</title><style>{_CSS}</style></head><body><main><header><h1>{escape(title)}</h1>"]
    for key, tag in (("subtitle", "p"), ("description", "p")):
        value = _text(metadata.get(key), key)
        if value:
            parts.append(f"<{tag} class=\"{key}\">{escape(value)}</{tag}>")
    parts.append("</header>")
    for visual in metadata["visuals"]:
        if not isinstance(visual, dict) or visual.get("kind") not in {"svg", "png"} or not isinstance(visual.get("path"), str):
            raise ValueError("Cada visual requiere kind svg/png y path.")
        asset = (output_dir / visual["path"]).resolve()
        if not asset.is_relative_to(output_dir) or not asset.is_file():
            raise ValueError(f"Asset inexistente o fuera del directorio permitido: {visual['path']}")
        data = asset.read_bytes()
        if visual["kind"] == "svg":
            try:
                root = ET.fromstring(data)
            except ET.ParseError as error:
                raise ValueError("El asset SVG no es válido.") from error
            if root.tag.split("}")[-1] != "svg" or any(node.tag.split("}")[-1] in {"script", "foreignObject"} for node in root.iter()):
                raise ValueError("El asset SVG no es seguro o no contiene un elemento svg.")
            for node in root.iter():
                if any(key.lower().startswith("on") or key.lower().endswith("href") and not value.startswith("#") for key, value in node.attrib.items()):
                    raise ValueError("El asset SVG contiene referencias o eventos no permitidos.")
            content = ET.tostring(root, encoding="unicode")
        else:
            if not data.startswith(b"\x89PNG\r\n\x1a\n"):
                raise ValueError("El asset PNG no es válido.")
            content = f"data:image/png;base64,{base64.b64encode(data).decode('ascii')}"
        parts.append("<figure>")
        if visual["kind"] == "svg":
            alt = escape(_text(visual.get("alt_text"), "alt_text") or _text(visual.get("caption"), "caption") or title)
            parts.append(f"<div class=\"visual\" role=\"img\" aria-label=\"{alt}\">{content}</div>")
        else:
            parts.append(f"<img class=\"visual\" src=\"{content}\" alt=\"{escape(_text(visual.get('alt_text'), 'alt_text') or '')}\">")
        caption = _text(visual.get("caption"), "caption")
        if caption:
            parts.append(f"<figcaption>{escape(caption)}</figcaption>")
        parts.append("</figure>")
    notes = metadata.get("notes", [])
    if not isinstance(notes, list) or any(not isinstance(note, str) for note in notes):
        raise ValueError("notes debe ser una lista de textos.")
    if notes:
        parts.append("<section><h2>Qué mirar</h2><ul>" + "".join(f"<li>{escape(note)}</li>" for note in notes) + "</ul></section>")
    source = metadata.get("source")
    if source:
        if isinstance(source, str):
            source = {"title": source}
        if not isinstance(source, dict):
            raise ValueError("source debe ser texto u objeto.")
        details = [source.get(key) for key in ("title", "chapter", "section", "page") if source.get(key) is not None]
        parts.append(f"<footer>{escape(' · '.join(str(value) for value in details))}</footer>")
    parts.append("</main></body></html>")
    output = Path(output_path) if output_path else output_dir / f"{_slug(title)}-artifact.html"
    if output.resolve().parent != output_dir:
        raise ValueError("El artifact debe guardarse dentro de diagrams/generated/.")
    output.write_text("".join(parts), encoding="utf-8")
    return {"artifact": str(output.relative_to(ROOT)) if ROOT in output.resolve().parents else str(output), "created_at": metadata.get("created_at") or datetime.now(timezone.utc).isoformat()}


def _text(value, name, required=False):
    if value is None and not required:
        return None
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{name} debe ser texto no vacío.")
    return value.strip()


def _slug(value):
    return re.sub(r"[^a-z0-9]+", "-", value.casefold()).strip("-")[:60] or "visual"


_CSS = """
:root{color-scheme:light dark;--bg:#f4f5f7;--card:#fff;--text:#20242b;--muted:#626b78;--line:#e3e6eb}
@media(prefers-color-scheme:dark){:root{--bg:#17191d;--card:#22252b;--text:#edf0f4;--muted:#aeb6c2;--line:#383d46}}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--text);font:16px/1.6 system-ui,sans-serif}main{max-width:960px;margin:clamp(20px,6vw,72px) auto;padding:clamp(20px,5vw,56px);background:var(--card);border:1px solid var(--line);border-radius:18px}h1{line-height:1.2;font-size:clamp(2rem,5vw,3rem)}h2{font-size:1.2rem}.subtitle{font-size:1.25rem;color:var(--muted)}.description,footer,figcaption{color:var(--muted)}figure{margin:32px 0}.visual{display:block;width:100%;height:auto;max-height:75vh;object-fit:contain}.visual svg{width:100%;height:auto}figcaption{margin-top:10px}section{border-top:1px solid var(--line);padding-top:16px}footer{margin-top:28px}
"""
