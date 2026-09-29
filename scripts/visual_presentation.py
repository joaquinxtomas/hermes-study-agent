"""Choose where to show a native artifact from its graph metadata."""


def choose_presentation(visual_type: str, analysis: dict) -> dict:
    """Return a portable preference; the caller handles preview availability."""
    nodes = analysis["node_count"]
    edges = analysis["edge_count"]
    levels = analysis["number_of_levels"]
    width = analysis["max_nodes_per_level"]
    branching = analysis["branching_factor"]
    groups = analysis["number_of_groups"]

    if nodes >= 16 or edges >= 24 or levels >= 12 or width >= 6 or branching >= 5 or groups >= 6:
        complexity = "large"
    elif nodes >= 9 or edges >= 11 or levels >= 8 or width >= 4 or branching >= 3 or groups >= 3:
        complexity = "medium"
    else:
        complexity = "small"

    very_dense = nodes > 0 and edges >= 12 and edges >= 2 * nodes
    expanded = complexity == "large" or very_dense
    return {
        "complexity": complexity,
        "preferred_presentation": "expanded" if expanded else "inline",
        "presentation_reason": (
            f"{complexity}_complexity_{visual_type}" if complexity == "large" else
            f"dense_{visual_type}" if very_dense else
            "medium_fits_inline" if complexity == "medium" else "small_artifact"
        ),
    }


def choose_math_presentation(visual_type: str, data: dict) -> dict:
    """Keep simple boards inline; open dense mathematical views in preview."""
    count = (data.get("grid", 9) ** 2 if visual_type == "vector_field" else
             len(data.get("elements", [])) if visual_type in {"geometry", "circuit"} else 1)
    expanded = (visual_type == "vector_field" and count >= 49 or
                visual_type in {"geometry", "circuit"} and count >= 12)
    complexity = "large" if count >= 40 else "medium" if expanded else "small"
    return {"complexity": complexity, "preferred_presentation": "expanded" if expanded else "inline",
            "presentation_reason": "dense_math_artifact" if expanded else "small_math_artifact"}
