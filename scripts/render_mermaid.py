"""Render structured nodes and edges as Mermaid source."""

import json
import re
import shutil
import subprocess
import warnings

extension = ".mmd"


def has_mmdc():
    return shutil.which("mmdc")


def _nodes_edges(data):
    nodes, edges = data.get("nodes"), data.get("edges", [])
    if not isinstance(nodes, list) or not nodes or not isinstance(edges, list):
        raise ValueError("Mermaid requiere data.nodes y data.edges como listas no vacías.")
    ids = set()
    lines = []
    for node in nodes:
        if not isinstance(node, dict) or not re.fullmatch(r"[A-Za-z][A-Za-z0-9_]{0,39}", str(node.get("id", ""))):
            raise ValueError("Cada nodo necesita id seguro (letras, números y _).")
        if node["id"] in ids:
            raise ValueError(f"ID de nodo duplicado: {node['id']}.")
        label = node.get("label", node["id"])
        if not isinstance(label, str) or len(label) > 200 or "\n" in label:
            raise ValueError("Las etiquetas deben ser texto de hasta 200 caracteres en una línea.")
        ids.add(node["id"])
        lines.append(f"    {node['id']}[{json.dumps(label, ensure_ascii=False)}]")
    for edge in edges:
        if not isinstance(edge, dict) or edge.get("from") not in ids or edge.get("to") not in ids:
            raise ValueError("Cada enlace debe apuntar a IDs de nodos existentes.")
        label = edge.get("label")
        arrow = f" -- {json.dumps(label, ensure_ascii=False)} --> " if label else " --> "
        lines.append(f"    {edge['from']}{arrow}{edge['to']}")
    return lines


def render(request, path):
    if request.type == "sequence":
        participants, messages = request.data.get("participants"), request.data.get("messages")
        if not isinstance(participants, list) or not participants or not isinstance(messages, list):
            raise ValueError("sequence requiere data.participants y data.messages.")
        ids = set()
        lines = ["sequenceDiagram"]
        for item in participants:
            if not isinstance(item, dict) or not re.fullmatch(r"[A-Za-z][A-Za-z0-9_]{0,39}", str(item.get("id", ""))):
                raise ValueError("Cada participante necesita id seguro.")
            if item["id"] in ids:
                raise ValueError(f"ID de participante duplicado: {item['id']}.")
            ids.add(item["id"])
            label = item.get("label", item["id"])
            if not isinstance(label, str) or len(label) > 200 or "\n" in label:
                raise ValueError("Las etiquetas deben ser texto de hasta 200 caracteres en una línea.")
            lines.append(f"    participant {item['id']} as {label}")
        for message in messages:
            if (not isinstance(message, dict) or message.get("from") not in ids
                    or message.get("to") not in ids or not isinstance(message.get("label"), str)
                    or len(message["label"]) > 200 or "\n" in message["label"]):
                raise ValueError("Cada mensaje requiere participantes válidos y una etiqueta de una línea.")
            lines.append(f"    {message['from']}->>{message['to']}: {message['label']}")
        body = "\n".join(lines) + "\n"
    else:
        direction = request.data.get("direction", "LR")
        if direction not in {"LR", "RL", "TB", "BT"}:
            raise ValueError("direction debe ser LR, RL, TB o BT.")
        body = "\n".join([f"flowchart {direction}", *_nodes_edges(request.data)]) + "\n"
    path.write_text(body, encoding="utf-8")
    mmdc = has_mmdc()
    if mmdc:
        output = path.with_suffix(".svg")
        try:
            subprocess.run([mmdc, "-i", str(path), "-o", str(output)], check=True, timeout=60, capture_output=True, text=True)
        except (subprocess.CalledProcessError, subprocess.TimeoutExpired) as error:
            details = getattr(error, "stderr", None)
            warnings.warn(
                f"mmdc no pudo generar SVG{': ' + details.strip() if details else ''}; source guardado en {path}.",
                RuntimeWarning,
            )
            return None
        return output
    return None
