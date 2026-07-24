def build_chroma_filter(user_id: str, document_ids: list[str] | None = None) -> dict:
    """
    Builds the metadata 'where' clause for ChromaDB.
    Documents are global, so we only filter by document_ids if provided.
    """
    where = {}
    
    if document_ids:
        if len(document_ids) == 1:
            where["document_id"] = document_ids[0]
        else:
            where["document_id"] = {"$in": document_ids}
            
    return where if where else None
