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
        lms_db: Session,
        document_ids: list[str] | None = None,
    ):
        """
        Executes the full RAG pipeline and YIELDS chunks of text.
        At the very end, yields a dict containing citations and metrics.
        """
        tracker = ObservabilityTracker().start()

        print(f"\\n{'='*50}")
        print(f"💬 [CHAT START] Query: '{query}'")
        print(f"{'='*50}")

        try:
            # 1. Classify intent
            t0 = time.time()
            intent = await self.intent_classifier.classify(query)
            tracker.log_latency("intent_classification", t0, time.time())
            tracker.log("intent", intent)
            print(f"🎯 [1/8] Intent Classified: '{intent.upper()}'")

            if intent in ["conversational", "greeting"]:
                # Short-circuit RAG pipeline for simple chat
                rewritten_query = query
                candidates = []
                compressed = []
                reranked = []
                metrics = {
                    "intent_classification_ms": round((time.time() - t0) * 1000, 2),
                    "intent": intent,
                    "query_rewrite_ms": 0.0,
                    "rewritten_query": rewritten_query,
                    "multi_query_ms": 0.0,
                    "hybrid_retrieval_ms": 0.0,
                    "candidates_count": 0,
                    "reranking_ms": 0.0,
                    "compression_ms": 0.0,
                    "llm_generation_ms": 0.0,
                    "total_pipeline_ms": 0.0
                }
            else:
                # 2. Rewrite query based on history
                t1 = time.time()
                rewritten_query = await self.query_rewriter.rewrite(query, history)
                tracker.log_latency("query_rewrite", t1, time.time())
                tracker.log("rewritten_query", rewritten_query)
                print(f"✍️  [2/8] Rewritten Query: '{rewritten_query}'")

                # 3. Generate multi-query variants
                t2 = time.time()
                queries = await self.multi_query.generate(rewritten_query, n=4)
                tracker.log_latency("multi_query", t2, time.time())
                print(f"🔎 [3/8] Generated {len(queries)} multi-query variants.")

                # 4. Build filter & Retrieve candidates via Hybrid Search
                t3 = time.time()
                where = build_chroma_filter(user_id=user_id, document_ids=document_ids)
                candidates = await self.hybrid_retriever.retrieve(
                    queries=queries, where=where, document_ids=document_ids, k=20
                )
                tracker.log_latency("hybrid_retrieval", t3, time.time())
                tracker.log("candidates_count", len(candidates))
                print(f"📥 [4/8] Retrieved {len(candidates)} candidate chunks.")

                if not candidates:
                    # Do not early exit; user might be asking a DB/Tool question or greeting.
                    reranked = []
                else:
                    # 5. Rerank candidates
                    t4 = time.time()
                    reranked = await self.reranker.rerank(rewritten_query, candidates, top_n=5)
                    tracker.log_latency("reranking", t4, time.time())
                    print(f"⚖️  [5/8] Reranked candidates down to top {len(reranked)}.")

                # 6. Compress context
                t5 = time.time()
                compressed = []
                if reranked:
                    compressed = await self.compressor.compress(rewritten_query, reranked)
                tracker.log_latency("compression", t5, time.time())
                print(f"🗜️  [6/8] Compressed context.")

            # 7. LLM Generation
            t6 = time.time()
            context_text = "\n\n---\n\n".join(
                [c.get("text", "") for c in compressed]
            ) if compressed else "No relevant documents found."
            
            response_text = ""
            async for chunk in self._call_llm(rewritten_query, context_text, intent, history, lms_db, user_id):
                response_text += chunk
                yield chunk
                
            tracker.log_latency("llm_generation", t6, time.time())
            print(f"🧠 [7/8] Generated LLM Response.")

            # 8. Attach Citations
            answer = self.citation_builder.build(response_text, reranked)
            print(f"🔗 [8/8] Built {len(answer.get('citations', []))} citations.")
            
            metrics = tracker.finish()
            logger.info("rag_pipeline_complete", metrics=metrics)

            print(f"\n{'='*50}")
            print(f"✅ [CHAT SUCCESS] Total Time: {metrics.get('total_pipeline_ms', 0):.2f}ms")
            print(f"{'='*50}\n")
            
            # Yield the final metadata (citations + metrics) as a dict
            yield {
                "answer": answer["answer"],
                "citations": answer["citations"],
                "metrics": metrics
            }

        except Exception as exc:
            print(f"\n{'='*50}")
            print(f"❌ [CHAT FAILED] Error: {str(exc)}")
            print(f"{'='*50}\n")
            logger.error("rag_pipeline_failed", exc_info=True, error=str(exc))
            metrics = tracker.finish()
            
            # Yield error chunk and then metadata
            yield "An error occurred while processing your query."
            yield {
                "answer": "An error occurred while processing your query.",
                "citations": [],
                "metrics": metrics
            }

    async def _call_llm(self, query: str, context: str, intent: str, history: list[dict], lms_db: Session, user_id: str):
        from app.agent.tools import AGENT_TOOLS, dispatch_tool
        
        system_prompt = build_system_prompt(intent)
        messages = [{"role": "system", "content": system_prompt}]
        
        # Include a limited amount of recent history
        messages.extend(history[-6:])
        
        # Final user prompt combines context + question
        user_content = f"Context:\n{context}\n\nQuestion: {query}"
        messages.append({"role": "user", "content": user_content})

        is_conversational = intent in ["conversational", "greeting"]

        if is_conversational:
            response = await self.client.chat.completions.create(
                model="gpt-4o",
                messages=messages,
                max_tokens=1500,
                temperature=0.7,
            )
            if response.choices and response.choices[0].message.content:
                yield response.choices[0].message.content
            return

        stream = await self.client.chat.completions.create(
            model="gpt-4o",
            messages=messages,
            tools=AGENT_TOOLS,
            max_tokens=1500,
            temperature=0.3,
            stream=True,
        )
        
        tool_calls_buffer = {}
        
        async for chunk in stream:
            if not chunk.choices:
                continue
            delta = chunk.choices[0].delta
            
            if delta.content:
                yield delta.content
                
            if delta.tool_calls:
                for tc in delta.tool_calls:
                    if tc.index not in tool_calls_buffer:
                        tool_calls_buffer[tc.index] = {
                            "id": tc.id,
                            "type": "function",
                            "function": {"name": tc.function.name or "", "arguments": ""}
                        }
                    else:
                        if tc.function.name:
                            tool_calls_buffer[tc.index]["function"]["name"] += tc.function.name
                        if tc.function.arguments:
                            tool_calls_buffer[tc.index]["function"]["arguments"] += tc.function.arguments

        # If the LLM called tools, we execute them and stream a second response
        if tool_calls_buffer:
            class DotDict:
                pass

            tool_calls_list = []
            for k in sorted(tool_calls_buffer.keys()):
                tc = tool_calls_buffer[k]
                obj = DotDict()
                obj.id = tc["id"]
                obj.type = tc["type"]
                obj.function = DotDict()
                obj.function.name = tc["function"]["name"]
                obj.function.arguments = tc["function"]["arguments"]
                tool_calls_list.append(obj)

            messages.append({"role": "assistant", "content": None, "tool_calls": list(tool_calls_buffer.values())})
            
            for tc in tool_calls_list:
                function_response = dispatch_tool(tc, lms_db, user_id)
                messages.append(
                    {
                        "tool_call_id": tc.id,
                        "role": "tool",
                        "name": tc.function.name,
                        "content": function_response,
                    }
                )
            
            stream2 = await self.client.chat.completions.create(
                model="gpt-4o",
                messages=messages,
                max_tokens=1500,
                stream=True,
            )
            async for chunk in stream2:
                if chunk.choices and chunk.choices[0].delta.content:
                    yield chunk.choices[0].delta.content
