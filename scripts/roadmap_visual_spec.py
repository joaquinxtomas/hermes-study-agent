"""Validation for editorial learning roadmaps (separate from graph specs)."""

from dataclasses import dataclass


IMPORTANCE = {"core", "recommended", "optional", "specialization"}
BRANCH_KINDS = {"recommended", "optional", "specialization"}
SOURCE_KEYS = {"title", "chapter", "section", "page"}


def _text(value, field, optional=False, limit=2000):
    if value is None and optional:
        return None
    if not isinstance(value, str) or not value.strip() or len(value) > limit:
        raise ValueError(f"{field} debe ser texto no vacío de hasta {limit} caracteres.")
    return value.strip()


@dataclass(frozen=True)
class RoadmapVisualSpec:
    title: str
    sections: list
    nodes: list
    main_path: list
    branches: list
    subtitle: str | None = None
    description: str | None = None
    notes: list | None = None
    source: dict | None = None

    @classmethod
    def from_dict(cls, value):
        if not isinstance(value, dict) or value.get("type") != "roadmap":
            raise ValueError("La especificación debe tener type=roadmap.")
        title = _text(value.get("title"), "title", limit=160)
        raw_sections = value.get("sections")
        raw_nodes = value.get("nodes")
        raw_path = value.get("main_path")
        raw_branches = value.get("branches", [])
        if not isinstance(raw_sections, list) or not 1 <= len(raw_sections) <= 12:
            raise ValueError("sections debe contener entre 1 y 12 etapas.")
        if not isinstance(raw_nodes, list) or not 1 <= len(raw_nodes) <= 50:
            raise ValueError("nodes debe contener entre 1 y 50 conceptos.")
        if not isinstance(raw_path, list) or not raw_path:
            raise ValueError("main_path debe contener IDs de nodos en orden.")
        if not isinstance(raw_branches, list):
            raise ValueError("branches debe ser una lista.")

        sections, section_ids, section_orders = [], set(), set()
        for index, raw in enumerate(raw_sections):
            if not isinstance(raw, dict):
                raise ValueError("Cada section debe ser un objeto.")
            section_id = _text(raw.get("id"), "section.id", limit=100)
            order = raw.get("order", index + 1)
            if section_id in section_ids or not isinstance(order, int) or isinstance(order, bool) or order in section_orders:
                raise ValueError("Cada section necesita id y order únicos; order debe ser entero.")
            section_ids.add(section_id)
            section_orders.add(order)
            sections.append({"id": section_id, "title": _text(raw.get("title"), "section.title", limit=100),
                             "order": order, "description": _text(raw.get("description"), "section.description", True)})
        sections.sort(key=lambda item: item["order"])
        section_rank = {section["id"]: index for index, section in enumerate(sections)}

        nodes, node_ids = [], set()
        for raw in raw_nodes:
            if not isinstance(raw, dict):
                raise ValueError("Cada node debe ser un objeto.")
            node_id = _text(raw.get("id"), "node.id", limit=100)
            section = raw.get("section")
            importance = raw.get("importance", "core")
            if node_id in node_ids:
                raise ValueError(f"ID de nodo duplicado: {node_id}.")
            if not isinstance(section, str) or section not in section_ids:
                raise ValueError(f"Section desconocida para {node_id}: {section!r}.")
            if not isinstance(importance, str) or importance not in IMPORTANCE:
                raise ValueError(f"Importancia no soportada: {importance!r}.")
            node_ids.add(node_id)
            nodes.append({"id": node_id, "title": _text(raw.get("title"), "node.title", limit=100),
                          "section": section, "importance": importance,
                          "subtitle": _text(raw.get("subtitle"), "node.subtitle", True, 240),
                          "description": _text(raw.get("description"), "node.description", True)})
        by_id = {node["id"]: node for node in nodes}
        if any(not isinstance(node_id, str) or node_id not in node_ids for node_id in raw_path):
            raise ValueError("main_path contiene IDs inexistentes.")
        if len(set(raw_path)) != len(raw_path):
            raise ValueError("main_path no puede repetir nodos.")
        if any(section_rank[by_id[a]["section"]] > section_rank[by_id[b]["section"]]
               for a, b in zip(raw_path, raw_path[1:])):
            raise ValueError("main_path debe avanzar en el orden de sections.")
        if {by_id[node_id]["section"] for node_id in raw_path} != section_ids:
            raise ValueError("Cada section debe contener al menos un nodo del main_path.")
        path_rank = {node_id: index for index, node_id in enumerate(raw_path)}

        branches, assigned = [], set(raw_path)
        for raw in raw_branches:
            if not isinstance(raw, dict) or not isinstance(raw.get("nodes"), list) or not raw["nodes"]:
                raise ValueError("Cada branch necesita from y una lista nodes no vacía.")
            origin, members, kind, rejoin = raw.get("from"), raw["nodes"], raw.get("kind"), raw.get("rejoin")
            if not isinstance(origin, str) or origin not in path_rank:
                raise ValueError(f"Branch.from debe ser un nodo del main_path: {origin!r}.")
            if not isinstance(kind, str) or kind not in BRANCH_KINDS:
                raise ValueError(f"Tipo de rama no soportado: {kind!r}.")
            if any(not isinstance(node_id, str) or node_id not in node_ids or node_id in assigned for node_id in members) or len(set(members)) != len(members):
                raise ValueError("Branch.nodes contiene IDs inexistentes o repetidos.")
            if any(by_id[node_id]["section"] != by_id[origin]["section"] for node_id in members):
                raise ValueError("En V1, una rama permanece en la section de su origen.")
            if rejoin is not None and (not isinstance(rejoin, str) or rejoin not in path_rank or path_rank[rejoin] <= path_rank[origin]
                                       or by_id[rejoin]["section"] != by_id[origin]["section"]):
                raise ValueError("Branch.rejoin debe apuntar a un nodo posterior del main_path en la misma section.")
            assigned.update(members)
            branches.append({"from": origin, "nodes": list(members), "kind": kind,
                             "rejoin": rejoin, "label": _text(raw.get("label"), "branch.label", True, 120)})
        orphaned = node_ids - assigned
        if orphaned:
            raise ValueError("Nodos huérfanos fuera de main_path y branches: " + ", ".join(sorted(orphaned)))

        notes = value.get("notes")
        if notes is not None and (not isinstance(notes, list) or any(not isinstance(note, str) or len(note) > 2000 for note in notes)):
            raise ValueError("notes debe ser una lista de textos de hasta 2000 caracteres.")
        source = value.get("source")
        if source is not None:
            if not isinstance(source, dict) or any(key not in SOURCE_KEYS for key in source) or any(not isinstance(item, (str, int)) or not str(item).strip() for item in source.values()):
                raise ValueError("source admite title, chapter, section y page como textos o números.")
            source = {key: str(item).strip() for key, item in source.items()}
        return cls(title, sections, nodes, list(raw_path), branches,
                   _text(value.get("subtitle"), "subtitle", True, 500),
                   _text(value.get("description"), "description", True), notes, source)
