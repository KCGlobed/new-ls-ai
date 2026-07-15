from app.rag.loaders.base import BaseLoader
from app.rag.loaders.pdf_loader import PdfLoader
from app.rag.loaders.docx_loader import DocxLoader
from app.rag.loaders.txt_loader import TxtLoader
from app.rag.loaders.csv_loader import CsvLoader
from app.rag.loaders.xlsx_loader import XlsxLoader

MIME_TO_LOADER: dict[str, type[BaseLoader]] = {
    "application/pdf": PdfLoader,
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document": DocxLoader,
    "application/msword": DocxLoader,
    "text/plain": TxtLoader,
    "text/csv": CsvLoader,
    "application/csv": CsvLoader,
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet": XlsxLoader,
    "application/vnd.ms-excel": XlsxLoader,
}


def get_loader(mime_type: str) -> BaseLoader:
    """Return the appropriate loader instance for the given MIME type."""
    loader_class = MIME_TO_LOADER.get(mime_type)
    if not loader_class:
        raise ValueError(
            f"Unsupported file type: '{mime_type}'. "
            f"Supported types: {list(MIME_TO_LOADER.keys())}"
        )
    return loader_class()
