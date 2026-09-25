"""Validate visual requests and route them to a local renderer."""

from dataclasses import dataclass
import json
from pathlib import Path
import re
import sys

import render_graphviz
import render_mermaid
import render_plot
import render_artifact
import render_native_artifact
from native_visual_spec import SemanticVisualSpec

ROOT = Path(__file__).resolve().parents[1]
OUTPUT_DIR = ROOT / "diagrams" / "generated"
RENDERERS = {
    "flow": render_native_artifact,
    "process": render_native_artifact,
    "architecture": render_native_artifact,
    "pipeline": render_native_artifact,
    "sequence": render_mermaid,
    "tree": render_graphviz,
    "graph": render_graphviz,
    "dag": render_graphviz,
    "function": render_plot,
    "numeric_data": render_plot,
    "study_metrics": render_plot,
}


@dataclass(frozen=True)
class VisualRequest:
    type: str
    title: str
    data: dict
    output_format: str = "source"
    subject: str | None = None
    topic: str | None = None
    source: str | dict | None = None
    subtitle: str | None = None
    description: str | None = None
    notes: list | None = None

    @classmethod
    def from_dict(cls, value: dict) -> "VisualRequest":
        if not isinstance(value, dict):
            raise ValueError("La solicitud visual debe ser un objeto JSON.")
        kind, title, data = value.get("type"), value.get("title"), value.get("data")
        if not isinstance(kind, str) or kind not in RENDERERS:
            raise ValueError(f"Tipo visual no soportado: {kind!r}.")
        if not isinstance(title, str) or not title.strip() or len(title) > 160:
            raise ValueError("title debe ser texto de 1 a 160 caracteres.")
        if not isinstance(data, dict) or len(json.dumps(data, ensure_ascii=False)) > 200_000:
            raise ValueError("data debe ser un objeto JSON de hasta 200 KB.")
        output_format = value.get("output_format", "png" if kind in {"function", "numeric_data", "study_metrics"} else "source")
        if not isinstance(output_format, str) or output_format not in {"source", "svg", "png", "html"}:
            raise ValueError("output_format debe ser source, svg, png o html.")
        if kind in {"flow", "process", "architecture", "pipeline"} and output_format not in {"source", "svg", "html"}:
            raise ValueError("El renderer nativo admite html; source/svg quedan disponibles para exportación Mermaid.")
        if kind == "sequence" and output_format not in {"source", "svg"}:
            raise ValueError("Mermaid admite output_format source o svg.")
        if kind in {"tree", "graph", "dag"} and output_format not in {"source", "png"}:
            raise ValueError("Graphviz admite output_format source o png.")
        if kind in {"function", "numeric_data", "study_metrics"} and output_format != "png":
            raise ValueError("Matplotlib admite output_format png.")
        if kind in {"flow", "process", "architecture", "pipeline"}:
            data = {**data, "type": kind, "title": title.strip()}
            for node in data.get("nodes", []) if isinstance(data.get("nodes"), list) else []:
                if isinstance(node, dict) and "title" not in node:
                    node["title"] = node.get("label") or node.get("id")
        return cls(
            type=kind, title=title.strip(), data=data, output_format=output_format,
            subject=_optional_text(value.get("subject"), "subject"),
            topic=_optional_text(value.get("topic"), "topic"),
            source=value.get("source"),
            subtitle=_optional_text(value.get("subtitle"), "subtitle"),
            description=_optional_text(value.get("description"), "description"),
            notes=_optional_notes(value.get("notes")),
        )


def _optional_text(value, name):
    if value is not None and (not isinstance(value, str) or len(value) > 500):
        raise ValueError(f"{name} debe ser texto de hasta 500 caracteres.")
    return value


def _optional_notes(value):
    if value is not None and (not isinstance(value, list) or any(not isinstance(item, str) or len(item) > 1000 for item in value)):
        raise ValueError("notes debe ser una lista de textos de hasta 1000 caracteres.")
    return value


