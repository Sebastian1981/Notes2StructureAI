"""Local Gradio frontend for previewing an analysis before saving it."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Final

import gradio as gr

from notes2structure.application import (
    AnalysisPreview,
    build_provider,
    create_preview,
    save_preview,
)
from notes2structure.config import load_configuration
from notes2structure.errors import Notes2StructureError
from notes2structure.providers.base import AnalysisOptions
from notes2structure.schemas import KnownType, Mode

AUTO = "Automatisch erkennen"
TRANSCRIBE = "Nur Reinschrift"
NOTES = "Strukturierte Notizen"
MINDMAP = "Mindmap"
PROCESS = "Prozessdiagramm"
ARCHITECTURE = "Architekturdiagramm"
OUTPUT_CHOICES: Final = (AUTO, TRANSCRIBE, NOTES, MINDMAP, PROCESS, ARCHITECTURE)

_CSS = """
.n2s-shell { max-width: 1450px; margin: 0 auto; }
.n2s-hero { padding: 0.5rem 0 0.25rem; }
.n2s-status { border-left: 4px solid #168aad; padding-left: 0.9rem; }
.n2s-actions button { min-height: 44px; }
"""


@dataclass(frozen=True, slots=True)
class PreviewView:
    """Display-only values derived from a validated preview."""

    status: str
    transcript: str
    notes: str
    diagram: str
    diagram_source: str
    result_json: str


def selection_to_options(selection: str) -> AnalysisOptions:
    """Map one explicit UI choice to the existing provider contract."""
    choices = {
        AUTO: AnalysisOptions(Mode.FULL, None),
        TRANSCRIBE: AnalysisOptions(Mode.TRANSCRIBE, None),
        NOTES: AnalysisOptions(Mode.FULL, KnownType.NOTES),
        MINDMAP: AnalysisOptions(Mode.FULL, KnownType.MINDMAP),
        PROCESS: AnalysisOptions(Mode.FULL, KnownType.PROCESS),
        ARCHITECTURE: AnalysisOptions(Mode.FULL, KnownType.ARCHITECTURE),
    }
    try:
        return choices[selection]
    except KeyError as error:
        message = "Die gewählte Ausgabeart ist ungültig."
        raise ValueError(message) from error


def preview_to_view(preview: AnalysisPreview) -> PreviewView:
    """Prepare safe Markdown and source views without writing files."""
    document = preview.document
    review = (
        "⚠️ Bitte prüfe die markierten Unsicherheiten."
        if document.review_required
        else "✅ Keine fachliche Prüfung markiert."
    )
    status = f"### Analyse bereit\n\n{review}\n\nDas Ergebnis ist noch nicht gespeichert."
    notes = preview.artifacts.get(
        "notes.md",
        "_Für die reine Transkription werden keine strukturierten Notizen erzeugt._\n",
    )
    diagram_source = preview.artifacts.get("diagram.mmd", "")
    if diagram_source:
        diagram = f"```mermaid\n{diagram_source.rstrip()}\n```\n"
    else:
        reason = document.diagram.reason or "Für diese Auswahl ist kein Diagramm vorgesehen."
        diagram = f"_Kein Diagramm erzeugt: {reason}_\n"
    return PreviewView(
        status=status,
        transcript=preview.artifacts["transcript.md"],
        notes=notes,
        diagram=diagram,
        diagram_source=diagram_source,
        result_json=preview.artifacts["result.json"],
    )


def _analyze(
    image_path: str | None,
    selection: str,
    allow_remote: bool,
    env_file: str,
) -> tuple[AnalysisPreview, str, str, str, str, str, str, gr.Button]:
    if image_path is None:
        message = "Bitte füge zuerst ein PNG- oder JPEG-Bild ein."
        raise gr.Error(message)
    env_path = Path(env_file.strip()) if env_file.strip() else None
    try:
        provider = build_provider(load_configuration(env_path))
        preview = create_preview(
            Path(image_path),
            selection_to_options(selection),
            provider,
            allow_remote=allow_remote,
        )
        view = preview_to_view(preview)
    except Notes2StructureError as error:
        raise gr.Error(str(error)) from error
    except ValueError as error:
        raise gr.Error(str(error)) from error
    except Exception as error:
        message = "Unerwarteter interner Fehler bei der Analyse."
        raise gr.Error(message) from error
    return (
        preview,
        view.status,
        view.transcript,
        view.notes,
        view.diagram,
        view.diagram_source,
        view.result_json,
        gr.Button(interactive=True),
    )


def _save(
    preview: AnalysisPreview | None,
    output_dir: str,
) -> tuple[str, gr.Button]:
    if preview is None:
        message = "Es gibt noch kein Analyseergebnis zum Speichern."
        raise gr.Error(message)
    if not output_dir.strip():
        message = "Bitte gib ein Ausgabeverzeichnis an."
        raise gr.Error(message)
    try:
        result_dir = save_preview(preview, Path(output_dir.strip()))
    except Notes2StructureError as error:
        raise gr.Error(str(error)) from error
    except Exception as error:
        message = "Unerwarteter interner Fehler beim Speichern."
        raise gr.Error(message) from error
    return (
        f"### Gespeichert\n\n✅ Ergebnisordner: `{result_dir}`",
        gr.Button(interactive=False),
    )


def _reset_preview() -> tuple[None, str, str, str, str, str, str, gr.Button]:
    return (
        None,
        "### Bereit\n\nFüge ein Bild ein und wähle die gewünschte Ausgabe.",
        "",
        "",
        "",
        "",
        "",
        gr.Button(interactive=False),
    )


def _discard() -> tuple[None, None, str, str, str, str, str, str, gr.Button]:
    reset = _reset_preview()
    return (reset[0], None, *reset[1:])


def build_frontend() -> gr.Blocks:
    """Build the local-only showcase frontend."""
    with gr.Blocks(
        title="Notes2StructureAI",
        analytics_enabled=False,
        delete_cache=(86_400, 86_400),
    ) as demo:
        preview_state = gr.State(value=None)
        with gr.Column(elem_classes="n2s-shell"):
            gr.Markdown(
                "# Notes2StructureAI\n"
                "Handschrift und Skizzen lokal auswählen, prüfen und erst dann speichern.",
                elem_classes="n2s-hero",
            )
            with gr.Row(equal_height=False):
                with gr.Column(scale=5):
                    image = gr.Image(
                        label="1. Bild einfügen",
                        sources=["upload", "clipboard"],
                        type="filepath",
                        format="png",
                        height=330,
                        buttons=["fullscreen"],
                        placeholder="PNG/JPEG hier ablegen oder aus der Zwischenablage einfügen",
                    )
                    selection = gr.Radio(
                        choices=OUTPUT_CHOICES,
                        value=AUTO,
                        label="2. Gewünschte Ausgabe",
                        info="Automatisch erkennt den Dokumenttyp; eine Vorgabe dient als Hinweis.",
                    )
                    allow_remote = gr.Checkbox(
                        value=False,
                        label="Bildübertragung an OpenAI für diese Analyse erlauben",
                        info=(
                            "Die Oberfläche läuft lokal; die Bildanalyse verwendet den "
                            "konfigurierten externen Provider."
                        ),
                    )
                    with gr.Accordion("Lokale Einstellungen", open=False):
                        env_file = gr.Textbox(value=".env", label="Env-Datei")
                        output_dir = gr.Textbox(
                            value="local-data/output",
                            label="Ausgabeverzeichnis",
                        )
                    with gr.Row(elem_classes="n2s-actions"):
                        analyze_button = gr.Button("Jetzt analysieren", variant="primary")
                        save_button = gr.Button("Ergebnis speichern", interactive=False)
                        discard_button = gr.Button("Verwerfen")
                with gr.Column(scale=7):
                    status = gr.Markdown(
                        "### Bereit\n\nFüge ein Bild ein und wähle die gewünschte Ausgabe.",
                        elem_classes="n2s-status",
                    )
                    with gr.Tabs():
                        with gr.Tab("Reinschrift"):
                            transcript = gr.Markdown(buttons=["copy"])
                        with gr.Tab("Notizen"):
                            notes = gr.Markdown(buttons=["copy"])
                        with gr.Tab("Diagramm"):
                            diagram = gr.Markdown()
                            with gr.Accordion("Mermaid-Quelltext", open=False):
                                diagram_source = gr.Code(
                                    language="markdown",
                                    interactive=False,
                                    buttons=["copy", "download"],
                                    lines=12,
                                )
                        with gr.Tab("JSON"):
                            result_json = gr.Code(
                                language="json",
                                interactive=False,
                                buttons=["copy", "download"],
                                lines=24,
                            )

        preview_outputs = [
            preview_state,
            status,
            transcript,
            notes,
            diagram,
            diagram_source,
            result_json,
            save_button,
        ]
        analyze_button.click(
            _analyze,
            inputs=[image, selection, allow_remote, env_file],
            outputs=preview_outputs,
            api_visibility="private",
            concurrency_limit=1,
        )
        save_button.click(
            _save,
            inputs=[preview_state, output_dir],
            outputs=[status, save_button],
            api_visibility="private",
        )
        discard_button.click(
            _discard,
            outputs=[image, *preview_outputs],
            api_visibility="private",
        )
        image.change(
            _reset_preview,
            outputs=preview_outputs,
            api_visibility="private",
        )
        selection.change(
            _reset_preview,
            outputs=preview_outputs,
            api_visibility="private",
        )
    return demo.queue(default_concurrency_limit=1, max_size=4, api_open=False)


def main() -> None:
    """Launch the frontend only on the local loopback interface."""
    demo = build_frontend()
    demo.launch(
        server_name="127.0.0.1",
        inbrowser=True,
        share=False,
        show_error=False,
        max_file_size="20mb",
        enable_monitoring=False,
        footer_links=[],
        mcp_server=False,
        css=_CSS,
    )


if __name__ == "__main__":
    main()
