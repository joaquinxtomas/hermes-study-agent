"""Validate semantic specifications for native flow artifacts."""

from dataclasses import dataclass


ROLES = {"input", "process", "storage", "decision", "output", "agent", "source", "tool"}
EDGE_STYLES = {"normal", "dashed", "emphasis"}
TEXT_LIMIT = 2000


def _text(value, name, optional=False):
    if value is None and optional:
        return None
    if not isinstance(value, str) or not value.strip() or len(value) > TEXT_LIMIT:
        raise ValueError(f"{name} debe ser texto no vacío de hasta {TEXT_LIMIT} caracteres.")
    return value.strip()


@dataclass(frozen=True)
class SemanticVisualSpec:
    type: str
    title: str
    nodes: list
    edges: list
    subtitle: str | None = None
    description: str | None = None
    groups: list | None = None
    annotations: list | None = None
    notes: list | None = None
    source: dict | None = None

    @classmethod
    def from_dict(cls, value):
        if not isinstance(value, dict):
            raise ValueError("La especificación visual debe ser un objeto.")
        kind = value.get("type")
        if not isinstance(kind, str) or kind not in {"flow", "process", "architecture", "pipeline"}:
            raise ValueError("type debe ser flow, process, architecture o pipeline.")
        title = _text(value.get("title"), "title")
        nodes, edges = value.get("nodes"), value.get("edges")
        if not isinstance(nodes, list) or not nodes or len(nodes) > 100:
            raise ValueError("nodes debe contener entre 1 y 100 nodos.")
        if not isinstance(edges, list) or len(edges) > 200:
            raise ValueError("edges debe ser una lista de hasta 200 conexiones.")
        ids, clean_nodes = set(), []
        for node in nodes:
            if not isinstance(node, dict):
                raise ValueError("Cada nodo debe ser un objeto.")
            node_id = _text(node.get("id"), "node.id")
            if node_id in ids:
                raise ValueError(f"ID de nodo duplicado: {node_id}.")
            ids.add(node_id)
            role = node.get("role", "process")
            if not isinstance(role, str) or role not in ROLES:
                raise ValueError(f"Rol de nodo no soportado: {role!r}.")
            metadata = node.get("metadata")
            if metadata is not None and (not isinstance(metadata, dict) or any(not isinstance(k, str) or not isinstance(v, (str, int, float, bool)) for k, v in metadata.items())):
                raise ValueError("node.metadata debe ser un objeto de valores simples.")
            clean_nodes.append({"id": node_id, "title": _text(node.get("title"), "node.title"),
                                "subtitle": _text(node.get("subtitle"), "node.subtitle", True),
                                "role": role, "description": _text(node.get("description"), "node.description", True),
                                "metadata": metadata})
        clean_edges = []
        for edge in edges:
            if (not isinstance(edge, dict) or not isinstance(edge.get("from"), str)
                    or not isinstance(edge.get("to"), str) or edge["from"] not in ids or edge["to"] not in ids):
                raise ValueError("Cada conexión debe apuntar a IDs de nodos existentes.")
            style = edge.get("style", "normal")
            if not isinstance(style, str) or style not in EDGE_STYLES:
                raise ValueError(f"Estilo de conexión no soportado: {style!r}.")
            clean_edges.append({"from": edge["from"], "to": edge["to"],
                                "label": _text(edge.get("label"), "edge.label", True), "style": style})
        if kind != "architecture" and _has_cycle(ids, clean_edges):
            raise ValueError("Los flows, procesos y pipelines deben ser acíclicos.")
        notes = value.get("notes")
        if notes is not None and (not isinstance(notes, list) or any(not isinstance(n, str) or len(n) > TEXT_LIMIT for n in notes)):
            raise ValueError("notes debe ser una lista de textos de hasta 2000 caracteres.")
        source = value.get("source")
        if source is not None:
            if not isinstance(source, dict) or any(k not in {"title", "chapter", "section", "page"} for k in source):
                raise ValueError("source debe incluir solo title, chapter, section y page.")
            if any(not isinstance(v, (str, int)) or not str(v).strip() for v in source.values()):
                raise ValueError("Los metadatos de source deben ser textos o números.")
            source = {k: str(v).strip() for k, v in source.items()}
        groups = value.get("groups")
        if groups is not None:
            if not isinstance(groups, list) or any(not isinstance(g, dict) or not isinstance(g.get("title"), str) or not isinstance(g.get("nodes"), list) or any(not isinstance(n, str) or n not in ids for n in g["nodes"]) for g in groups):
                raise ValueError("groups debe contener {title, nodes} con IDs válidos.")
        annotations = value.get("annotations")
        if annotations is not None and (not isinstance(annotations, list) or any(not isinstance(a, str) for a in annotations)):
            raise ValueError("annotations debe ser una lista de textos.")
        if annotations is not None and any(len(a) > TEXT_LIMIT for a in annotations):
            raise ValueError("Cada annotation admite hasta 2000 caracteres.")
        return cls(kind, title, clean_nodes, clean_edges,
                   _text(value.get("subtitle"), "subtitle", True), _text(value.get("description"), "description", True),
                   groups, annotations, notes, source)


def _has_cycle(ids, edges):
    indegree = dict.fromkeys(ids, 0)
    outgoing = {node: [] for node in ids}
    for edge in edges:
        outgoing[edge["from"]].append(edge["to"])
        indegree[edge["to"]] += 1
    ready = [node for node, degree in indegree.items() if degree == 0]
    visited = 0
    while ready:
        node = ready.pop()
        visited += 1
        for target in outgoing[node]:
            indegree[target] -= 1
            if indegree[target] == 0:
                ready.append(target)
    return visited != len(ids)
