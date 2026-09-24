"""Render tree/graph/DAG specifications as DOT, with optional Graphviz PNG."""

import json
import re
import shutil
import subprocess

extension = ".dot"


def render(request, path):
    nodes, edges = request.data.get("nodes"), request.data.get("edges", [])
    if not isinstance(nodes, list) or not nodes or not isinstance(edges, list):
        raise ValueError("Graphviz requiere data.nodes y data.edges como listas no vacías.")
    ids = set()
    lines = []
    for node in nodes:
        if not isinstance(node, dict) or not re.fullmatch(r"[A-Za-z][A-Za-z0-9_]{0,39}", str(node.get("id", ""))):
            raise ValueError("Cada nodo necesita id seguro (letras, números y _).")
        if node["id"] in ids:
            raise ValueError(f"ID de nodo duplicado: {node['id']}.")
        label = node.get("label", node["id"])
        if not isinstance(label, str) or len(label) > 200:
            raise ValueError("Las etiquetas deben ser texto de hasta 200 caracteres.")
        ids.add(node["id"])
        lines.append(f"  {node['id']} [label={json.dumps(label, ensure_ascii=False)}];")
    for edge in edges:
        if not isinstance(edge, dict) or edge.get("from") not in ids or edge.get("to") not in ids:
            raise ValueError("Cada enlace debe apuntar a IDs de nodos existentes.")
        lines.append(f"  {edge['from']} -> {edge['to']};")
    source = "digraph" if request.type in {"tree", "dag"} else "graph"
    arrow = "->" if source == "digraph" else "--"
    lines = [line.replace(" -> ", f" {arrow} ") for line in lines]
    path.write_text(f"{source} study {{\n" + "\n".join(lines) + "\n}\n", encoding="utf-8")
    if request.output_format == "png":
        dot = shutil.which("dot")
        if not dot:
            raise RuntimeError(f"Artifact DOT guardado en {path}; Graphviz (dot) no está instalado para PNG.")
        try:
            subprocess.run([dot, "-Tpng", str(path), "-o", str(path.with_suffix(".png"))], check=True, timeout=30, capture_output=True)
        except (subprocess.CalledProcessError, subprocess.TimeoutExpired) as error:
            raise RuntimeError(f"Graphviz no pudo generar PNG: {error} (source disponible en {path}).") from error
