INTENT_PROMPT = """
Analyze the user's question and classify it into exactly one of the following intents:
- factual_lookup: Asking for a specific fact, definition, or date.
- conceptual_explain: Asking how something works or for an explanation of a concept.
- comparison: Asking to compare two or more things.
- summarization: Asking for a summary of a topic or document.
- unknown: None of the above apply clearly.

Return ONLY the intent name in lowercase, with no other text.
"""

REWRITE_PROMPT = """
You are a query rewriter for an educational document retrieval system.
Given the conversation history and a user question, rewrite the question
to be fully self-contained, specific, and optimized for searching documents.
Do NOT answer the question.
Resolve any pronouns (it, he, they, this) based on the history.
Return ONLY the rewritten question.
"""

MULTI_QUERY_PROMPT = """
Generate {n} semantically different search queries for the following user question.
Each query should use different keywords or phrasing to retrieve different but relevant documents.
Return ONLY the queries, one per line, with no numbering, bullets, or extra text.
"""

RERANK_PROMPT = """
You are an expert relevance judge. Score how relevant this passage is to the user's query.
Score it from 0.0 to 10.0, where 10.0 means perfectly relevant and answers the query, 
and 0.0 means completely irrelevant.

Return ONLY the numerical score (e.g., 7.5). No explanation.

Query: {query}
Passage: {passage}
"""

COMPRESS_PROMPT = """
Extract ONLY the sentences from the passage that are directly relevant to the user's query.
Remove any irrelevant sentences, filler, or unrelated topics. 
Return the extracted sentences as a single cohesive block of text.
If absolutely nothing in the passage is relevant, return an empty string.

Query: {query}
Passage: {passage}
"""
