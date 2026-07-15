def build_chroma_filter(user_id: str, document_ids: list[str] | None = None) -> dict:
    """
    Builds the metadata 'where' clause for ChromaDB.
    Ensures the user can only search their own documents.
    """
    where = {"user_id": user_id}
    
    if document_ids:
        if len(document_ids) == 1:
            where["document_id"] = document_ids[0]
        else:
            where["document_id"] = {"$in": document_ids}
            
    return where
