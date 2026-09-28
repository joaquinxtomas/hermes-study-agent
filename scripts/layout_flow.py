"""Deterministic DAG analysis and container-independent layout plans.

Python packs semantic lanes into grid slots. The standalone browser selects a
plan for the measured container; CSS supplies actual sizes, JS measures anchors.
"""

from collections import Counter, deque

MIN_CARD_WIDTH = 208
PREFERRED_CARD_WIDTH = 248
MAX_CARD_WIDTH = 320
COLUMN_GAP = 48
GUTTER = 28
MAX_COLUMNS = 6


def flow_layout(spec):
    indegree = {node["id"]: 0 for node in spec.nodes}
    outgoing = {key: [] for key in indegree}
    for edge in spec.edges:
        outgoing[edge["from"]].append(edge["to"])
        indegree[edge["to"]] += 1
    ready = deque(key for key, count in indegree.items() if count == 0)
    levels = dict.fromkeys(ready, 0)
    while ready:
        current = ready.popleft()
        for target in outgoing[current]:
            levels[target] = max(levels.get(target, 0), levels[current] + 1)
            indegree[target] -= 1
            if indegree[target] == 0:
                ready.append(target)
    return [[node for node in spec.nodes if levels.get(node["id"]) == level]
            for level in range(max(levels.values(), default=0) + 1)]


def analyze_graph(spec):
    levels = flow_layout(spec)
    acyclic = sum(map(len, levels)) == len(spec.nodes)
    degrees = Counter(edge["from"] for edge in spec.edges)
    # Branching factor is maximum distinct successors, not duplicate edges.
    branching = max((len({e["to"] for e in spec.edges if e["from"] == node})
                     for node in degrees), default=0)
    size = max(len(spec.nodes), len(spec.edges) / 2)
    return {"node_count": len(spec.nodes), "edge_count": len(spec.edges),
            "number_of_levels": len(levels) if acyclic else 0,
            "longest_path": len(levels) - 1 if acyclic else 0,
            "max_nodes_per_level": max(map(len, levels)) if acyclic else 0,
            "branching_factor": branching, "number_of_groups": len(spec.groups or []),
            "density": "large" if size > 16 or branching > 4 else "medium" if size > 8 else "small"}


def semantic_lanes(spec):
    """Stable topological order, preferring the current group among ready nodes.

    Cross-group dependencies may split a group into several lane segments.
    Multiple memberships stay in the spec; the first group owns placement.
    """
    owner = {}
    for index, group in enumerate(spec.groups or []):
        for node in group["nodes"]:
            owner.setdefault(node, index)
    pending = [node["id"] for level in flow_layout(spec) for node in level]
    parents = {node: set() for node in pending}
    for edge in spec.edges:
        parents[edge["to"]].add(edge["from"])
    visited, lanes = set(), []
    previous = None
    while pending:
        ready = [node for node in pending if parents[node] <= visited]
        current = next((node for node in ready if owner.get(node) == previous), ready[0])
        group = owner.get(current)
        if not lanes or group != previous:
            lanes.append({"group": group, "title": spec.groups[group]["title"] if group is not None else None,
                          "nodes": []})
        lanes[-1]["nodes"].append(current)
        visited.add(current)
        pending.remove(current)
        previous = group
    return lanes


def pack_layout(spec, columns, mode="compact"):
    """Return grid slots, lane bands, and per-edge anchor sides; never pixels."""
    if not 1 <= columns <= MAX_COLUMNS or mode not in {"wide", "compact", "narrow"}:
        raise ValueError("Modo o cantidad de columnas inválidos.")
    positions, bands, row = {}, [], 0
    for lane in semantic_lanes(spec):
        first = row
        if lane["title"] is not None:
            row += 1  # An actual header row: no node/label overlays.
        local = {}
        for node in lane["nodes"]:
            local[node] = max((local[e["from"]] + 1 for e in spec.edges
                               if e["to"] == node and e["from"] in local), default=0)
        levels = [[node for node in lane["nodes"] if local[node] == level]
                  for level in range(max(local.values()) + 1)]
        if mode == "wide":
            for start in range(0, len(levels), columns):
                band = levels[start:start + columns]
                height = max(map(len, band))
                for col, level in enumerate(band):
                    for offset, node in enumerate(level):
                        positions[node] = {"row": row + (height - len(level)) // 2 + offset, "col": col}
                row += height
        else:
            col = 0
            previous_parallel = False
            for level in levels:
                parallel = len(level) > 1
                if col and (parallel or previous_parallel):
                    row, col = row + 1, 0
                if previous_parallel and len(level) == 1:
                    # Keep a surviving branch over its own predecessor when possible.
                    parents = [positions[e["from"]]["col"] for e in spec.edges
                               if e["to"] == level[0] and e["from"] in local
                               and e["from"] in positions]
                    if parents:
                        col = min(parents)
                for node in level:
                    positions[node] = {"row": row, "col": col}
                    col += 1
                    if col == columns:
                        row, col = row + 1, 0
                previous_parallel = parallel
            if col:
                row += 1
        bands.append({**lane, "start": first, "end": row})
    anchors = []
    for edge in spec.edges:
        a, b = positions[edge["from"]], positions[edge["to"]]
        horizontal = a["row"] == b["row"] or (mode == "wide" and b["col"] > a["col"])
        anchors.append(["right", "left"] if horizontal else ["bottom", "top"])
    return {"positions": positions, "lanes": bands, "anchors": anchors, "rows": row}


def responsive_layouts(spec):
    return {"analysis": analyze_graph(spec),
            "sizing": {"min": MIN_CARD_WIDTH, "preferred": PREFERRED_CARD_WIDTH,
                       "max": MAX_CARD_WIDTH, "gap": COLUMN_GAP, "gutter": GUTTER},
            "plans": {f"{mode}-{columns}": pack_layout(spec, columns, mode)
                      for mode in ("narrow", "compact", "wide")
                      for columns in ([1] if mode == "narrow" else range(2, MAX_COLUMNS + 1))}}
