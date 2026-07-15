"""
Parent-Child Chunker

Strategy:
- Parent chunks: ~2000 tokens  → stored in DB, sent to LLM for context
- Child chunks:  ~400 tokens   → indexed in ChromaDB for precise retrieval

When a child chunk matches a query, we retrieve its parent for richer context.
"""
import re
from dataclasses import dataclass, field

import structlog

from app.rag.loaders.base import LoadedPage

logger = structlog.get_logger(__name__)

PARENT_CHUNK_SIZE = 2000    # approximate characters (≈ 500 tokens)
CHILD_CHUNK_SIZE = 400      # approximate characters (≈ 100 tokens)
CHILD_CHUNK_OVERLAP = 50    # characters of overlap between child chunks


@dataclass
class ChildChunk:
    text: str
    chunk_index: int
    page_number: int
    token_count: int
    metadata: dict = field(default_factory=dict)


@dataclass
class ParentChunk:
    text: str
    parent_index: int
    page_number: int
    token_count: int
    children: list[ChildChunk] = field(default_factory=list)
    metadata: dict = field(default_factory=dict)


def _approx_token_count(text: str) -> int:
    """Rough approximation: 1 token ≈ 4 characters."""
    return max(1, len(text) // 4)


def _split_text(text: str, chunk_size: int, overlap: int) -> list[str]:
    """
    Split text into overlapping chunks on sentence boundaries where possible.
    Falls back to character-level splitting if no sentence boundary found.
    """
    chunks: list[str] = []
    start = 0
    while start < len(text):
        end = min(start + chunk_size, len(text))
        # Try to end on a sentence boundary (period / newline)
        if end < len(text):
            boundary = max(
                text.rfind(". ", start, end),
                text.rfind("\n", start, end),
            )
            if boundary > start + chunk_size // 2:
                end = boundary + 1
        chunk = text[start:end].strip()
        if chunk:
            chunks.append(chunk)
        start = end - overlap if end < len(text) else len(text)
    return chunks


class ParentChildChunker:
    def __init__(
        self,
        parent_chunk_size: int = PARENT_CHUNK_SIZE,
        child_chunk_size: int = CHILD_CHUNK_SIZE,
        child_overlap: int = CHILD_CHUNK_OVERLAP,
    ):
        self.parent_chunk_size = parent_chunk_size
        self.child_chunk_size = child_chunk_size
        self.child_overlap = child_overlap

    def chunk(self, pages: list[LoadedPage]) -> list[ParentChunk]:
        """
        Takes a list of LoadedPage objects and returns a list of ParentChunk
        objects, each containing their child chunks.
        """
        parent_chunks: list[ParentChunk] = []
        parent_index = 0
        child_index = 0

        for page in pages:
            if not page.text.strip():
                continue

            # Split page into parent-sized segments
            parent_texts = _split_text(
                page.text, self.parent_chunk_size, overlap=100
            )

            for parent_text in parent_texts:
                # Split parent into child-sized segments
                child_texts = _split_text(
                    parent_text, self.child_chunk_size, self.child_overlap
                )
                children = [
                    ChildChunk(
                        text=ct,
                        chunk_index=child_index + i,
                        page_number=page.page_number,
                        token_count=_approx_token_count(ct),
                        metadata={**page.metadata},
                    )
                    for i, ct in enumerate(child_texts)
                ]
                child_index += len(children)

                parent_chunks.append(
                    ParentChunk(
                        text=parent_text,
                        parent_index=parent_index,
                        page_number=page.page_number,
                        token_count=_approx_token_count(parent_text),
                        children=children,
                        metadata={**page.metadata},
                    )
                )
                parent_index += 1

        total_children = sum(len(p.children) for p in parent_chunks)
        logger.info(
            "chunking_complete",
            parent_count=len(parent_chunks),
            child_count=total_children,
        )
        return parent_chunks
