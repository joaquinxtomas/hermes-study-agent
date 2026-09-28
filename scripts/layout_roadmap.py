"""Deterministic section and backbone packing for editorial roadmaps."""

from collections import Counter


# Widths refer to the artifact container, not the host window.
VARIANTS = (("narrow", 0, 1), ("compact", 600, 2), ("compact", 850, 3),
            ("wide", 1100, 4), ("wide", 1400, 5))
BRANCH_ORDER = {"recommended": 0, "optional": 1, "specialization": 2}


def variant_for_width(width):
    return next((variant for variant in reversed(VARIANTS) if width >= variant[1]), VARIANTS[0])


def layout_roadmap(spec, columns):
    """Pack the main path by section; branches stay beside their parent."""
    if columns not in range(1, 6):
        raise ValueError("columns debe estar entre 1 y 5.")
    attached = {node_id: [] for node_id in spec.main_path}
    for index, branch in enumerate(spec.branches):
        attached[branch["from"]].append((BRANCH_ORDER[branch["kind"]], index, branch))
    section_of = {node["id"]: node["section"] for node in spec.nodes}
    return [{"section": section,
             "rows": [[{"node": node_id,
                        "branches": [item[2] for item in sorted(attached[node_id])]}
                       for node_id in path[start:start + columns]]
                      for start in range(0, len(path), columns)]}
            for section in spec.sections
            if (path := [node_id for node_id in spec.main_path
                         if section_of[node_id] == section["id"]])]


def analyze_roadmap(spec):
    branches = Counter(branch["from"] for branch in spec.branches)
    edge_count = max(0, len(spec.main_path) - 1) + sum(len(branch["nodes"]) + bool(branch["rejoin"])
                                                               for branch in spec.branches)
    node_count = len(spec.nodes)
    return {"node_count": node_count, "edge_count": edge_count,
            "number_of_levels": len(spec.main_path), "longest_path": len(spec.main_path) - 1,
            "max_nodes_per_level": max((1 + branches[node] for node in spec.main_path), default=1),
            "branching_factor": max((1 + count for count in branches.values()), default=1),
            "number_of_groups": len(spec.sections),
            "density": "large" if node_count >= 31 else "medium" if node_count >= 13 else "small"}
