import structlog
import pandas as pd

from app.rag.loaders.base import BaseLoader, LoadedPage

logger = structlog.get_logger(__name__)


class XlsxLoader(BaseLoader):
    def load(self, file_path: str) -> list[LoadedPage]:
        excel = pd.ExcelFile(file_path)
        pages: list[LoadedPage] = []
        for sheet_name in excel.sheet_names:
            df = excel.parse(sheet_name)
            for i, row in df.iterrows():
                text = " | ".join(f"{col}: {val}" for col, val in row.items())
                pages.append(
                    LoadedPage(
                        text=text,
                        page_number=int(i) + 1,
                        metadata={
                            "source": file_path,
                            "sheet": sheet_name,
                            "row": int(i),
                        },
                    )
                )
        logger.info("xlsx_loaded", file=file_path, page_count=len(pages))
        return pages
