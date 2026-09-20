"""Local Gradio frontend for visually cleaning handwritten notes."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import gradio as gr

from notes2structure.application import (
    CleanupPreview,
    build_provider,
    create_cleanup_preview,
    save_cleanup_preview,
)
from notes2structure.config import load_configuration
from notes2structure.errors import Notes2StructureError

_CSS = """
.n2s-shell { max-width: 1450px; margin: 0 auto; }
.n2s-hero { padding: 0.5rem 0 0.25rem; }
.n2s-status { border-left: 4px solid #168aad; padding-left: 0.9rem; }
.n2s-actions button { min-height: 44px; }
.n2s-clean-preview svg { width: 100%; height: auto; min-height: 430px; max-height: 70vh; }
"""


@dataclass(frozen=True, slots=True)
class PreviewView:
    """Display-only values derived from a validated cleanup preview."""

    status: str
    optimized_note: str
    transcript: str
    result_json: str


def preview_to_view(preview: CleanupPreview) -> PreviewView:
    """Prepare the cleaned page and supporting review data without writing files."""
    document = preview.document
    review = (
        "⚠️ Bitte prüfe die orange markierten oder als unsicher erkannten Stellen."
        if document.review_required
        else "✅ Alle erkannten Inhalte wurden als eindeutig eingestuft."
    )
    return PreviewView(
        status=(
            f"### Optimierte Notiz bereit\n\n{review}\n\nDas Ergebnis ist noch nicht gespeichert."
        ),
        optimized_note=preview.artifacts["optimized-note.svg"],
        transcript=preview.artifacts["transcript.md"],
        result_json=preview.artifacts["result.json"],
    )


def _optimize(
    image_path: str | None,
    allow_remote: bool,
    env_file: str,
) -> tuple[CleanupPreview, str, str, str, str, gr.Button]:
    if image_path is None:
        message = "Bitte füge zuerst ein PNG- oder JPEG-Bild ein."
        raise gr.Error(message)
    env_path = Path(env_file.strip()) if env_file.strip() else None
    try:
        provider = build_provider(load_configuration(env_path))
        preview = create_cleanup_preview(
            Path(image_path),
            provider,
            allow_remote=allow_remote,
        )
    except Notes2StructureError as error:
        raise gr.Error(str(error)) from error
    except ValueError as error:
        raise gr.Error(str(error)) from error
    except Exception as error:
        message = "Unerwarteter interner Fehler bei der Optimierung."
        raise gr.Error(message) from error
    view = preview_to_view(preview)
    return (
        preview,
        view.status,
        view.optimized_note,
        view.transcript,
        view.result_json,
        gr.Button(interactive=True),
    )


def _save(preview: CleanupPreview | None, output_dir: str) -> tuple[str, gr.Button]:
    if preview is None:
        message = "Es gibt noch keine optimierte Notiz zum Speichern."
        raise gr.Error(message)
    if not output_dir.strip():
        message = "Bitte gib ein Ausgabeverzeichnis an."
        raise gr.Error(message)
    try:
        result_dir = save_cleanup_preview(preview, Path(output_dir.strip()))
    except Notes2StructureError as error:
        raise gr.Error(str(error)) from error
    except Exception as error:
        message = "Unerwarteter interner Fehler beim Speichern."
        raise gr.Error(message) from error
    return (
        f"### Gespeichert\n\n✅ Optimierte Notiz: `{result_dir / 'optimized-note.svg'}`",
        gr.Button(interactive=False),
    )


def _reset_preview() -> tuple[None, str, str, str, str, gr.Button]:
    return (
        None,
        "### Bereit\n\nFüge ein Bild ein und lasse deine Notiz aufräumen.",
        "",
        "",
        "",
        gr.Button(interactive=False),
    )


def _discard() -> tuple[None, None, str, str, str, str, gr.Button]:
    reset = _reset_preview()
    return (reset[0], None, *reset[1:])


def build_frontend() -> gr.Blocks:
    """Build the local-only note-cleanup frontend."""
    with gr.Blocks(
        title="Notes2StructureAI",
        analytics_enabled=False,
        delete_cache=(86_400, 86_400),
    ) as demo:
        preview_state = gr.State(value=None)
        with gr.Column(elem_classes="n2s-shell"):
            gr.Markdown(
                "# Notes2StructureAI\n"
                "Aus deiner handschriftlichen Seite wird eine saubere digitale Notiz - "
                "ohne sie in einen bestimmten Diagrammtyp zu zwingen.",
                elem_classes="n2s-hero",
            )
            with gr.Row(equal_height=False):
                with gr.Column(scale=5):
                    image = gr.Image(
                        label="1. Handschriftliche Notiz einfügen",
                        sources=["upload", "clipboard"],
                        type="filepath",
                        format="png",
                        height=380,
                        buttons=["fullscreen"],
                        placeholder="PNG/JPEG hier ablegen oder aus OneNote einfügen",
                    )
                    gr.Markdown(
                        "**2. Notiz optimieren**  \n"
                        "Text, Anordnung, Kästen, Linien und Pfeile bleiben erhalten und werden "
                        "als saubere digitale Seite neu gezeichnet."
                    )
                    allow_remote = gr.Checkbox(
                        value=False,
                        label="Übertragung an OpenAI für diese Optimierung erlauben",
                        info="Es wird genau ein normalisiertes Bild an OpenAI übertragen.",
                    )
                    with gr.Accordion("Lokale Einstellungen", open=False):
                        env_file = gr.Textbox(value=".env", label="Env-Datei")
                        output_dir = gr.Textbox(
                            value="local-data/output",
                            label="Ausgabeverzeichnis",
                        )
                    with gr.Row(elem_classes="n2s-actions"):
                        optimize_button = gr.Button("Notiz optimieren", variant="primary")
                        save_button = gr.Button("Ergebnis speichern", interactive=False)
                        discard_button = gr.Button("Verwerfen")
                with gr.Column(scale=7):
                    status = gr.Markdown(
                        "### Bereit\n\nFüge ein Bild ein und lasse deine Notiz aufräumen.",
                        elem_classes="n2s-status",
                    )
                    with gr.Tabs():
                        with gr.Tab("Optimierte Notiz"):
                            optimized_note = gr.HTML(
                                min_height=480,
                                apply_default_css=False,
                                elem_classes="n2s-clean-preview",
                            )
                        with gr.Tab("Erkannter Inhalt"):
                            transcript = gr.Markdown(buttons=["copy"])
                        with gr.Tab("Technische Details"):
                            result_json = gr.Code(
                                language="json",
                                interactive=False,
                                buttons=["copy", "download"],
                                lines=24,
                            )

        preview_outputs = [
            preview_state,
            status,
            optimized_note,
            transcript,
            result_json,
            save_button,
        ]
        optimize_button.click(
            _optimize,
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
