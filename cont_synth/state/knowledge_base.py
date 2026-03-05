"""Knowledge Base state mixin.

Handles document listing, upload, and deletion for the Product Context page.
Field definitions live on the concrete State class; only behavior lives here.
"""
import reflex as rx
from sqlmodel import select, func

from ..models import WorkspaceDocument, DocumentChunk
from .core import WorkspaceDocumentItem


class KnowledgeBaseStateMixin(rx.State, mixin=True):

    def load_kb_documents(self):
        """Load all WorkspaceDocuments for the active product into state."""
        product_id = int(self.active_product_id)
        with rx.session() as session:
            docs = session.exec(
                select(WorkspaceDocument)
                .where(WorkspaceDocument.product_id == product_id)
                .order_by(WorkspaceDocument.upload_date.desc())
            ).all()

            items: list[WorkspaceDocumentItem] = []
            for doc in docs:
                chunk_count = session.exec(
                    select(func.count(DocumentChunk.id)).where(
                        DocumentChunk.document_id == doc.id
                    )
                ).one()
                items.append(
                    WorkspaceDocumentItem(
                        id=doc.id,
                        filename=doc.filename,
                        upload_date=doc.upload_date.strftime("%Y-%m-%d %H:%M"),
                        chunk_count=chunk_count,
                    )
                )
        self.kb_documents = items

    async def handle_kb_upload(self, files: list[rx.UploadFile]):
        """Ingest an uploaded file into the Knowledge Base."""
        if not files:
            return
        file = files[0]
        filename = file.filename or "unknown"
        lower = filename.lower()

        if not (lower.endswith('.pdf') or lower.endswith('.txt')):
            self.kb_upload_error = "Only PDF and TXT files are supported."
            return

        self.kb_is_uploading = True
        self.kb_upload_error = ""
        yield

        try:
            file_data = await file.read()
            from ..kb_ingest import ingest_document
            ingest_document(file_data, filename, int(self.active_product_id))
            self.load_kb_documents()
        except Exception as e:
            self.kb_upload_error = f"Upload failed: {str(e)}"
        finally:
            self.kb_is_uploading = False

    def delete_kb_document(self, doc_id: int):
        """Cascading delete: removes DocumentChunks then the WorkspaceDocument."""
        with rx.session() as session:
            chunks = session.exec(
                select(DocumentChunk).where(DocumentChunk.document_id == doc_id)
            ).all()
            for chunk in chunks:
                session.delete(chunk)
            session.commit()

            doc = session.get(WorkspaceDocument, doc_id)
            if doc:
                session.delete(doc)
            session.commit()

        self.load_kb_documents()

    def reprocess_all_kb_documents(self):
        """Sanitize and re-embed all stored chunks for the active product.

        Applies the spaced-letter sanitization to existing chunk_text records
        and regenerates embeddings from the cleaned text.
        """
        product_id = int(self.active_product_id)
        self.kb_is_reprocessing = True
        yield

        try:
            from ..kb_ingest import reprocess_document_chunks
            with rx.session() as session:
                docs = session.exec(
                    select(WorkspaceDocument)
                    .where(WorkspaceDocument.product_id == product_id)
                ).all()
                doc_ids = [d.id for d in docs]

            total = 0
            for doc_id in doc_ids:
                total += reprocess_document_chunks(doc_id)

            print(f"Re-processed {total} chunks across {len(doc_ids)} documents.")
            self.load_kb_documents()
        except Exception as e:
            self.kb_upload_error = f"Re-processing failed: {str(e)}"
        finally:
            self.kb_is_reprocessing = False
