import json
import uuid
from typing import AsyncGenerator

from loguru import logger

from app.llm_client import chat_completion
from app.core.prompts import SYSTEM_CHAT
from app.core.conversation_store import ConversationStore
from app.core.vector_store import VectorStore


SYSTEM_RAG_CHAT = """You are an enterprise AI assistant with access to a knowledge base.

## CRITICAL RULES
1. Below you will see "Retrieved Documents" section. If it exists and has content, you MUST use those documents to answer. Always mention the source filename.
2. ONLY say "참고 문서 없음" if the Retrieved Documents section explicitly says "(참고 가능한 문서 없음)".
3. If documents are provided, ALWAYS reference them in your answer, even if the question is vague. Summarize what's in the documents.
4. Use the same language as the user.

{rag_context}"""


class ChatService:
    def __init__(self):
        self._store = ConversationStore()
        self._vector_store = VectorStore()

    def _search_all_collections(self, query: str, top_k: int = 5) -> tuple[list[dict], str]:
        """Search across all RAG collections and build context."""
        all_results = []
        try:
            collections = self._vector_store.list_collections()
        except Exception as e:
            logger.warning(f"Failed to list collections: {e}")
            return [], ""

        for col in collections:
            col_name = col.get("name", col) if isinstance(col, dict) else str(col)
            try:
                results = self._vector_store.search(
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

        # Sort by score (lower = more relevant for distance-based)
        all_results.sort(key=lambda x: x.get("score", 999))
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
        conv_id = conversation_id or str(uuid.uuid4())
        history = self._store.load(conv_id)

        # Always search RAG first
        sources, rag_context = self._search_all_collections(message)

        if rag_context:
            rag_block = f"\n## Retrieved Documents\n{rag_context}"
            system_prompt = SYSTEM_RAG_CHAT.format(rag_context=rag_block)
        else:
            system_prompt = SYSTEM_RAG_CHAT.format(rag_context="\n(참고 가능한 문서 없음)")

        messages = [{"role": "system", "content": system_prompt}]
        messages.extend(history)
        messages.append({"role": "user", "content": message})

        try:
            response = chat_completion(messages=messages)
            reply = response.choices[0].message.content or ""
        except Exception as e:
            logger.error(f"LLM call failed: {e}")
            return {"reply": f"LLM 호출 실패: {e}", "conversation_id": conv_id}

        # Persist
        self._store.append(conv_id, {"role": "user", "content": message})
        self._store.append(conv_id, {"role": "assistant", "content": reply})

        logger.info(f"Chat [{conv_id[:8]}]: {message[:50]}... (RAG sources: {len(sources)})")
        result = {"reply": reply, "conversation_id": conv_id}
        if sources:
            result["sources"] = sources
        return result

    async def chat_stream(
        self,
        message: str,
        conversation_id: str | None = None,
    ) -> AsyncGenerator[str, None]:
        conv_id = conversation_id or str(uuid.uuid4())
        history = self._store.load(conv_id)

        # Always search RAG first
        sources, rag_context = self._search_all_collections(message)

        if rag_context:
            rag_block = f"\n## Retrieved Documents\n{rag_context}"
            system_prompt = SYSTEM_RAG_CHAT.format(rag_context=rag_block)
        else:
            system_prompt = SYSTEM_RAG_CHAT.format(rag_context="\n(참고 가능한 문서 없음)")

        messages = [{"role": "system", "content": system_prompt}]
        messages.extend(history)
        messages.append({"role": "user", "content": message})

        # Send sources info first
        if sources:
            yield f"data: {json.dumps({'sources': sources, 'conversation_id': conv_id}, ensure_ascii=False)}\n\n"

        try:
            stream = chat_completion(messages=messages, stream=True)
        except Exception as e:
            logger.error(f"LLM stream failed: {e}")
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
