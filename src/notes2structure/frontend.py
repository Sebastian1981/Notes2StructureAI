"""Local Gradio frontend for previewing an analysis before saving it."""

from __future__ import annotations

import html
from dataclasses import dataclass
from pathlib import Path

import gradio as gr

from notes2structure.application import (
    AnalysisPreview,
    build_provider,
    create_preview,
    reinterpret_preview,
    save_preview,
)
from notes2structure.config import load_configuration
from notes2structure.errors import Notes2StructureError
from notes2structure.providers.base import AnalysisOptions
from notes2structure.renderers.svg import render_svg_preview
from notes2structure.schemas import DiagramStatus, DocumentType, KnownType, Mode

MINDMAP = "Mindmap"
PROCESS = "Prozessdiagramm"
ARCHITECTURE = "Architekturdiagramm"

_CSS = """
.n2s-shell { max-width: 1450px; margin: 0 auto; }
.n2s-hero { padding: 0.5rem 0 0.25rem; }
.n2s-status { border-left: 4px solid #168aad; padding-left: 0.9rem; }
.n2s-actions button { min-height: 44px; }
.n2s-empty-diagram { padding: 2rem; color: #516873; }
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


def _reinterpretation_type(selection: str) -> KnownType:
    choices = {
        MINDMAP: KnownType.MINDMAP,
        PROCESS: KnownType.PROCESS,
        ARCHITECTURE: KnownType.ARCHITECTURE,
    }
    try:
        return choices[selection]
    except KeyError as error:
        message = "Die gewählte Neuinterpretation ist ungültig."
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
    diagram = render_svg_preview(document)
    if diagram is None:
        reason = document.diagram.reason or "Für diese Auswahl ist kein Diagramm vorgesehen."
        diagram = f'<p class="n2s-empty-diagram">Kein Diagramm erzeugt: {html.escape(reason)}</p>'
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
    allow_remote: bool,
    env_file: str,
) -> tuple[
    AnalysisPreview,
    str,
    str,
    str,
    str,
    str,
    str,
    gr.Button,
    gr.Button,
    gr.Button,
    gr.Button,
]:
    if image_path is None:
        message = "Bitte füge zuerst ein PNG- oder JPEG-Bild ein."
        raise gr.Error(message)
    env_path = Path(env_file.strip()) if env_file.strip() else None
    try:
        provider = build_provider(load_configuration(env_path))
        preview = create_preview(
            Path(image_path),
            AnalysisOptions(Mode.FULL, None),
            provider,
            allow_remote=allow_remote,
        )
    except Notes2StructureError as error:
        raise gr.Error(str(error)) from error
    except ValueError as error:
        raise gr.Error(str(error)) from error
    except Exception as error:
        message = "Unerwarteter interner Fehler bei der Analyse."
        raise gr.Error(message) from error
    return _preview_outputs(preview)


def _reinterpret(
    preview: AnalysisPreview | None,
    selection: str,
    allow_remote: bool,
    env_file: str,
) -> tuple[
    AnalysisPreview,
    str,
    str,
    str,
    str,
    str,
    str,
    gr.Button,
    gr.Button,
    gr.Button,
    gr.Button,
]:
    if preview is None:
        message = "Bitte führe zuerst die vollständige Analyse aus."
        raise gr.Error(message)
    requested_type = _reinterpretation_type(selection)
    current_type = preview.document.classification.effective_type
    same_requested_type = preview.document.classification.requested_type is requested_type
    current_diagram_exists = preview.document.diagram.status is DiagramStatus.GENERATED
    if current_type == DocumentType(requested_type.value) and (
        same_requested_type or current_diagram_exists
    ):
        return _preview_outputs(
            preview,
            status=(
                "### Bereits vorhanden\n\n"
                f"✅ Das aktuelle Ergebnis ist bereits als {selection} dargestellt. "
                "Es wurde kein weiterer OpenAI-Aufruf ausgeführt."
            ),
        )
    env_path = Path(env_file.strip()) if env_file.strip() else None
    try:
        provider = build_provider(load_configuration(env_path))
        updated = reinterpret_preview(
            preview,
            requested_type,
            provider,
            allow_remote=allow_remote,
        )
    except Notes2StructureError as error:
        raise gr.Error(str(error)) from error
    except ValueError as error:
        raise gr.Error(str(error)) from error
    except Exception as error:
        message = "Unerwarteter interner Fehler bei der Neuinterpretation."
        raise gr.Error(message) from error
    return _preview_outputs(
        updated,
        status=(
            f"### {selection} bereit\n\n"
            "✅ Aus dem vorhandenen Analyse-JSON neu interpretiert; das Bild wurde nicht erneut "
            "übertragen. Das Ergebnis ist noch nicht gespeichert."
        ),
    )


def _preview_outputs(
    preview: AnalysisPreview,
    *,
    status: str | None = None,
) -> tuple[
    AnalysisPreview,
    str,
    str,
    str,
    str,
    str,
    str,
    gr.Button,
    gr.Button,
    gr.Button,
    gr.Button,
]:
    view = preview_to_view(preview)
    return (
        preview,
        status or view.status,
        view.transcript,
        view.notes,
        view.diagram,
        view.diagram_source,
        view.result_json,
        gr.Button(interactive=True),
        gr.Button(interactive=True),
        gr.Button(interactive=True),
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


def _reset_preview() -> tuple[
    None,
    str,
    str,
    str,
    str,
    str,
    str,
    gr.Button,
    gr.Button,
    gr.Button,
    gr.Button,
]:
    return (
        None,
        "### Bereit\n\nFüge ein Bild ein und starte die vollständige Analyse.",
        "",
        "",
        "",
        "",
        "",
        gr.Button(interactive=False),
        gr.Button(interactive=False),
        gr.Button(interactive=False),
        gr.Button(interactive=False),
    )


def _discard() -> tuple[
    None,
    None,
    str,
    str,
    str,
    str,
    str,
    str,
    gr.Button,
    gr.Button,
    gr.Button,
    gr.Button,
]:
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
                    gr.Markdown(
                        "**2. Vollständig analysieren**  \n"
                        "Ein OpenAI-Aufruf erzeugt gemeinsam Reinschrift, strukturierte Notizen "
                        "und das automatisch passende Diagramm."
                    )
                    allow_remote = gr.Checkbox(
                        value=False,
                        label="Übertragung an OpenAI für diese Analyse erlauben",
                        info=(
                            "Die erste Analyse überträgt das Bild. Optionale Neuinterpretationen "
                            "übertragen nur das bereits validierte Analyse-JSON."
                        ),
                    )
                    with gr.Accordion("Lokale Einstellungen", open=False):
                        env_file = gr.Textbox(value=".env", label="Env-Datei")
                        output_dir = gr.Textbox(
                            value="local-data/output",
                            label="Ausgabeverzeichnis",
                        )
                    with gr.Row(elem_classes="n2s-actions"):
                        analyze_button = gr.Button("Vollständig analysieren", variant="primary")
                        save_button = gr.Button("Ergebnis speichern", interactive=False)
                        discard_button = gr.Button("Verwerfen")
                with gr.Column(scale=7):
                    status = gr.Markdown(
                        "### Bereit\n\nFüge ein Bild ein und starte die vollständige Analyse.",
                        elem_classes="n2s-status",
                    )
                    with gr.Tabs():
                        with gr.Tab("Reinschrift"):
                            transcript = gr.Markdown(buttons=["copy"])
                        with gr.Tab("Notizen"):
                            notes = gr.Markdown(buttons=["copy"])
                        with gr.Tab("Diagramm"):
                            diagram = gr.HTML(
                                min_height=430,
                                apply_default_css=False,
                            )
                            with gr.Accordion("Mermaid-Quelltext", open=False):
                                diagram_source = gr.Code(
                                    language="markdown",
                                    interactive=False,
                                    buttons=["copy", "download"],
                                    lines=12,
                                )
                            gr.Markdown(
                                "**Optional anders darstellen**  \n"
                                "Jede Neuinterpretation kann einen zusätzlichen OpenAI-Aufruf "
                                "auslösen, verwendet aber nicht erneut das Bild."
                            )
                            with gr.Row():
                                mindmap_button = gr.Button(
                                    "Als Mindmap",
                                    interactive=False,
                                )
                                process_button = gr.Button(
                                    "Als Prozess",
                                    interactive=False,
                                )
                                architecture_button = gr.Button(
                                    "Als Architektur",
                                    interactive=False,
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
            mindmap_button,
            process_button,
            architecture_button,
        ]
        analyze_button.click(
            _analyze,
            inputs=[image, allow_remote, env_file],
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
        for button, selection in (
            (mindmap_button, MINDMAP),
            (process_button, PROCESS),
            (architecture_button, ARCHITECTURE),
        ):
            target = gr.State(value=selection)
            button.click(
                _reinterpret,
                inputs=[preview_state, target, allow_remote, env_file],
                outputs=preview_outputs,
                api_visibility="private",
                concurrency_limit=1,
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
