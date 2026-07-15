import structlog
from pypdf import PdfReader

from app.rag.loaders.base import BaseLoader, LoadedPage

logger = structlog.get_logger(__name__)


class PdfLoader(BaseLoader):
    def load(self, file_path: str) -> list[LoadedPage]:
        reader = PdfReader(file_path)
        pages: list[LoadedPage] = []
        for i, page in enumerate(reader.pages):
            text = page.extract_text() or ""
            if text.strip():
                pages.append(
                    LoadedPage(
                        text=text,
                        page_number=i + 1,
                        metadata={"source": file_path, "page": i + 1},
                    )
                )
        logger.info("pdf_loaded", file=file_path, page_count=len(pages))
        return pages
