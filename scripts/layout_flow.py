"""Deterministic longest-path layout for simple directed acyclic flows."""


def flow_layout(spec):
    indegree = {node["id"]: 0 for node in spec.nodes}
    outgoing = {key: [] for key in indegree}
    for edge in spec.edges:
        outgoing[edge["from"]].append(edge["to"])
        indegree[edge["to"]] += 1
    ready = [key for key, count in indegree.items() if count == 0]
    levels = dict.fromkeys(ready, 0)
    # ponytail: pop(0) is O(V²), switch to deque if specs exceed the current 100-node limit.
    while ready:
        current = ready.pop(0)
        for target in outgoing[current]:
            levels[target] = max(levels.get(target, 0), levels[current] + 1)
            indegree[target] -= 1
            if indegree[target] == 0:
                ready.append(target)
    return [[node for node in spec.nodes if levels[node["id"]] == level]
            for level in range(max(levels.values(), default=0) + 1)]
