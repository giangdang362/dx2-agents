"""
title: Unit Test Generator Agent
description: Generates comprehensive unit tests for source code pasted in chat or attached as files. Supports Python (pytest), TypeScript/JavaScript (vitest/jest), Go (testing), and Java (JUnit 5).
requirements: aiohttp
"""

import logging
import re
from typing import AsyncGenerator, Callable

from pydantic import BaseModel, Field

from open_webui.utils import llm_client

log = logging.getLogger(__name__)


SYSTEM_PROMPT_TEMPLATE = """\
You are a senior expert {language} developer, specializing in Test-Driven Development (TDD) and robust testing methodologies.

Your task is to write a comprehensive suite of unit tests for the {language} source code provided by the user, using the `{framework}` testing framework.

The user's source code may appear as fenced code blocks in their message, as attached file contents, or both. Treat all such code as the input under test. If multiple functions, methods, or classes are present, generate tests for each.

Testing Requirements:
* Full Coverage: Cover the happy path, all relevant edge cases (empty / null values, zeros, negative numbers, boundary conditions), and invalid input types.
* Error Handling: If the code is expected to raise/throw under certain conditions, write tests that verify those errors are produced correctly using the framework's idiomatic mechanism.
* Clear Structure: Strictly follow the Arrange-Act-Assert (AAA) pattern in every test case. For class methods, instantiate the class in the Arrange block.
* Isolation & Mocking: If the code has external dependencies (HTTP, database, filesystem, time, randomness, other classes/methods), mock them using the idiomatic mocking facility for {framework}. Tests must be deterministic and run in isolation.
* Idiomatic Style: Use {framework} naming conventions, fixtures/setup hooks, and assertion idioms. Group related tests appropriately (describe blocks, test classes, table-driven tests, etc.) when natural for the framework.
* Output Format: Return the test code inside a single fenced code block tagged with the correct language (e.g. ```{language_tag}). Do not include explanations, prose, or commentary outside the code block. The code itself may contain brief comments where they aid readability.

Focus on creating comprehensive, maintainable tests with clear assertions and good edge-case coverage.
"""

LANGUAGE_FRAMEWORK_MAP: dict[str, str] = {
    "python": "pytest",
    "typescript": "vitest",
    "javascript": "jest",
    "go": "testing",
    "java": "junit5",
}

LANGUAGE_TAG_MAP: dict[str, str] = {
    "python": "python",
    "typescript": "typescript",
    "javascript": "javascript",
    "go": "go",
    "java": "java",
}

FENCE_LANGUAGE_ALIASES: dict[str, str] = {
    "py": "python",
    "python": "python",
    "python3": "python",
    "ts": "typescript",
    "tsx": "typescript",
    "typescript": "typescript",
    "js": "javascript",
    "jsx": "javascript",
    "javascript": "javascript",
    "node": "javascript",
    "go": "go",
    "golang": "go",
    "java": "java",
}

EXTENSION_LANGUAGE_MAP: dict[str, str] = {
    ".py": "python",
    ".ts": "typescript",
    ".tsx": "typescript",
    ".js": "javascript",
    ".jsx": "javascript",
    ".mjs": "javascript",
    ".cjs": "javascript",
    ".go": "go",
    ".java": "java",
}

_FENCE_RE = re.compile(r"```([A-Za-z0-9_+-]*)")
_FILENAME_RE = re.compile(r"[\w./-]+(\.[A-Za-z0-9]+)")


