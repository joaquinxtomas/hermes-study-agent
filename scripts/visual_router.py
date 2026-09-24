"""Validate visual requests and route them to a local renderer."""

from dataclasses import dataclass
import json
from pathlib import Path
import re
import sys

import render_graphviz
import render_mermaid
import render_plot

ROOT = Path(__file__).resolve().parents[1]
OUTPUT_DIR = ROOT / "diagrams" / "generated"
RENDERERS = {
    "process": render_mermaid,
    "architecture": render_mermaid,
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
    source: str | None = None

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
        if not isinstance(output_format, str) or output_format not in {"source", "svg", "png"}:
            raise ValueError("output_format debe ser source, svg o png.")
        if kind in {"process", "architecture", "sequence"} and output_format not in {"source", "svg"}:
            raise ValueError("Mermaid admite output_format source o svg.")
        if kind in {"tree", "graph", "dag"} and output_format not in {"source", "png"}:
            raise ValueError("Graphviz admite output_format source o png.")
        if kind in {"function", "numeric_data", "study_metrics"} and output_format != "png":
            raise ValueError("Matplotlib admite output_format png.")
        return cls(
            type=kind, title=title.strip(), data=data, output_format=output_format,
            subject=_optional_text(value.get("subject"), "subject"),
            topic=_optional_text(value.get("topic"), "topic"),
            source=_optional_text(value.get("source"), "source"),
        )


def _optional_text(value, name):
    if value is not None and (not isinstance(value, str) or len(value) > 500):
        raise ValueError(f"{name} debe ser texto de hasta 500 caracteres.")
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
    while (path.exists() or (renderer is render_mermaid and render_mermaid.has_mmdc()
                             and path.with_suffix(".svg").exists())):
        path = OUTPUT_DIR / f"{slug}-{index}{renderer.extension}"
        index += 1
    extra_artifact = renderer.render(request, path)
    artifacts = [str(path.relative_to(ROOT))]
    if extra_artifact is not None:
        artifacts.append(str(extra_artifact.relative_to(ROOT)))
    return {"type": request.type, "title": request.title, "artifact": artifacts[0], "artifacts": artifacts}


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
