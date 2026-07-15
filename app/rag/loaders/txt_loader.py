import structlog

from app.rag.loaders.base import BaseLoader, LoadedPage

logger = structlog.get_logger(__name__)


class TxtLoader(BaseLoader):
    def load(self, file_path: str) -> list[LoadedPage]:
        with open(file_path, encoding="utf-8", errors="replace") as f:
            text = f.read()
        logger.info("txt_loaded", file=file_path, char_count=len(text))
        return [
            LoadedPage(
                text=text,
                page_number=1,
                metadata={"source": file_path},
            )
        ]
