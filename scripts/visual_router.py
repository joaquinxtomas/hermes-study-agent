"""Validate visual requests and route them to a local renderer."""

from dataclasses import dataclass
import json
from pathlib import Path
import re
import sys

from latency_profiler import LatencyRun

_LATENCY = LatencyRun.from_environment("visual_artifact")
_LATENCY.mark("python_entry_started")

import render_graphviz
import render_mermaid
import render_plot
import render_math_artifact
import render_artifact
import render_native_artifact
import render_architecture_artifact
import render_roadmap_artifact
from native_visual_spec import SemanticVisualSpec
from layout_flow import analyze_graph
from roadmap_visual_spec import RoadmapVisualSpec
from layout_roadmap import analyze_roadmap
from visual_presentation import choose_presentation, choose_math_presentation

ROOT = Path(__file__).resolve().parents[1]
OUTPUT_DIR = ROOT / "diagrams" / "generated"
RENDERERS = {
    "flow": render_native_artifact,
    "process": render_native_artifact,
    "architecture": render_architecture_artifact,
    "roadmap": render_roadmap_artifact,
    "pipeline": render_native_artifact,
    "sequence": render_mermaid,
    "tree": render_graphviz,
    "graph": render_graphviz,
    "dag": render_graphviz,
    "function": render_math_artifact,
    "geometry": render_math_artifact,
    "coordinate_system": render_math_artifact,
    "vector_field": render_math_artifact,
    "circuit": render_math_artifact,
    "numeric_data": render_plot,
    "study_metrics": render_plot,
}
NATIVE_RENDERERS = {render_native_artifact, render_architecture_artifact, render_roadmap_artifact}


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
        if kind == "roadmap" and data is None:
            data = {key: value[key] for key in ("sections", "nodes", "main_path", "branches") if key in value}
        if not isinstance(data, dict) or len(json.dumps(data, ensure_ascii=False)) > 200_000:
            raise ValueError("data debe ser un objeto JSON de hasta 200 KB.")
        default_format = "png" if kind in {"numeric_data", "study_metrics"} else "html" if kind in {"flow", "process", "architecture", "pipeline", "roadmap", "function", "geometry", "coordinate_system", "vector_field", "circuit"} else "source"
        output_format = value.get("output_format", default_format)
        if not isinstance(output_format, str) or output_format not in {"source", "svg", "png", "html"}:
            raise ValueError("output_format debe ser source, svg, png o html.")
        if kind in {"flow", "process", "architecture", "pipeline"} and output_format not in {"source", "svg", "html"}:
            raise ValueError("El renderer nativo admite html; source/svg quedan disponibles para exportación Mermaid.")
        if kind == "roadmap" and output_format != "html":
            raise ValueError("Roadmap V1 admite únicamente output_format html.")
        if kind == "sequence" and output_format not in {"source", "svg"}:
            raise ValueError("Mermaid admite output_format source o svg.")
        if kind in {"tree", "graph", "dag"} and output_format not in {"source", "png"}:
            raise ValueError("Graphviz admite output_format source o png.")
        if kind in {"function", "geometry", "coordinate_system", "vector_field", "circuit"} and output_format != "html":
            raise ValueError("La visual matemática nativa admite output_format html.")
        if kind in {"numeric_data", "study_metrics"} and output_format != "png":
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


def _contains_math(value):
    if isinstance(value, str):
        return r"\(" in value or "$$" in value
    if isinstance(value, dict):
        return any(_contains_math(item) for item in value.values())
    if isinstance(value, (list, tuple)):
        return any(_contains_math(item) for item in value)
    return False


