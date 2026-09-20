"""Deterministic safe renderers for a visually cleaned note."""

from __future__ import annotations

import html
import math
import textwrap

from notes2structure.schemas import (
    CleanDocumentIR,
    LayoutShape,
    LayoutText,
    ShapeKind,
    TextAlignment,
    TextRole,
)

_FONT_SIZE = {
    TextRole.HEADING: 34,
    TextRole.BODY: 23,
    TextRole.LABEL: 21,
    TextRole.NOTE: 22,
}


def render_clean_svg(document: CleanDocumentIR) -> str:
    """Render provider-described geometry as a self-contained, inert SVG."""
    width = document.layout.canvas_width
    height = document.layout.canvas_height
    parts = [
        (
            f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}" '
            'role="img" aria-label="Optimierte handschriftliche Notiz">'
        ),
        "<defs>",
        (
            '<marker id="arrowhead" markerWidth="10" markerHeight="8" refX="9" refY="4" '
            'orient="auto" markerUnits="strokeWidth"><path d="M0,0 L10,4 L0,8 Z" '
            'fill="#1677a5"/></marker>'
        ),
        "</defs>",
        '<rect width="100%" height="100%" fill="#fffefa"/>',
    ]
    parts.extend(_render_shape(shape, width, height) for shape in document.layout.shapes)
    parts.extend(_render_text(item, width, height) for item in document.layout.texts)
    parts.append("</svg>\n")
    return "".join(parts)


def render_cleanup_transcript(document: CleanDocumentIR) -> str:
    lines = [
        "# Erkannter Inhalt",
        "",
        f"- Quelle: {_markdown_escape(document.source.filename)}",
        f"- Menschliche Prüfung erforderlich: {'ja' if document.review_required else 'nein'}",
        "",
    ]
    if document.transcript:
        lines.extend(
            f"- **{segment.id}** (`{segment.status.value}`): {_markdown_escape(segment.text)}"
            for segment in document.transcript
        )
    else:
        lines.append("_Kein lesbarer Text erkannt._")
    if document.warnings:
        lines.extend(("", "## Hinweise", ""))
        lines.extend(f"- {_markdown_escape(value)}" for value in document.warnings)
    if document.uncertainties:
        lines.extend(("", "## Unsicherheiten", ""))
        for uncertainty in document.uncertainties:
            targets = ", ".join(uncertainty.target_ids)
            lines.append(
                f"- **{uncertainty.id}** (Ziele: {targets}): "
                f"{_markdown_escape(uncertainty.message)}"
            )
    return "\n".join(lines).rstrip() + "\n"


def render_cleanup_artifacts(document: CleanDocumentIR) -> dict[str, str]:
    return {
        "optimized-note.svg": render_clean_svg(document),
        "result.json": document.model_dump_json(indent=2) + "\n",
        "transcript.md": render_cleanup_transcript(document),
    }


def _render_shape(shape: LayoutShape, width: int, height: int) -> str:
    x1, y1 = _point(shape.x1, shape.y1, width, height)
    x2, y2 = _point(shape.x2, shape.y2, width, height)
    stroke = "#e88732" if shape.uncertain else "#1677a5"
    dash = ' stroke-dasharray="10 7"' if shape.uncertain else ""
    common = (
        f' fill="none" stroke="{stroke}" stroke-width="3"{dash} '
        'stroke-linecap="round" stroke-linejoin="round"'
    )
    if shape.kind in {ShapeKind.RECTANGLE, ShapeKind.ROUNDED_RECTANGLE}:
        radius = 16 if shape.kind is ShapeKind.ROUNDED_RECTANGLE else 3
        return (
            f'<rect x="{x1}" y="{y1}" width="{x2 - x1}" height="{y2 - y1}" rx="{radius}"{common}/>'
        )
    if shape.kind is ShapeKind.ELLIPSE:
        return (
            f'<ellipse cx="{(x1 + x2) / 2:g}" cy="{(y1 + y2) / 2:g}" '
            f'rx="{(x2 - x1) / 2:g}" ry="{(y2 - y1) / 2:g}"{common}/>'
        )
    marker = ' marker-end="url(#arrowhead)"' if shape.kind is ShapeKind.ARROW else ""
    return f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}"{common}{marker}/>'


def _render_text(item: LayoutText, width: int, height: int) -> str:
    x, y = _point(item.x, item.y, width, height)
    box_width = max(1.0, item.width * width / 1_000)
    font_size = _FONT_SIZE[item.role]
    scaled_font = max(13, round(font_size * min(width, height) / 900))
    max_chars = max(4, math.floor(box_width / (scaled_font * 0.56)))
    lines = textwrap.wrap(
        item.text.replace("\r", " ").replace("\n", " "),
        width=max_chars,
        break_long_words=False,
        break_on_hyphens=False,
    ) or [item.text]
    anchor = "middle" if item.alignment is TextAlignment.CENTER else "start"
    text_x = x + box_width / 2 if anchor == "middle" else x
    weight = "700" if item.role is TextRole.HEADING else "500"
    color = "#9b5b20" if item.uncertain else "#17324d"
    rendered_lines: list[str] = []
    for index, line in enumerate(lines):
        dy = scaled_font * 1.25 if index else 0
        rendered_lines.append(f'<tspan x="{text_x:g}" dy="{dy:g}">{html.escape(line)}</tspan>')
    return (
        f'<text x="{text_x:g}" y="{y + scaled_font:g}" text-anchor="{anchor}" '
        f'font-family="Segoe UI, Arial, sans-serif" font-size="{scaled_font}" '
        f'font-weight="{weight}" fill="{color}">{"".join(rendered_lines)}</text>'
    )


def _point(x: int, y: int, width: int, height: int) -> tuple[float, float]:
    return round(x * width / 1_000, 2), round(y * height / 1_000, 2)


def _markdown_escape(value: str) -> str:
    escaped = value.replace("\\", "\\\\").replace("<", "&lt;").replace(">", "&gt;")
    for character in "`*_{}[]()#+-.!|":
        escaped = escaped.replace(character, f"\\{character}")
    return escaped.replace("\r\n", " ").replace("\r", " ").replace("\n", " ")
