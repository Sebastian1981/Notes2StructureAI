"""Deterministic Markdown renderers for transcript and structured notes."""

from __future__ import annotations

from notes2structure.schemas import DocumentIR, Mode


def render_transcript(document: DocumentIR) -> str:
    lines = [
        "# Transkription",
        "",
        f"- Quelle: {_escape(document.source.filename)}",
        f"- Modus: `{document.mode.value}`",
        f"- Menschliche Prüfung erforderlich: {_yes_no(document.review_required)}",
        "",
        "## Segmente",
        "",
    ]
    if document.transcript:
        for segment in document.transcript:
            lines.append(f"- **{segment.id}** (`{segment.status.value}`): {_escape(segment.text)}")
    else:
        lines.append("_Kein lesbarer Text erkannt._")
    lines.extend(_render_uncertainties(document))
    return "\n".join(lines).rstrip() + "\n"


def render_notes(document: DocumentIR) -> str:
    if document.mode is not Mode.FULL:
        message = "Structured notes are only available in full mode."
        raise ValueError(message)
    classification = document.classification
    detected_type = (
        classification.detected_type.value
        if classification.detected_type is not None
        else "nicht verfügbar"
    )
    effective_type = (
        classification.effective_type.value
        if classification.effective_type is not None
        else "nicht verfügbar"
    )
    lines = [
        "# Strukturierte Notizen",
        "",
        f"- Erkannter Typ: `{detected_type}`",
        f"- Gewünschter Typ: {_type_value(classification.requested_type)}",
        f"- Effektiver Typ: `{effective_type}`",
        f"- Begründung: {_escape(classification.reason)}",
        f"- Menschliche Prüfung erforderlich: {_yes_no(document.review_required)}",
        "",
        "## Inhalte",
        "",
    ]
    if document.sections:
        uncertain_source_ids = {
            segment.id for segment in document.transcript if segment.status.value != "clear"
        }
        for section in document.sections:
            lines.extend((f"### {_escape(section.heading)}", ""))
            for item in section.items:
                references = ", ".join(item.source_ids)
                uncertainty_marker = (
                    " **[unsicher]**" if uncertain_source_ids.intersection(item.source_ids) else ""
                )
                lines.append(
                    f"- {_escape(item.text)}{uncertainty_marker} _(Quellen: {references})_"
                )
            lines.append("")
    else:
        lines.extend(("_Keine strukturierten Notizen erkannt._", ""))

    lines.extend(("## Diagramm", ""))
    lines.append(f"- Status: `{document.diagram.status.value}`")
    if document.diagram.reason is not None:
        lines.append(f"- Grund: {_escape(document.diagram.reason)}")
    if document.warnings:
        lines.extend(("", "## Warnungen", ""))
        lines.extend(f"- {_escape(warning)}" for warning in document.warnings)
    lines.extend(_render_uncertainties(document))
    return "\n".join(lines).rstrip() + "\n"


def _render_uncertainties(document: DocumentIR) -> list[str]:
    if not document.uncertainties:
        return []
    lines = ["", "## Unsicherheiten", ""]
    for uncertainty in document.uncertainties:
        targets = ", ".join(uncertainty.target_ids)
        line = (
            f"- **{uncertainty.id}** (`{uncertainty.kind.value}`, Ziele: {targets}): "
            f"{_escape(uncertainty.message)}"
        )
        lines.append(line)
        if uncertainty.alternatives:
            alternatives = "; ".join(_escape(value) for value in uncertainty.alternatives)
            lines.append(f"  - Alternativen: {alternatives}")
    return lines


def _escape(value: str | None) -> str:
    if value is None:
        return "-"
    escaped = value.replace("\\", "\\\\").replace("<", "&lt;").replace(">", "&gt;")
    for character in "`*_{}[]()#+-.!|":
        escaped = escaped.replace(character, f"\\{character}")
    return escaped.replace("\r\n", " ").replace("\r", " ").replace("\n", " ")


def _yes_no(value: bool) -> str:
    return "ja" if value else "nein"


def _type_value(value: object) -> str:
    if value is None:
        return "`auto`"
    return f"`{value}`"