def classify_visual_intent(text: str) -> str | None:
    """Small deterministic heuristic; ambiguous requests stay unclassified."""
    normalized = text.casefold()
    if any(phrase in normalized for phrase in ("roadmap", "ruta de aprendizaje", "camino de aprendizaje", "plan de estudio", "prerrequisitos", "qué debería aprender", "que deberia aprender")):
        return "roadmap"
    if "arquitectura" in normalized or "architecture" in normalized:
        return "architecture"
    if any(word in normalized for word in ("circuito", "resistencia", "capacitor")):
        return "circuit"
    if any(word in normalized for word in ("campo vectorial", "campo eléctrico", "campo electrico")):
        return "vector_field"
    if any(word in normalized for word in ("geometría", "geometria", "vectores", "sistema de coordenadas")):
        return "geometry"
    if any(word in normalized for word in ("gráfico", "grafico", "función", "funcion", "plot")):
        return "function" if "func" in normalized else "numeric_data"
    if any(word in normalized for word in ("árbol", "arbol", "grafo", "dag")):
        return "tree" if "árbol" in normalized or "arbol" in normalized else "graph"
    if any(word in normalized for word in ("flujo", "proceso", "pasos", "secuencia")):
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
           or (renderer in NATIVE_RENDERERS and any(path.with_suffix(ext).exists() for ext in (".mmd", ".svg")))
           or (renderer is render_mermaid and render_mermaid.has_mmdc() and path.with_suffix(".svg").exists())):
        path = OUTPUT_DIR / f"{slug}-{index}{renderer.extension}"
        index += 1
    if renderer in NATIVE_RENDERERS:
        payload = {**request.data,
            "type": request.type, "title": request.title,
            "subtitle": request.subtitle or request.data.get("subtitle"),
            "description": request.description or request.data.get("description"),
            "notes": request.notes if request.notes is not None else request.data.get("notes"),
            "source": request.source if request.source is not None else request.data.get("source")}
        semantic = RoadmapVisualSpec.from_dict(payload) if renderer is render_roadmap_artifact else SemanticVisualSpec.from_dict(payload)
        analysis = analyze_roadmap(semantic) if renderer is render_roadmap_artifact else analyze_graph(semantic)
        renderer.render(semantic, path, OUTPUT_DIR)
        if _contains_math(payload):
            render_math_artifact.inject_typesetting(path)
        artifacts = [path.relative_to(ROOT).as_posix()]
        result = {"type": request.type, "title": request.title, "artifact": artifacts[0], "artifacts": artifacts,
                  "presentation_artifact": artifacts[0],
                  "renderer": "native-roadmap" if renderer is render_roadmap_artifact else "native-graphviz" if renderer is render_architecture_artifact else "native",
                  "visual_type": request.type, **analysis, **choose_presentation(request.type, analysis)}
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
    if renderer is render_math_artifact:
        renderer.render(request, path)
        artifact = path.relative_to(ROOT).as_posix()
        return {"type": request.type, "title": request.title, "artifact": artifact,
                "artifacts": [artifact], "presentation_artifact": artifact,
                "renderer": "native-math", "visual_type": request.type,
                **choose_math_presentation(request.type, request.data)}
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
        if _contains_math((request.title, request.subtitle, request.description, request.notes, request.source)):
            render_math_artifact.inject_typesetting(presentation_path)
        result["technical_asset"] = visual_path
        presentation_path = presentation_path.relative_to(ROOT).as_posix()
        result["presentation_artifact"] = presentation_path
        result["artifacts"].append(presentation_path)
    return result


def main() -> int:
    _LATENCY.mark("core_program_started")
    try:
        request = VisualRequest.from_dict(json.load(sys.stdin))
        node_count = len(request.data.get("nodes", [])) if isinstance(request.data.get("nodes"), list) else 0
        _LATENCY.set_benchmark(
            "roadmap_large" if request.type == "roadmap" and node_count >= 16 else
            "visual_medium" if request.type == "architecture" else
            "visual_artifact"
        )
        _LATENCY.mark("artifact_render_started")
        result = render_request(request)
        _LATENCY.mark("artifact_generated")
        _LATENCY.artifact_generated = True
        print(json.dumps(result, ensure_ascii=False, indent=2))
        _LATENCY.mark("core_program_finished")
        _LATENCY.finish(success=True)
        return 0
    except (ValueError, RuntimeError, OSError) as error:
        _LATENCY.artifact_generated = False
        _LATENCY.mark("core_program_finished")
        _LATENCY.finish(success=False, error=error)
        print(f"Error: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
