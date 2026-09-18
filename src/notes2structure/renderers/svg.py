"""Safe deterministic SVG preview for a validated diagram graph."""

from __future__ import annotations

import html
import math
import textwrap
from collections import defaultdict, deque
from dataclasses import dataclass

from notes2structure.schemas import DiagramStatus, DocumentIR, DocumentType, NodeKind

_MARGIN = 70
_NODE_WIDTH = 230
_NODE_HEIGHT = 90
_LAYER_GAP = 125
_ITEM_GAP = 45
_MIN_CANVAS_WIDTH = 720
_MIN_CANVAS_HEIGHT = 430


@dataclass(frozen=True, slots=True)
class _Point:
    x: float
    y: float


def render_svg_preview(document: DocumentIR) -> str | None:
    """Render a static SVG image from validated graph data for the local UI only."""
    if document.diagram.status is not DiagramStatus.GENERATED or not document.graph.nodes:
        return None

    layers = _build_layers(document)
    left_to_right = document.classification.effective_type is DocumentType.ARCHITECTURE
    positions, width, height = _layout(layers, left_to_right=left_to_right)
    node_by_id = {node.id: node for node in document.graph.nodes}

    parts = [
        (
            f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}" '
            'role="img" aria-label="Erkanntes Diagramm" '
            'style="width:100%;height:auto;min-height:420px;background:#fbfdff;'
            'border:1px solid #dbe5ec;border-radius:14px">'
        ),
        '<rect width="100%" height="100%" fill="#fbfdff" rx="14"/>',
    ]
    for edge in document.graph.edges:
        source = positions[edge.source]
        target = positions[edge.target]
        parts.extend(_render_edge(source, target, edge.label, edge.directed, edge.uncertain))
    for node_id in sorted(node_by_id, key=_id_number):
        node = node_by_id[node_id]
        parts.extend(
            _render_node(
                positions[node_id],
                node.label + (" (?)" if node.uncertain else ""),
                node.kind,
                node.uncertain,
            )
        )
    parts.append("</svg>")
    return "".join(parts)


def _build_layers(document: DocumentIR) -> list[list[str]]:
    node_ids = sorted((node.id for node in document.graph.nodes), key=_id_number)
    indegree = dict.fromkeys(node_ids, 0)
    outgoing: dict[str, list[str]] = defaultdict(list)
    neighbors: dict[str, list[str]] = defaultdict(list)
    for edge in document.graph.edges:
        neighbors[edge.source].append(edge.target)
        neighbors[edge.target].append(edge.source)
        if edge.directed:
            outgoing[edge.source].append(edge.target)
            indegree[edge.target] += 1

    depth = _assign_directed_depths(node_ids, indegree, outgoing)
    _assign_remaining_depths(node_ids, neighbors, depth)

    grouped: dict[int, list[str]] = defaultdict(list)
    for node_id in node_ids:
        grouped[depth[node_id]].append(node_id)
    return [grouped[index] for index in sorted(grouped)]


def _assign_directed_depths(
    node_ids: list[str],
    indegree: dict[str, int],
    outgoing: dict[str, list[str]],
) -> dict[str, int]:
    roots = deque(node_id for node_id in node_ids if indegree[node_id] == 0)
    depth = dict.fromkeys(roots, 0)
    remaining_indegree = dict(indegree)
    while roots:
        source = roots.popleft()
        for target in sorted(outgoing[source], key=_id_number):
            depth[target] = max(depth.get(target, 0), depth[source] + 1)
            remaining_indegree[target] -= 1
            if remaining_indegree[target] == 0:
                roots.append(target)
    return depth


def _assign_remaining_depths(
    node_ids: list[str],
    neighbors: dict[str, list[str]],
    depth: dict[str, int],
) -> None:
    unassigned = [node_id for node_id in node_ids if node_id not in depth]
    next_depth = max(depth.values(), default=-1) + 1
    while unassigned:
        start = unassigned[0]
        depth[start] = next_depth
        queue = deque([start])
        while queue:
            source = queue.popleft()
            for target in sorted(neighbors[source], key=_id_number):
                if target in depth:
                    continue
                depth[target] = depth[source] + 1
                queue.append(target)
        unassigned = [node_id for node_id in node_ids if node_id not in depth]
        next_depth = max(depth.values()) + 1