class Pipe:
    class Valves(BaseModel):
        LLM_PROVIDER: str = Field(
            default="openai",
            description="LLM provider: 'ollama', 'gemini', or 'openai' (OpenAI-compatible, incl. Azure AI Foundry via OPENAI_API_BASE_URL/OPENAI_API_KEY env)",
        )
        OLLAMA_BASE_URL: str = Field(
            default="http://localhost:11434",
            description="Ollama base URL (used when LLM_PROVIDER=ollama)",
        )
        MODEL: str = Field(
            default="gpt-5.3-chat",
            description="Model name (e.g. gpt-5.3-chat, gemini-2.5-flash, phi4-mini)",
        )
        DEFAULT_LANGUAGE: str = Field(
            default="python",
            description="Fallback language when none can be detected from the user's message (python, typescript, javascript, go, java)",
        )
        FRAMEWORK_PYTHON: str = Field(default="pytest", description="Test framework for Python")
        FRAMEWORK_TYPESCRIPT: str = Field(default="vitest", description="Test framework for TypeScript")
        FRAMEWORK_JAVASCRIPT: str = Field(default="jest", description="Test framework for JavaScript")
        FRAMEWORK_GO: str = Field(default="testing", description="Test framework for Go")
        FRAMEWORK_JAVA: str = Field(default="junit5", description="Test framework for Java")

    def __init__(self):
        self.valves = self.Valves()

    def pipes(self) -> list[dict]:
        return [{"id": "unittest-agent", "name": "Unit Test Generator"}]

    # ── helpers ──────────────────────────────────────────────────────

    @staticmethod
    def _message_text(msg: dict) -> str:
        content = msg.get("content", "")
        if isinstance(content, str):
            return content
        if isinstance(content, list):
            parts = []
            for part in content:
                if isinstance(part, dict) and part.get("type") == "text":
                    parts.append(part.get("text", ""))
            return "\n".join(parts)
        return ""

    @staticmethod
    def _all_user_text(messages: list[dict]) -> str:
        return "\n".join(
            Pipe._message_text(m) for m in messages if m.get("role") == "user"
        )

    def _detect_language(self, messages: list[dict]) -> str:
        text = self._all_user_text(messages)

        for tag in _FENCE_RE.findall(text):
            normalized = tag.strip().lower()
            if normalized in FENCE_LANGUAGE_ALIASES:
                return FENCE_LANGUAGE_ALIASES[normalized]

        for match in _FILENAME_RE.finditer(text):
            ext = match.group(1).lower()
            if ext in EXTENSION_LANGUAGE_MAP:
                return EXTENSION_LANGUAGE_MAP[ext]

        return self.valves.DEFAULT_LANGUAGE.lower()

    def _framework_for(self, language: str) -> str:
        mapping = {
            "python": self.valves.FRAMEWORK_PYTHON,
            "typescript": self.valves.FRAMEWORK_TYPESCRIPT,
            "javascript": self.valves.FRAMEWORK_JAVASCRIPT,
            "go": self.valves.FRAMEWORK_GO,
            "java": self.valves.FRAMEWORK_JAVA,
        }
        return mapping.get(language, LANGUAGE_FRAMEWORK_MAP.get(language, "pytest"))

    def _build_system_prompt(self, language: str) -> str:
        framework = self._framework_for(language)
        language_tag = LANGUAGE_TAG_MAP.get(language, language)
        return SYSTEM_PROMPT_TEMPLATE.format(
            language=language,
            framework=framework,
            language_tag=language_tag,
        )

    # ── LLM helpers ──────────────────────────────────────────────────

    async def _chat(self, messages: list[dict]) -> str:
        try:
            if self.valves.LLM_PROVIDER == "gemini":
                return await llm_client.gemini_chat(messages, model=self.valves.MODEL)
            if self.valves.LLM_PROVIDER == "openai":
                return await llm_client.openai_chat(messages, model=self.valves.MODEL)
            return await llm_client.ollama_chat(
                messages,
                model=self.valves.MODEL,
                base_url=self.valves.OLLAMA_BASE_URL,
            )
        except Exception as e:
            log.error(f"[unittest-agent] LLM error: {e!r}")
            return "Sorry, an error occurred while generating tests."

    async def _stream(self, messages: list[dict]) -> AsyncGenerator[str, None]:
        try:
            if self.valves.LLM_PROVIDER == "gemini":
                async for token in llm_client.gemini_stream(messages, model=self.valves.MODEL):
                    yield token
                return
            if self.valves.LLM_PROVIDER == "openai":
                async for token in llm_client.openai_stream(messages, model=self.valves.MODEL):
                    yield token
                return
            async for token in llm_client.ollama_stream(
                messages,
                model=self.valves.MODEL,
                base_url=self.valves.OLLAMA_BASE_URL,
            ):
                yield token
        except Exception as e:
            log.error(f"[unittest-agent] LLM stream error: {e!r}")
            yield f"Sorry, an error occurred while contacting the LLM: {e}"

    # ── main entry point ────────────────────────────────────────────

    async def pipe(
        self,
        body: dict,
        __user__: dict = None,
        __event_emitter__: Callable = None,
        __task__: str = None,
        __metadata__: dict = None,
    ) -> AsyncGenerator[str, None] | str:
        if __task__:
            non_system = [
                m for m in body.get("messages", []) if m.get("role") != "system"
            ]
            return await self._chat(non_system)

        messages = body.get("messages", [])
        streaming = body.get("stream", False)

        language = self._detect_language(messages)
        system_prompt = self._build_system_prompt(language)

        augmented = [{"role": "system", "content": system_prompt}] + messages

        if not streaming:
            return await self._chat(augmented)

        return self._stream(augmented)
