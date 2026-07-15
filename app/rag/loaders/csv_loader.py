import structlog
import pandas as pd

from app.rag.loaders.base import BaseLoader, LoadedPage

logger = structlog.get_logger(__name__)


class CsvLoader(BaseLoader):
    def load(self, file_path: str) -> list[LoadedPage]:
        df = pd.read_csv(file_path)
        pages: list[LoadedPage] = []
        for i, row in df.iterrows():
            text = " | ".join(f"{col}: {val}" for col, val in row.items())
            pages.append(
                LoadedPage(
                    text=text,
                    page_number=int(i) + 1,
                    metadata={"source": file_path, "row": int(i)},
                )
            )
        logger.info("csv_loaded", file=file_path, row_count=len(pages))
        return pages