def _layout(layers: list[list[str]], *, left_to_right: bool) -> tuple[dict[str, _Point], int, int]:
    layer_count = len(layers)
    max_items = max(len(layer) for layer in layers)
    if left_to_right:
        width = max(
            _MIN_CANVAS_WIDTH,
            2 * _MARGIN + layer_count * _NODE_WIDTH + (layer_count - 1) * _LAYER_GAP,
        )
        height = max(
            _MIN_CANVAS_HEIGHT,
            2 * _MARGIN + max_items * _NODE_HEIGHT + (max_items - 1) * _ITEM_GAP,
        )
    else:
        width = max(
            _MIN_CANVAS_WIDTH,
            2 * _MARGIN + max_items * _NODE_WIDTH + (max_items - 1) * _ITEM_GAP,
        )
        height = max(
            _MIN_CANVAS_HEIGHT,
            2 * _MARGIN + layer_count * _NODE_HEIGHT + (layer_count - 1) * _LAYER_GAP,
        )

    positions: dict[str, _Point] = {}
    for layer_index, layer in enumerate(layers):
        if left_to_right:
            x = _MARGIN + _NODE_WIDTH / 2 + layer_index * (_NODE_WIDTH + _LAYER_GAP)
            total = len(layer) * _NODE_HEIGHT + (len(layer) - 1) * _ITEM_GAP
            top = (height - total) / 2
            for item_index, node_id in enumerate(layer):
                y = top + _NODE_HEIGHT / 2 + item_index * (_NODE_HEIGHT + _ITEM_GAP)
                positions[node_id] = _Point(x, y)
        else:
            y = _MARGIN + _NODE_HEIGHT / 2 + layer_index * (_NODE_HEIGHT + _LAYER_GAP)
            total = len(layer) * _NODE_WIDTH + (len(layer) - 1) * _ITEM_GAP
            left = (width - total) / 2
            for item_index, node_id in enumerate(layer):
                x = left + _NODE_WIDTH / 2 + item_index * (_NODE_WIDTH + _ITEM_GAP)
                positions[node_id] = _Point(x, y)
    return positions, width, height


def _render_edge(
    source: _Point,
    target: _Point,
    label: str | None,
    directed: bool,
    uncertain: bool,
) -> list[str]:
    dx = target.x - source.x
    dy = target.y - source.y
    distance = max(math.hypot(dx, dy), 1.0)
    unit_x = dx / distance
    unit_y = dy / distance
    padding = 62
    start = _Point(source.x + unit_x * padding, source.y + unit_y * padding)
    end = _Point(target.x - unit_x * padding, target.y - unit_y * padding)
    stroke = "#d97706" if uncertain else "#3b6478"
    dash = ' stroke-dasharray="9 7"' if uncertain else ""
    parts = [
        (
            f'<line x1="{start.x:.1f}" y1="{start.y:.1f}" x2="{end.x:.1f}" '
            f'y2="{end.y:.1f}" stroke="{stroke}" stroke-width="3"{dash}/>'
        )
    ]
    if directed:
        back = _Point(end.x - unit_x * 15, end.y - unit_y * 15)
        side_x = -unit_y * 7
        side_y = unit_x * 7
        points = (
            f"{end.x:.1f},{end.y:.1f} "
            f"{back.x + side_x:.1f},{back.y + side_y:.1f} "
            f"{back.x - side_x:.1f},{back.y - side_y:.1f}"
        )
        parts.append(f'<polygon points="{points}" fill="{stroke}"/>')
    if label:
        value = html.escape(label + (" (?)" if uncertain else ""))
        middle_x = (start.x + end.x) / 2
        middle_y = (start.y + end.y) / 2
        box_width = min(220, max(70, len(label) * 8 + 24))
        parts.extend(
            (
                (
                    f'<rect x="{middle_x - box_width / 2:.1f}" y="{middle_y - 15:.1f}" '
                    f'width="{box_width}" height="30" rx="8" fill="#ffffff" opacity="0.94"/>'
                ),
                (
                    f'<text x="{middle_x:.1f}" y="{middle_y + 5:.1f}" text-anchor="middle" '
                    'font-family="system-ui, sans-serif" font-size="15" fill="#244554">'
                    f"{value}</text>"
                ),
            )
        )
    return parts


def _render_node(
    center: _Point,
    label: str,
    kind: NodeKind,
    uncertain: bool,
) -> list[str]:
    stroke = "#d97706" if uncertain else "#147d9b"
    fill = "#fff7e8" if uncertain else "#eaf7fb"
    if kind is NodeKind.DECISION:
        half_width = _NODE_WIDTH / 2
        half_height = _NODE_HEIGHT / 2
        points = (
            f"{center.x:.1f},{center.y - half_height:.1f} "
            f"{center.x + half_width:.1f},{center.y:.1f} "
            f"{center.x:.1f},{center.y + half_height:.1f} "
            f"{center.x - half_width:.1f},{center.y:.1f}"
        )
        shape = f'<polygon points="{points}" fill="{fill}" stroke="{stroke}" stroke-width="3"/>'
    else:
        shape = (
            f'<rect x="{center.x - _NODE_WIDTH / 2:.1f}" '
            f'y="{center.y - _NODE_HEIGHT / 2:.1f}" width="{_NODE_WIDTH}" '
            f'height="{_NODE_HEIGHT}" rx="15" fill="{fill}" stroke="{stroke}" stroke-width="3"/>'
        )
    lines = textwrap.wrap(
        label,
        width=24,
        break_long_words=False,
        break_on_hyphens=False,
    ) or [label]
    lines = lines[:3]
    first_y = center.y - (len(lines) - 1) * 11
    text_parts = [
        (
            f'<text x="{center.x:.1f}" y="{first_y:.1f}" text-anchor="middle" '
            'font-family="system-ui, sans-serif" font-size="17" font-weight="600" fill="#163743">'
        )
    ]
    for index, line in enumerate(lines):
        dy = "0" if index == 0 else "22"
        text_parts.append(f'<tspan x="{center.x:.1f}" dy="{dy}">{html.escape(line)}</tspan>')
    text_parts.append("</text>")
    return [shape, *text_parts]


def _id_number(value: str) -> int:
    return int(value[1:])
