"""Deterministic, conservative knowledge-state transitions."""

DIMENSIONS = {"conceptual", "procedural", "independent_problem_solving", "retention"}
STATUSES = {"not_seen", "introduced", "understood", "practicing", "independent", "needs_review"}
EVIDENCE_TYPES = {"explanation", "guided_exercise", "independent_exercise", "exam_question", "doubt", "review", "self_assessment"}
RESULTS = {"correct", "partially_correct", "incorrect", "completed", "observed"}


def apply_evidence(current_status: str, dimension: str, evidence_type: str, result: str) -> str:
    """Return the next state; doubt observations never change a state."""
    if current_status not in STATUSES:
        raise ValueError(f"Invalid knowledge status: {current_status}")
    if dimension not in DIMENSIONS:
        raise ValueError(f"Invalid knowledge dimension: {dimension}")
    if evidence_type not in EVIDENCE_TYPES:
        raise ValueError(f"Invalid evidence type: {evidence_type}")
    if result not in RESULTS:
        raise ValueError(f"Invalid evidence result: {result}")
    if evidence_type == "doubt":
        return current_status
    if result == "incorrect":
        if evidence_type in {"independent_exercise", "exam_question"}:
            return "practicing" if current_status == "independent" else "needs_review"
        return current_status
    if result not in {"correct", "completed"}:
        return "introduced" if current_status == "not_seen" else current_status
    if dimension == "conceptual" and evidence_type == "explanation" and result == "correct":
        return "understood"
    if dimension == "procedural":
        if evidence_type == "guided_exercise":
            return "practicing"
        if evidence_type == "independent_exercise":
            return "independent"
    if dimension == "independent_problem_solving" and evidence_type == "independent_exercise":
        return "independent"
    if dimension == "retention" and evidence_type == "review":
        return "understood"
    if current_status == "not_seen":
        return "introduced"
    return current_status
