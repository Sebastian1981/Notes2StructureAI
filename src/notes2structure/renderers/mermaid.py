"""Safe Mermaid flowchart rendering from validated graph data only."""

from __future__ import annotations

import re

from notes2structure.schemas import DiagramStatus, DocumentIR, DocumentType, Edge, Node, NodeKind

_ACTIVE_CHARACTERS = frozenset('#"&<>`{}[]();|%:/')


def render_mermaid(document: DocumentIR) -> str | None:
    if document.diagram.status is not DiagramStatus.GENERATED:
        return None
    direction = (
        "LR" if document.classification.effective_type is DocumentType.ARCHITECTURE else "TD"
    )
    lines = [f"flowchart {direction}"]
    lines.extend(f"    {_render_node(node)}" for node in sorted(document.graph.nodes, key=_id_key))
    lines.extend(f"    {_render_edge(edge)}" for edge in sorted(document.graph.edges, key=_id_key))
    return "\n".join(lines) + "\n"


def _render_node(node: Node) -> str:
    label = node.label + (" (?)" if node.uncertain else "")
    safe_label = _escape_label(label)
    if node.kind is NodeKind.DECISION:
        return f'{node.id}{{"{safe_label}"}}'
    return f'{node.id}["{safe_label}"]'


def _render_edge(edge: Edge) -> str:
    if edge.uncertain:
        connector = "-.->" if edge.directed else "-.-"
    else:
        connector = "-->" if edge.directed else "---"
    if edge.label is None:
        return f"{edge.source} {connector} {edge.target}"
    label = edge.label + (" (?)" if edge.uncertain else "")
    return f'{edge.source} {connector}|"{_escape_label(label)}"| {edge.target}'


def _escape_label(value: str) -> str:
    normalized = re.sub(r"[\x00-\x1f\x7f]+", " ", value).strip()
    return "".join(
        f"#{ord(character)};" if character in _ACTIVE_CHARACTERS else character
        for character in normalized
    )


def _id_key(item: Node | Edge) -> int:
    return int(item.id[1:])
