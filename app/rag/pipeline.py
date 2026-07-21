import structlog
from openai import AsyncOpenAI
import time
from sqlalchemy.orm import Session

from app.core.config import settings
from app.rag.retrieval import (
    IntentClassifier,
    QueryRewriter,
    MultiQueryGenerator,
    HybridRetriever,
    build_chroma_filter
)
from app.rag.reranking.openai_reranker import OpenAIReranker
from app.rag.compression.context_compressor import ContextCompressor
from app.rag.citation.citation_builder import CitationBuilder
from app.observability.tracker import ObservabilityTracker
from app.rag.prompts.system_prompt import build_system_prompt

logger = structlog.get_logger(__name__)


class RAGPipeline:
    def __init__(self) -> None:
        self.intent_classifier = IntentClassifier()
        self.query_rewriter = QueryRewriter()
        self.multi_query = MultiQueryGenerator()
        self.hybrid_retriever = HybridRetriever()
        self.reranker = OpenAIReranker()
        self.compressor = ContextCompressor()
        self.citation_builder = CitationBuilder()
        self.client = AsyncOpenAI(api_key=settings.openai_api_key)

    async def run(
        self,
        query: str,
        user_id: str,
        history: list[dict],
        db: Session,
        document_ids: list[str] | None = None,
    ) -> tuple[dict, dict]:
        """
        Executes the full RAG pipeline and returns the structured answer + observability metrics.
        """
        tracker = ObservabilityTracker().start()

        try:
            # 1. Classify intent
            t0 = time.time()
            intent = await self.intent_classifier.classify(query)
            tracker.log_latency("intent_classification", t0, time.time())
            tracker.log("intent", intent)

            # 2. Rewrite query based on history
            t1 = time.time()
            rewritten_query = await self.query_rewriter.rewrite(query, history)
            tracker.log_latency("query_rewrite", t1, time.time())
            tracker.log("rewritten_query", rewritten_query)

            # 3. Generate multi-query variants
            t2 = time.time()
            queries = await self.multi_query.generate(rewritten_query, n=4)
            tracker.log_latency("multi_query", t2, time.time())

            # 4. Build filter & Retrieve candidates via Hybrid Search
            t3 = time.time()
            where = build_chroma_filter(user_id=user_id, document_ids=document_ids)
            candidates = await self.hybrid_retriever.retrieve(
                queries=queries, where=where, document_ids=document_ids, k=20
            )
            tracker.log_latency("hybrid_retrieval", t3, time.time())
            tracker.log("candidates_count", len(candidates))

            if not candidates:
                # Do not early exit; user might be asking a DB/Tool question or greeting.
                reranked = []
            else:
                # 5. Rerank candidates
                t4 = time.time()
                reranked = await self.reranker.rerank(rewritten_query, candidates, top_n=5)
                tracker.log_latency("reranking", t4, time.time())

            # 6. Compress context
            t5 = time.time()
            compressed = []
            if reranked:
                compressed = await self.compressor.compress(rewritten_query, reranked)
            tracker.log_latency("compression", t5, time.time())

            # 7. LLM Generation
            t6 = time.time()
            context_text = "\n\n---\n\n".join(
                [c.get("text", "") for c in compressed]
            ) if compressed else "No relevant documents found."
            
            response_text = await self._call_llm(rewritten_query, context_text, intent, history, db, user_id)
            tracker.log_latency("llm_generation", t6, time.time())

            # 8. Attach Citations
            answer = self.citation_builder.build(response_text, reranked)
            
            metrics = tracker.finish()
            logger.info("rag_pipeline_complete", metrics=metrics)
            return answer, metrics

        except Exception as exc:
            logger.error("rag_pipeline_failed", exc_info=True, error=str(exc))
            metrics = tracker.finish()
            return {"answer": "An error occurred while processing your query.", "citations": []}, metrics

    async def _call_llm(self, query: str, context: str, intent: str, history: list[dict], db: Session, user_id: str) -> str:
        from app.agent.tools import AGENT_TOOLS, dispatch_tool
        
        system_prompt = build_system_prompt(intent)
        messages = [{"role": "system", "content": system_prompt}]
        
        # Include a limited amount of recent history
        messages.extend(history[-6:])
        
        # Final user prompt combines context + question
        user_content = f"Context:\n{context}\n\nQuestion: {query}"
        messages.append({"role": "user", "content": user_content})

        response = await self.client.chat.completions.create(
            model="gpt-4o",  # Core generation uses the most capable model
            messages=messages,
            tools=AGENT_TOOLS,
            max_tokens=1500,
            temperature=0.3,
        )
        
        response_message = response.choices[0].message
        
        # Check if the model wants to call a tool
        if response_message.tool_calls:
            # Append the tool call message to the conversation
            messages.append(response_message)
            
            # Execute all tools requested by the model
            for tool_call in response_message.tool_calls:
                function_response = dispatch_tool(tool_call, db, user_id)
                messages.append(
                    {
                        "tool_call_id": tool_call.id,
                        "role": "tool",
                        "name": tool_call.function.name,
                        "content": function_response,
                    }
                )
            
            # Call the LLM again with the tool results
            second_response = await self.client.chat.completions.create(
                model="gpt-4o",
                messages=messages,
                max_tokens=1500,
            )
            return second_response.choices[0].message.content
            
        return response_message.content
