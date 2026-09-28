"""Standalone architecture maps laid out by Graphviz, with readable HTML details."""

from html import escape
import json
from pathlib import Path
import re
import shutil
import subprocess
from textwrap import shorten

from native_visual_spec import SemanticVisualSpec

extension = ".html"
MAX_OVERVIEW_NODES = 12
MAX_OVERVIEW_EDGES = 18

ROLE_COLORS = {
    "input": ("#94a3b8", "#1e293b"),
    "source": ("#22d3ee", "#103747"),
    "process": ("#34d399", "#103b32"),
    "tool": ("#22d3ee", "#103747"),
    "agent": ("#c084fc", "#36244a"),
    "storage": ("#a78bfa", "#31234b"),
    "decision": ("#fb7185", "#471e33"),
    "output": ("#fbbf24", "#46351a"),
}


def _dot_source(spec, direction):
    ids = {node["id"]: f"n{index}" for index, node in enumerate(spec.nodes)}
    lines = ["digraph Architecture {",
             f'graph [rankdir={direction}, bgcolor="transparent", pad="0.25", nodesep="0.55", ranksep="0.9", splines=ortho, outputorder=edgesfirst];',
             'node [shape=box, style="rounded,filled", penwidth=1.7, margin="0.24,0.20", fontname="sans-serif", fontsize=17, fontcolor="#f8fafc"];',
             'edge [color="#8ba4b6", penwidth=1.7, arrowsize=0.7];']
    for index, node in enumerate(spec.nodes):
        color, fill = ROLE_COLORS[node["role"]]
        title = shorten(node["title"].replace("\n", " "), width=32, placeholder="…")
        subtitle = shorten((node["subtitle"] or "").replace("\n", " "), width=34, placeholder="…")
        label = title + ("\n" + subtitle if subtitle else "")
        lines.append(f'n{index} [label={json.dumps(label, ensure_ascii=False)}, color="{color}", fillcolor="{fill}", URL="#component-{index}"];')
    pairs = {(edge["from"], edge["to"]) for edge in spec.edges}
    drawn = set()
    for edge in spec.edges:
        source, target = edge["from"], edge["to"]
        if (source, target) in drawn:
            continue
        reverse = (target, source) in pairs and source != target
        color = "#fbbf24" if edge["style"] == "emphasis" else "#8ba4b6"
        attrs = [f'color="{color}"']
        if edge["style"] == "dashed":
            attrs.append('style="dashed"')
        if reverse:
            attrs.append("dir=both")
            drawn.add((target, source))
        lines.append(f'{ids[source]} -> {ids[target]} [{", ".join(attrs)}];')
        drawn.add((source, target))
    lines.append("}")
    return "\n".join(lines)


def _svg(spec, direction, dot):
    try:
        result = subprocess.run([dot, "-Tsvg"], input=_dot_source(spec, direction),
                                text=True, capture_output=True, check=True, timeout=30)
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired) as error:
        raise RuntimeError(f"Graphviz no pudo distribuir la arquitectura: {error}") from error
    svg = result.stdout[result.stdout.index("<svg "):]
    svg = re.sub(r'id="([^"]+)"', lambda match: f'id="{direction.lower()}-{match.group(1)}"', svg)
    return svg.replace("<svg ", f'<svg role="img" aria-label="Arquitectura: {escape(spec.title, quote=True)}" ', 1)


