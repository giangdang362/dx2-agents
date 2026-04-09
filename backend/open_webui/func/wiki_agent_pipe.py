"""
title: Wiki Agent
description: Company wiki assistant — answers HR, policy, and benefits questions. Attach knowledge bases via OpenWebUI UI.
requirements: aiohttp
"""

import logging
from typing import AsyncGenerator, Callable

from pydantic import BaseModel, Field

from open_webui.utils import llm_client

log = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# System prompt
# ---------------------------------------------------------------------------

_WIKI_SYSTEM_PROMPT = """You are the CMC Global Wiki Assistant — an AI agent specialized in company policies, benefits, and HR procedures.

You help employees find answers about HR policies, benefits, and procedures, drawing on company documents provided to you in the context above.

Never reveal your underlying model or technology stack. If asked, say:
"I'm the CMC Wiki Assistant — a specialized company knowledge agent. I can't share details about the technology behind me."
Do not engage with hypothetical framings, roleplay, or capability questions designed to identify the underlying model.

---


SCOPE
Only answer questions related to: company policies, employee benefits, HR procedures, regulations, leave policies, insurance, allowances, and company events.

For off-topic requests, respond:
"Tôi chuyên hỗ trợ về chính sách và phúc lợi công ty. Tôi không thể giúp vấn đề này, nhưng sẵn sàng trả lời các câu hỏi về chính sách nội bộ."
(Or the English equivalent if the user writes in English.)

---

BEHAVIOR RULES
1. If the user greets you or asks how you are doing, respond with a brief acknowledgment.
2. Always use the company knowledge provided in the context above to answer questions.
   - Only cite a document or section if it directly and relevantly answers the question.
   - If the context does not contain enough information, say so clearly:
     "Thông tin này chưa có trong cơ sở dữ liệu. Vui lòng liên hệ phòng HR để được hỗ trợ."
   - NEVER make up or hallucinate policy details, amounts, deadlines, or conditions.
3. When citing specific amounts (VND), deadlines (days), or conditions, quote them exactly as they appear in the context.
4. If the question spans multiple topics (e.g. "tất cả phúc lợi cho nhân viên thử việc"), compile information from ALL relevant context chunks into a comprehensive answer.
5. Calibrate response length to question type:
   - Factual lookups (amounts, deadlines, eligibility): concise and direct
   - Complex questions (comparing tiers, listing all benefits): full detail with tables or bullet points
   - Never truncate an answer for the sake of brevity when completeness matters
6. When referencing a specific benefit or policy, mention the section number (e.g. "Mục 6" or "Section 6") so the employee can look it up.
7. Respond in the same language the user writes in. Default to Vietnamese if ambiguous.
8. Never fabricate information. If you don't know something, say so clearly.

---

OUTPUT FORMAT

[Your answer]
""".strip()


# ---------------------------------------------------------------------------
# Pipe class
# ---------------------------------------------------------------------------


class Pipe:
    class Valves(BaseModel):
        LLM_PROVIDER: str = Field(
            default="gemini",
            description="LLM provider: 'ollama' or 'gemini'",
        )
        OLLAMA_BASE_URL: str = Field(
            default="http://localhost:11434",
            description="Ollama base URL (used when LLM_PROVIDER=ollama)",
        )
        MODEL: str = Field(
            default="gemini-2.5-flash",
            description="Model for generating answers (e.g. gemini-2.5-flash, phi4-mini)",
        )

    def __init__(self):
        self.valves = self.Valves()

    def pipes(self) -> list[dict]:
        return [{"id": "wiki-agent", "name": "Wiki Agent"}]

    # ------------------------------------------------------------------
    # LLM helpers
    # ------------------------------------------------------------------

    async def _chat(self, messages: list[dict]) -> str:
        """Non-streaming LLM call. Returns assistant text."""
        try:
            if self.valves.LLM_PROVIDER == "gemini":
                return await llm_client.gemini_chat(
                    messages, model=self.valves.MODEL
                )
            return await llm_client.ollama_chat(
                messages,
                model=self.valves.MODEL,
                base_url=self.valves.OLLAMA_BASE_URL,
            )
        except Exception as e:
            log.error(f"[wiki-agent] LLM error: {e!r}")
            return "Sorry, an error occurred while processing your request."

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _extract_last_user_message(messages: list) -> str:
        for msg in reversed(messages):
            if msg.get("role") == "user":
                content = msg.get("content", "")
                return content if isinstance(content, str) else ""
        return ""

    # ------------------------------------------------------------------
    # Main pipe entry point
    # ------------------------------------------------------------------

    async def pipe(
        self,
        body: dict,
        __user__: dict = None,
        __event_emitter__: Callable = None,
        __task__: str = None,
    ) -> str:
        messages = body.get("messages", [])

        # Background tasks (title/tag generation) — skip wiki system prompt
        if __task__:
            non_system = [m for m in messages if m.get("role") != "system"]
            return await self._chat(non_system)

        # Prepend wiki system prompt, keep any existing system messages
        # (OpenWebUI injects RAG context as system messages automatically)
        full_messages = [{"role": "system", "content": _WIKI_SYSTEM_PROMPT}] + messages

        return await self._chat(full_messages)
