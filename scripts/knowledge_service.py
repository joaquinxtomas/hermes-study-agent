"""Application service: persist evidence and apply deterministic rules."""
import knowledge_rules as rules
import knowledge_store as store


def record_learning_event(topic_id, dimension, evidence_type, result, details,
                          session_id=None, doubt_id=None, source_id=None):
    current = store.get_knowledge_state(topic_id, dimension)
    previous = current["status"] if current else "not_seen"
    next_status = rules.apply_evidence(previous, dimension, evidence_type, result)
    return store.record_transition(topic_id, dimension, evidence_type, result, details,
                                   next_status, session_id, doubt_id, source_id)


def explain_topic(topic_id):
    states = store.initialize_topic_states(topic_id)
    evidence = store.list_evidence(topic_id)
    misconceptions = store.list_misconceptions(topic_id=topic_id, status="active")
    return {"topic_id": topic_id, "states": states, "evidence": evidence,
            "active_misconceptions": misconceptions}