def render(spec, path, output_dir):
    if not isinstance(spec, SemanticVisualSpec):
        spec = SemanticVisualSpec.from_dict(spec)
    if spec.type != "architecture":
        raise ValueError("Este renderer requiere type=architecture.")
    output_dir, path = Path(output_dir).resolve(), Path(path).resolve()
    if path.parent != output_dir:
        raise ValueError("El artifact debe guardarse dentro del directorio permitido.")
    if len(spec.nodes) > MAX_OVERVIEW_NODES or len(spec.edges) > MAX_OVERVIEW_EDGES:
        raise ValueError("Arquitectura demasiado densa para una vista general: máximo 12 nodos y 18 relaciones. Dividí el sistema en un mapa general y vistas por subsistema.")
    dot = shutil.which("dot")
    if not dot:
        raise RuntimeError("Graphviz (dot) es necesario para generar arquitecturas HTML.")

    wide, compact = _svg(spec, "LR", dot), _svg(spec, "TB", dot)
    titles = {node["id"]: node["title"] for node in spec.nodes}
    ids = {node["id"]: index for index, node in enumerate(spec.nodes)}
    parts = ["<!doctype html><html lang='es'><head><meta charset='utf-8'><meta name='viewport' content='width=device-width,initial-scale=1'>",
             "<meta http-equiv='Content-Security-Policy' content=\"default-src 'none'; style-src 'unsafe-inline'\">",
             f"<title>{escape(spec.title)}</title><style>{_CSS}</style></head><body><main>",
             f"<header><p class='eyebrow'>ARQUITECTURA · {len(spec.nodes)} COMPONENTES</p><h1>{escape(spec.title)}</h1>"]
    for key in ("subtitle", "description"):
        if getattr(spec, key):
            parts.append(f"<p class='{key}'>{escape(getattr(spec, key))}</p>")
    parts.append("</header><section class='diagram' aria-label='Mapa de componentes'>"
                 f"<div class='compact'>{compact}</div><div class='wide'>{wide}</div></section>")
    if spec.groups:
        parts.append("<section class='groups' aria-label='Áreas del sistema'>")
        for group in spec.groups:
            members = [titles[node_id] for node_id in group["nodes"]]
            parts.append(f"<article class='group'><h2>{escape(group['title'])}</h2><p>{escape(' · '.join(members))}</p></article>")
        parts.append("</section>")
    parts.append("<section class='components' aria-label='Detalles de componentes'><h2>Componentes</h2><div class='cards'>")
    for index, node in enumerate(spec.nodes):
        color = ROLE_COLORS[node["role"]][0]
        parts.append(f"<article class='card' id='component-{index}' style='--role-color:{color}'>"
                     f"<span class='role'>{escape(node['role'].upper())}</span><h3>{escape(node['title'])}</h3>")
        if node["subtitle"]:
            parts.append(f"<p class='subtitle'>{escape(node['subtitle'])}</p>")
        if node["description"]:
            parts.append(f"<p>{escape(node['description'])}</p>")
        if node["metadata"]:
            parts.append("<dl>" + "".join(f"<div><dt>{escape(str(k))}</dt><dd>{escape(str(v))}</dd></div>" for k, v in node["metadata"].items()) + "</dl>")
        outgoing = list(dict.fromkeys(edge["to"] for edge in spec.edges if edge["from"] == node["id"]))
        if outgoing:
            parts.append("<p class='connections'>Conecta con: " + ", ".join(
                f"<a href='#component-{ids[target]}'>{escape(titles[target])}</a>" for target in outgoing) + "</p>")
        parts.append("</article>")
    parts.append("</div></section>")
    if spec.edges:
        parts.append("<details class='relations'><summary>Relaciones del mapa</summary><ul>" + "".join(
            f"<li>{escape(titles[e['from']])} → {escape(titles[e['to']])}" +
            (f": {escape(e['label'])}" if e["label"] else "") + "</li>" for e in spec.edges) + "</ul></details>")
    if spec.annotations or spec.notes:
        parts.append("<aside class='notes'><h2>Notas</h2><ul>" + "".join(
            f"<li>{escape(note)}</li>" for note in [*(spec.annotations or []), *(spec.notes or [])]) + "</ul></aside>")
    if spec.source:
        parts.append("<footer>Fuente · " + escape(" · ".join(f"{k}: {v}" for k, v in spec.source.items())) + "</footer>")
    parts.append("</main></body></html>")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(parts), encoding="utf-8")
    return path


_CSS = """
:root{color-scheme:dark;background:#090f1b;color:#f8fafc;font:15px/1.5 system-ui,sans-serif}*{box-sizing:border-box}body{margin:0}main{container-type:inline-size;max-width:1600px;margin:auto;padding:clamp(16px,3vw,36px)}header{max-width:860px;margin:0 auto 24px}.eyebrow{font-size:.72rem;font-weight:700;letter-spacing:.14em;color:#67e8f9}h1{font-size:clamp(1.7rem,3vw,2.5rem);line-height:1.15;letter-spacing:-.03em;margin:8px 0}.subtitle,.description{color:#cbd5e1;margin:8px 0}.diagram{background:#111c2b;border:1px solid #334155;border-radius:18px;padding:clamp(10px,2vw,24px)}.diagram svg{display:block;width:100%;height:auto;max-width:1250px;margin:auto}.diagram .wide{display:none}.diagram .node a{cursor:pointer}.diagram .node:hover polygon,.diagram .node:hover path{stroke-width:2.6}.groups,.cards{display:grid;grid-template-columns:repeat(auto-fit,minmax(min(100%,230px),1fr));gap:12px}.groups{margin:18px 0}.group,.card,.relations,.notes{background:#111c2b;border:1px solid #334155;border-radius:12px;padding:16px}.group h2{font-size:.95rem;margin:0 0 5px;color:#67e8f9}.group p{font-size:.82rem;color:#cbd5e1;margin:0}.components{margin-top:24px}.components>h2{font-size:1.1rem}.card{border-top:3px solid var(--role-color);scroll-margin:20px}.card:target{outline:3px solid var(--role-color)}.role{color:var(--role-color);font-size:.68rem;font-weight:700;letter-spacing:.12em}.card h3{font-size:1rem;margin:6px 0}.card p{font-size:.86rem;color:#cbd5e1;margin:7px 0}.card a{color:#8be9e0}.card dl{border-top:1px solid #334155;padding-top:8px;font-size:.8rem}.card dl div{display:flex;gap:6px;flex-wrap:wrap}.card dt{color:#94a3b8}.card dd{margin:0}.relations,.notes{margin:20px 0}.relations summary{cursor:pointer;color:#8be9e0}.relations ul,.notes ul{margin:8px 0 0;padding-left:20px}.notes h2{font-size:1rem;margin:0}footer{color:#94a3b8;font-size:.8rem;margin:24px 0}a:focus-visible,summary:focus-visible{outline:2px solid #67e8f9;outline-offset:3px}
@container(min-width:1050px){.diagram .compact{display:none}.diagram .wide{display:block}}
@container(max-width:520px){.diagram{display:none}.components{margin-top:18px}.components>h2::after{content:' · mapa compacto';font-size:.8rem;color:#94a3b8;font-weight:400}.cards{grid-template-columns:1fr}}
"""
