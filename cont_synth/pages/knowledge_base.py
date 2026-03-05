import reflex as rx
from cont_synth.state import State


def _document_row(doc) -> rx.Component:
    """Single row in the documents table."""
    return rx.table.row(
        rx.table.cell(
            rx.hstack(
                rx.icon("file-text", size=14, color="var(--gray-9)"),
                rx.text(doc.filename, size="2", weight="medium"),
                align="center",
                spacing="2",
            )
        ),
        rx.table.cell(rx.text(doc.upload_date, size="2", color="var(--gray-11)")),
        rx.table.cell(
            rx.badge(
                rx.hstack(
                    rx.icon("layers", size=12),
                    rx.text(doc.chunk_count.to_string(), size="1"),
                    spacing="1",
                    align="center",
                ),
                color_scheme="blue",
                variant="soft",
            )
        ),
        rx.table.cell(
            rx.alert_dialog.root(
                rx.alert_dialog.trigger(
                    rx.icon_button(
                        rx.icon("trash-2", size=14),
                        variant="ghost",
                        color_scheme="red",
                        size="1",
                        title="Delete document",
                    )
                ),
                rx.alert_dialog.content(
                    rx.alert_dialog.title("Delete Document"),
                    rx.alert_dialog.description(
                        rx.text(
                            "Delete ",
                            rx.el.strong(doc.filename),
                            " and all its indexed chunks? This cannot be undone.",
                            size="2",
                        )
                    ),
                    rx.flex(
                        rx.alert_dialog.cancel(
                            rx.button("Cancel", variant="soft", color_scheme="gray")
                        ),
                        rx.alert_dialog.action(
                            rx.button(
                                "Delete",
                                color_scheme="red",
                                on_click=State.delete_kb_document(doc.id),
                            )
                        ),
                        spacing="3",
                        justify="end",
                        margin_top="16px",
                    ),
                    max_width="420px",
                ),
            )
        ),
        align="center",
    )


def _upload_zone() -> rx.Component:
    """Drag-and-drop upload area."""
    return rx.upload(
        rx.vstack(
            rx.cond(
                State.kb_is_uploading,
                rx.hstack(
                    rx.spinner(size="3"),
                    rx.text("Processing & indexing…", size="3", color="var(--gray-11)"),
                    align="center",
                    spacing="3",
                ),
                rx.vstack(
                    rx.icon("upload-cloud", size=36, color="var(--gray-8)"),
                    rx.text(
                        "Drop a PDF or TXT file here, or click to browse",
                        size="3",
                        color="var(--gray-11)",
                        weight="medium",
                    ),
                    rx.text(
                        "Files are chunked and indexed with all-MiniLM-L6-v2 (384 dims)",
                        size="1",
                        color="var(--gray-9)",
                    ),
                    align="center",
                    spacing="2",
                ),
            ),
            align="center",
            justify="center",
            min_height="130px",
            width="100%",
        ),
        id="kb_upload",
        multiple=False,
        accept={".pdf": ["application/pdf"], ".txt": ["text/plain"]},
        on_drop=State.handle_kb_upload(rx.upload_files(upload_id="kb_upload")),
        border="2px dashed var(--gray-6)",
        border_radius="10px",
        background_color="var(--gray-2)",
        width="100%",
        _hover={"border_color": "var(--blue-7)", "background_color": "var(--blue-2)"},
        cursor="pointer",
        padding="12px",
    )


def render_knowledge_base() -> rx.Component:
    return rx.vstack(
        # Header
        rx.box(
            rx.text("Product Context", weight="bold", size="6"),
            rx.text(
                "Upload product documentation to give the synthesis engine workspace-aware context. "
                "Documents are chunked, embedded, and retrieved via semantic similarity during synthesis.",
                color="gray",
                size="3",
            ),
            margin_bottom="10px",
        ),
        rx.divider(),

        # Upload section
        rx.vstack(
            rx.text("Add Document", weight="medium", size="4"),
            _upload_zone(),
            rx.cond(
                State.kb_upload_error != "",
                rx.hstack(
                    rx.icon("circle-alert", size=14, color="#E5484D"),
                    rx.text(State.kb_upload_error, size="2", color="#E5484D"),
                    padding="8px 12px",
                    background_color="var(--red-2)",
                    border="1px solid var(--red-6)",
                    border_radius="6px",
                    width="100%",
                    align="center",
                    spacing="2",
                ),
            ),
            width="100%",
            spacing="3",
            padding="20px",
            background_color="var(--gray-1)",
            border="1px solid var(--gray-4)",
            border_radius="10px",
        ),

        # Documents table
        rx.vstack(
            rx.hstack(
                rx.text("Indexed Documents", weight="medium", size="4"),
                rx.badge(
                    State.kb_document_count.to_string(),
                    color_scheme="gray",
                    variant="soft",
                ),
                rx.spacer(),
                rx.tooltip(
                    rx.button(
                        rx.icon("refresh-cw", size=14),
                        "Re-process All",
                        variant="soft",
                        color_scheme="gray",
                        size="2",
                        on_click=State.reprocess_all_kb_documents,
                        loading=State.kb_is_reprocessing,
                        disabled=State.kb_documents.length() == 0,
                    ),
                    content="Sanitize PDF artifacts and re-embed all stored chunks",
                ),
                align="center",
                spacing="2",
                width="100%",
            ),
            rx.cond(
                State.kb_documents.length() == 0,
                rx.box(
                    rx.vstack(
                        rx.icon("inbox", size=32, color="var(--gray-7)"),
                        rx.text(
                            "No documents yet. Upload a PDF or TXT to get started.",
                            size="2",
                            color="var(--gray-9)",
                        ),
                        align="center",
                        spacing="2",
                    ),
                    padding="40px",
                    width="100%",
                    text_align="center",
                ),
                rx.table.root(
                    rx.table.header(
                        rx.table.row(
                            rx.table.column_header_cell("File"),
                            rx.table.column_header_cell("Uploaded"),
                            rx.table.column_header_cell("Chunks"),
                            rx.table.column_header_cell(""),
                        )
                    ),
                    rx.table.body(
                        rx.foreach(State.kb_documents, _document_row)
                    ),
                    variant="surface",
                    width="100%",
                ),
            ),
            width="100%",
            spacing="3",
            padding="20px",
            background_color="var(--gray-1)",
            border="1px solid var(--gray-4)",
            border_radius="10px",
        ),

        width="100%",
        max_width="900px",
        spacing="5",
        padding_top="20px",
    )
