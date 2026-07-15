import re

class CitationBuilder:
    def build(self, response_text: str, used_chunks: list[dict]) -> dict:
        """
        Attaches source citations to the final answer.
        Returns a dict containing the text and a structured list of sources.
        """
        # Deduplicate sources based on document and page number
        sources_seen = set()
        citations = []
        
        for i, chunk in enumerate(used_chunks):
            meta = chunk.get("metadata", {})
            file_name = meta.get("file_name", "Unknown File")
            page = meta.get("page_number", meta.get("row", "N/A"))
            
            source_key = f"{file_name}_p{page}"
            
            if source_key not in sources_seen:
                sources_seen.add(source_key)
                citations.append({
                    "id": i + 1,
                    "file_name": file_name,
                    "document_id": meta.get("document_id"),
                    "page_or_row": page,
                    "snippet": chunk.get("text", "")[:150] + "..."  # Preview of the cited text
                })
        
        return {
            "answer": response_text,
            "citations": citations
        }
