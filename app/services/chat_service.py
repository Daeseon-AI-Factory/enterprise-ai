import json
import time
import uuid
from typing import AsyncGenerator

from loguru import logger

from app.llm_client import chat_completion
from app.core.prompts import SYSTEM_CHAT
from app.core.conversation_store import ConversationStore
from app.core.vector_store import get_vector_store


SYSTEM_RAG_CHAT = """You are an enterprise AI assistant with access to a knowledge base.

## CRITICAL RULES
1. Below you will see "Retrieved Documents" section. If it exists and has content, you MUST use those documents to answer. Always mention the source filename.
2. ONLY say "참고 문서 없음" if the Retrieved Documents section explicitly says "(참고 가능한 문서 없음)".
3. If documents are provided, ALWAYS reference them in your answer, even if the question is vague. Summarize what's in the documents.
4. Use the same language as the user.

{rag_context}"""


RECENT_MSG_COUNT = 10  # Keep last N messages verbatim
SUMMARY_THRESHOLD = 16  # Summarize when history exceeds this


class ChatService:
    def __init__(self):
        self._store = ConversationStore()
        self._vector_store = get_vector_store()
        self._summaries: dict[str, str] = {}  # conv_id → summary

    def _compress_history(self, conv_id: str, history: list[dict]) -> list[dict]:
        """Compress long conversations: summary of old + recent messages verbatim."""
        if len(history) <= SUMMARY_THRESHOLD:
            return history

        old_messages = history[:-RECENT_MSG_COUNT]
        recent_messages = history[-RECENT_MSG_COUNT:]

        # Check if we already have a summary for this conversation
        existing_summary = self._summaries.get(conv_id, "")

        # Build summary from old messages
        old_text = "\n".join(
            f"{'User' if m['role'] == 'user' else 'AI'}: {m['content'][:200]}"
            for m in old_messages[-20:]  # Summarize last 20 old messages max
        )

        try:
            summary_response = chat_completion(
                messages=[
                    {"role": "system", "content": "Summarize the following conversation in 2-3 sentences. Preserve key facts, decisions, and context. Write in the same language as the conversation."},
                    {"role": "user", "content": f"Previous summary: {existing_summary}\n\nNew messages:\n{old_text}"},
                ],
                temperature=0.1,
            )
            summary = summary_response.choices[0].message.content or ""
            self._summaries[conv_id] = summary
            logger.info(f"Compressed {len(old_messages)} old messages into summary for [{conv_id[:8]}]")
        except Exception as e:
            logger.warning(f"Summary generation failed: {e}")
            summary = existing_summary or ""

        if summary:
            compressed = [{"role": "system", "content": f"[Previous conversation summary]\n{summary}"}]
            compressed.extend(recent_messages)
            return compressed
        return recent_messages

    def _search_all_collections(self, query: str, top_k: int = 5) -> tuple[list[dict], str]:
        """Search across all RAG collections and build context."""
        all_results = []
        try:
            collections = self._vector_store.list_collections()
        except Exception as e:
            logger.warning(f"Failed to list collections: {e}")
            return [], ""

        if not collections:
            return [], ""

        for col in collections:
            col_name = col.get("name", col) if isinstance(col, dict) else str(col)
            try:
                results = self._vector_store.hybrid_search(
                    collection=col_name,
                    query=query,
                    top_k=top_k,
                )
                for r in results:
                    r["collection"] = col_name
                all_results.extend(results)
            except Exception as e:
                logger.warning(f"Search failed in collection '{col_name}': {e}")

        if not all_results:
            return [], ""

        # Sort by rerank_score (higher = more relevant after reranking)
        all_results.sort(key=lambda x: x.get("rerank_score", x.get("score", 0)), reverse=True)
        top_results = all_results[:top_k]

        # Build context string
        context_parts = []
        sources = []
        for doc in top_results:
            source_info = f"[{doc.get('collection', '?')}/{doc.get('filename', '?')}]"
            context_parts.append(f"{source_info}\n{doc['content']}")
            sources.append({
                "collection": doc.get("collection", ""),
                "filename": doc.get("filename", ""),
                "score": doc.get("score", 0),
            })

        context_str = "\n\n---\n\n".join(context_parts)
        logger.info(
            f"RAG search: query='{query[:50]}' → {len(top_results)} docs from "
            f"{list(set(d.get('collection','') for d in top_results))}"
        )
        return sources, context_str

    async def chat(
        self,
        message: str,
        conversation_id: str | None = None,
    ) -> dict:
        t0 = time.time()
        conv_id = conversation_id or str(uuid.uuid4())
        history = self._store.load(conv_id)
        raw_count = len(history)

        # Compress long conversations: summary + recent messages
        history = self._compress_history(conv_id, history)
        logger.info(f"[CHAT] 질문: '{message[:60]}' (conv: {conv_id[:8]}, 히스토리: {raw_count}→{len(history)}개)")

        # Pure chat — no RAG search (RAG is handled by /ask or /analyze)
        system_prompt = SYSTEM_CHAT

        messages = [{"role": "system", "content": system_prompt}]
        messages.extend(history)
        messages.append({"role": "user", "content": message})
        total_chars = sum(len(m.get("content", "")) for m in messages)
        logger.info(f"[CHAT] LLM 호출: 메시지 {len(messages)}개, 약 {total_chars}자")

        try:
            t1 = time.time()
            response = chat_completion(messages=messages)
            reply = response.choices[0].message.content or ""
            logger.info(f"[CHAT] LLM 응답: {len(reply)}자 ({time.time()-t1:.1f}초)")
        except Exception as e:
            logger.error(f"[CHAT] LLM 호출 실패: {e}")
            return {"reply": f"LLM 호출 실패: {e}", "conversation_id": conv_id}

        # Persist
        self._store.append(conv_id, {"role": "user", "content": message})
        self._store.append(conv_id, {"role": "assistant", "content": reply})

        logger.info(f"[CHAT] 완료: 총 {time.time()-t0:.1f}초")
        return {"reply": reply, "conversation_id": conv_id}

    async def chat_stream(
        self,
        message: str,
        conversation_id: str | None = None,
    ) -> AsyncGenerator[str, None]:
        conv_id = conversation_id or str(uuid.uuid4())
        history = self._store.load(conv_id)

        # Compress long conversations: summary + recent messages
        history = self._compress_history(conv_id, history)
        logger.info(f"[CHAT-STREAM] 질문: '{message[:60]}' (conv: {conv_id[:8]})")

        # Pure chat — no RAG search
        system_prompt = SYSTEM_CHAT

        messages = [{"role": "system", "content": system_prompt}]
        messages.extend(history)
        messages.append({"role": "user", "content": message})

        try:
            stream = chat_completion(messages=messages, stream=True)
        except Exception as e:
            logger.error(f"[CHAT-STREAM] LLM 호출 실패: {e}")
            yield f"data: {json.dumps({'error': str(e), 'conversation_id': conv_id})}\n\n"
            return

        full_reply = ""
        for chunk in stream:
            delta = chunk.choices[0].delta.content or ""
            full_reply += delta
            yield f"data: {json.dumps({'content': delta, 'conversation_id': conv_id})}\n\n"

        # Persist
        self._store.append(conv_id, {"role": "user", "content": message})
        self._store.append(conv_id, {"role": "assistant", "content": full_reply})

        yield f"data: {json.dumps({'done': True, 'conversation_id': conv_id})}\n\n"

    async def chat_with_context(
        self,
        message: str,
        conversation_id: str | None = None,
        context: dict | None = None,
    ) -> dict:
        """Chat with additional page/code context from the widget."""
        context = context or {}
        context_str = ""
        if context.get("page_url"):
            context_str += f"\nCurrent page: {context['page_url']}"
        if context.get("component"):
            context_str += f"\nComponent: {context['component']}"

        enhanced_message = message
        if context_str:
            enhanced_message = f"[Context]{context_str}\n\n[Question] {message}"

        return await self.chat(
            message=enhanced_message,
            conversation_id=conversation_id,
        )

    async def list_conversations(self) -> list[dict]:
        return self._store.list_conversations()

    async def get_conversation(self, conversation_id: str) -> list[dict]:
        return self._store.load(conversation_id)

    async def delete_conversation(self, conversation_id: str) -> None:
        self._store.delete(conversation_id)