def classify_visual_intent(text: str) -> str | None:
    """Small deterministic heuristic; ambiguous requests stay unclassified."""
    normalized = text.casefold()
    if any(word in normalized for word in ("gráfico", "grafico", "función", "funcion", "plot")):
        return "function" if "func" in normalized else "numeric_data"
    if any(word in normalized for word in ("árbol", "arbol", "grafo", "dag")):
        return "tree" if "árbol" in normalized or "arbol" in normalized else "graph"
    if any(word in normalized for word in ("flujo", "proceso", "pasos", "secuencia", "arquitectura")):
        return "sequence" if "secuencia" in normalized else "process"
    return None


def render_request(request: VisualRequest) -> dict:
    renderer = RENDERERS[request.type]
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    slug = re.sub(r"[^a-z0-9]+", "-", request.title.casefold()).strip("-")[:60] or "visual"
    path = OUTPUT_DIR / f"{slug}{renderer.extension}"
    # Avoid replacing a prior artifact when two requests share a title.
    index = 2
    while (path.exists()
           or (renderer is render_native_artifact and any(path.with_suffix(ext).exists() for ext in (".mmd", ".svg")))
           or (renderer is render_mermaid and render_mermaid.has_mmdc() and path.with_suffix(".svg").exists())):
        path = OUTPUT_DIR / f"{slug}-{index}{renderer.extension}"
        index += 1
    if renderer is render_native_artifact:
        semantic = SemanticVisualSpec.from_dict({**request.data,
            "type": request.type, "title": request.title,
            "subtitle": request.subtitle or request.data.get("subtitle"),
            "description": request.description or request.data.get("description"),
            "notes": request.notes if request.notes is not None else request.data.get("notes"),
            "source": request.source if request.source is not None else request.data.get("source")})
        renderer.render(semantic, path, OUTPUT_DIR)
        artifacts = [path.relative_to(ROOT).as_posix()]
        result = {"type": request.type, "title": request.title, "artifact": artifacts[0], "artifacts": artifacts,
                  "presentation_artifact": artifacts[0], "renderer": "native"}
        if request.output_format in {"source", "svg"}:
            export = path.with_suffix(".mmd")
            render_mermaid.render(request, export, render_svg=request.output_format == "svg")
            export_rel = export.relative_to(ROOT).as_posix()
            artifacts.append(export_rel)
            result["technical_asset"] = export_rel
            if request.output_format == "svg" and export.with_suffix(".svg").exists():
                artifacts.append(export.with_suffix(".svg").relative_to(ROOT).as_posix())
                result["technical_asset"] = artifacts[-1]
        return result
    extra_artifact = renderer.render(request, path)
    artifacts = [path.relative_to(ROOT).as_posix()]
    if extra_artifact is not None:
        artifacts.append(extra_artifact.relative_to(ROOT).as_posix())
    result = {"type": request.type, "title": request.title, "artifact": artifacts[0], "artifacts": artifacts}
    visual_path = next((item for item in artifacts if item.endswith((".svg", ".png"))), None)
    if extra_artifact is not None and str(extra_artifact.relative_to(ROOT)).replace("\\", "/") not in artifacts:
        visual_path = str(extra_artifact.relative_to(ROOT)).replace("\\", "/")
        artifacts.append(visual_path)
    if visual_path:
        presentation_path = path.with_name(path.stem + "-artifact.html")
        index = 2
        while presentation_path.exists():
            presentation_path = path.with_name(f"{path.stem}-artifact-{index}.html")
            index += 1
        presentation = render_artifact.render_artifact({
            "title": request.title,
            "source": request.source,
            "subject": request.subject,
            "topic": request.topic,
            "subtitle": request.subtitle,
            "description": request.description,
            "notes": request.notes or [],
            "visuals": [{"kind": Path(visual_path).suffix[1:], "path": Path(visual_path).name}],
        }, presentation_path)
        result["technical_asset"] = visual_path
        presentation_path = presentation_path.relative_to(ROOT).as_posix()
        result["presentation_artifact"] = presentation_path
        result["artifacts"].append(presentation_path)
    return result


def main() -> int:
    try:
        result = render_request(VisualRequest.from_dict(json.load(sys.stdin)))
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0
    except (ValueError, RuntimeError, OSError) as error:
        print(f"Error: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
