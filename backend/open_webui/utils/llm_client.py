"""
Shared async LLM client for Open WebUI pipe functions.

Provides non-streaming and streaming helpers for both Ollama and Gemini.
All functions return extracted text strings (not raw API dicts).

Gemini reads GEMINI_API_KEY from the environment.
Ollama URL is passed per-call so each pipe keeps its own base_url valve.
"""

import json as _json
import os
import ssl
from typing import AsyncGenerator, Awaitable, Callable

import aiohttp
import certifi

_GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")
_GEMINI_BASE_URL = "https://generativelanguage.googleapis.com/v1beta"
_ssl_ctx = ssl.create_default_context(cafile=certifi.where())


# ---------------------------------------------------------------------------
# Gemini message format converters
# ---------------------------------------------------------------------------

def _openai_messages_to_gemini(messages: list) -> tuple[list, str | None]:
    """Convert OpenAI messages array to Gemini contents + system_instruction."""
    system_parts: list[str] = []
    contents: list[dict] = []

    for msg in messages:
        role = msg.get("role", "user")
        content = msg.get("content", "")

        if isinstance(content, str):
            parts = [{"text": content}] if content else []
        elif isinstance(content, list):
            parts = [
                {"text": item.get("text", "")}
                for item in content
                if isinstance(item, dict) and item.get("type") == "text"
            ]
        else:
            parts = []

        if role == "system":
            system_parts.append(
                content if isinstance(content, str)
                else " ".join(p.get("text", "") for p in parts)
            )
        elif role == "assistant":
            contents.append({"role": "model", "parts": parts})
        else:
            contents.append({"role": "user", "parts": parts})

    system_instruction = " ".join(system_parts) if system_parts else None
    return contents, system_instruction


def _gemini_text_from_response(data: dict) -> str:
    candidates = data.get("candidates", [])
    if not candidates:
        return ""
    parts = candidates[0].get("content", {}).get("parts", [])
    return "".join(p.get("text", "") for p in parts)


def _gemini_parts_from_response(data: dict) -> list[dict]:
    """Extract raw parts list from a Gemini generateContent response."""
    candidates = data.get("candidates", [])
    if not candidates:
        return []
    return candidates[0].get("content", {}).get("parts", [])


def _gemini_text_from_chunk(chunk: dict) -> str:
    candidates = chunk.get("candidates", [])
    if not candidates:
        return ""
    parts = candidates[0].get("content", {}).get("parts", [])
    return "".join(p.get("text", "") for p in parts)


# ---------------------------------------------------------------------------
# Ollama
# ---------------------------------------------------------------------------

async def ollama_chat(
    messages: list[dict],
    model: str,
    base_url: str = "http://localhost:11434",
) -> str:
    """Non-streaming Ollama call via /api/chat. Returns assistant text."""
    url = f"{base_url}/api/chat"
    payload = {"model": model, "messages": messages, "stream": False}
    async with aiohttp.ClientSession() as session:
        async with session.post(
            url, json=payload, timeout=aiohttp.ClientTimeout(total=300)
        ) as resp:
            if resp.status != 200:
                err = await resp.text()
                raise RuntimeError(f"Ollama error {resp.status}: {err}")
            data = await resp.json()
    return data.get("message", {}).get("content", "")


async def ollama_stream(
    messages: list[dict],
    model: str,
    base_url: str = "http://localhost:11434",
) -> AsyncGenerator[str, None]:
    """Streaming Ollama call via /api/chat. Yields text tokens."""
    url = f"{base_url}/api/chat"
    payload = {"model": model, "messages": messages, "stream": True}
    session = aiohttp.ClientSession()
    try:
        resp = await session.post(url, json=payload, timeout=aiohttp.ClientTimeout(total=300))
        if resp.status != 200:
            yield f"Error contacting Ollama (status {resp.status})"
            return
        async for raw_line in resp.content:
            line = raw_line.decode("utf-8").strip()
            if not line:
                continue
            try:
                chunk = _json.loads(line)
                token = chunk.get("message", {}).get("content", "")
                if token:
                    yield token
                if chunk.get("done", False):
                    break
            except _json.JSONDecodeError:
                continue
    finally:
        await session.close()


async def ollama_chat_openai(
    messages: list[dict],
    model: str,
    base_url: str = "http://localhost:11434",
) -> str:
    """Non-streaming Ollama call via /v1/chat/completions. Returns assistant text."""
    url = f"{base_url}/v1/chat/completions"
    payload = {"model": model, "messages": messages, "stream": False}
    async with aiohttp.ClientSession() as session:
        async with session.post(
            url, json=payload, timeout=aiohttp.ClientTimeout(total=120)
        ) as resp:
            if resp.status != 200:
                err = await resp.text()
                raise RuntimeError(f"Ollama error {resp.status}: {err}")
            data = await resp.json()
    return data.get("choices", [{}])[0].get("message", {}).get("content", "")


async def ollama_stream_sse(
    messages: list[dict],
    model: str,
    base_url: str = "http://localhost:11434",
) -> AsyncGenerator[str, None]:
    """Streaming Ollama call via /v1/chat/completions. Yields raw SSE lines."""
    url = f"{base_url}/v1/chat/completions"
    payload = {"model": model, "messages": messages, "stream": True}
    session = aiohttp.ClientSession()
    try:
        resp = await session.post(url, json=payload, timeout=aiohttp.ClientTimeout(total=300))
        if resp.status != 200:
            err = await resp.text()
            yield f"data: {_json.dumps({'error': err[:200]})}"
            return
        async for raw_line in resp.content:
            line = raw_line.decode("utf-8").strip()
            if line:
                yield line
    finally:
        await session.close()


# ---------------------------------------------------------------------------
# Gemini
# ---------------------------------------------------------------------------

async def gemini_chat(
    messages: list[dict],
    model: str = "gemini-2.0-flash",
) -> str:
    """Non-streaming Gemini call. Returns assistant text. Reads GEMINI_API_KEY from env."""
    contents, system_instruction = _openai_messages_to_gemini(messages)
    payload: dict = {"contents": contents}
    if system_instruction:
        payload["systemInstruction"] = {"parts": [{"text": system_instruction}]}

    url = f"{_GEMINI_BASE_URL}/models/{model}:generateContent?key={_GEMINI_API_KEY}"
    connector = aiohttp.TCPConnector(ssl=_ssl_ctx)
    async with aiohttp.ClientSession(connector=connector) as session:
        async with session.post(
            url, json=payload, timeout=aiohttp.ClientTimeout(total=60)
        ) as resp:
            if resp.status != 200:
                err = await resp.text()
                raise RuntimeError(f"Gemini API error {resp.status}: {err}")
            data = await resp.json()
    return _gemini_text_from_response(data)


async def gemini_chat_with_tools(
    contents: list[dict],
    system_instruction: str | None = None,
    tools: list[dict] | None = None,
    tool_executor: Callable[[str, dict], Awaitable[dict]] | None = None,
    model: str = "gemini-2.5-flash",
    max_tool_rounds: int = 10,
) -> str:
    """Gemini call with native function calling loop.

    Sends generateContent with tool declarations. When the model returns
    functionCall parts, executes them via *tool_executor*, appends
    functionResponse parts, and calls again. Repeats until the model
    returns text-only or *max_tool_rounds* is exhausted.

    Args:
        contents: Gemini-native contents list (role/parts dicts).
        system_instruction: Optional system instruction text.
        tools: Gemini tool declarations, e.g.
               [{"functionDeclarations": [...]}].
        tool_executor: ``async (name, args) -> dict`` callback.
        model: Gemini model name.
        max_tool_rounds: Safety limit on tool-call iterations.

    Returns:
        The final assistant text after all tool calls are resolved.
    """
    url = f"{_GEMINI_BASE_URL}/models/{model}:generateContent?key={_GEMINI_API_KEY}"

    for _round in range(max_tool_rounds):
        payload: dict = {"contents": contents}
        if system_instruction:
            payload["systemInstruction"] = {"parts": [{"text": system_instruction}]}
        if tools:
            payload["tools"] = tools

        connector = aiohttp.TCPConnector(ssl=_ssl_ctx)
        async with aiohttp.ClientSession(connector=connector) as session:
            async with session.post(
                url, json=payload, timeout=aiohttp.ClientTimeout(total=120)
            ) as resp:
                if resp.status != 200:
                    err = await resp.text()
                    raise RuntimeError(f"Gemini API error {resp.status}: {err}")
                data = await resp.json()

        parts = _gemini_parts_from_response(data)
        if not parts:
            return ""

        # Check for function calls in the response
        function_calls = [p for p in parts if "functionCall" in p]
        if not function_calls:
            # No tool calls — return concatenated text
            return "".join(p.get("text", "") for p in parts)

        # Append the model's turn (with functionCall parts) to contents
        contents.append({"role": "model", "parts": parts})

        # Execute each function call and build functionResponse parts
        response_parts: list[dict] = []
        for fc_part in function_calls:
            fc = fc_part["functionCall"]
            name = fc["name"]
            args = fc.get("args", {})
            print(f"[gemini-tools] Calling tool: {name}({args})", flush=True)
            if tool_executor:
                result = await tool_executor(name, args)
            else:
                result = {"error": "No tool executor configured"}
            response_parts.append({
                "functionResponse": {"name": name, "response": result}
            })

        # Append user turn with function responses
        contents.append({"role": "user", "parts": response_parts})

    raise RuntimeError(f"gemini_chat_with_tools: exceeded {max_tool_rounds} tool rounds")


async def gemini_stream(
    messages: list[dict],
    model: str = "gemini-2.0-flash",
) -> AsyncGenerator[str, None]:
    """Streaming Gemini call. Yields text tokens. Reads GEMINI_API_KEY from env."""
    contents, system_instruction = _openai_messages_to_gemini(messages)
    payload: dict = {"contents": contents}
    if system_instruction:
        payload["systemInstruction"] = {"parts": [{"text": system_instruction}]}

    url = f"{_GEMINI_BASE_URL}/models/{model}:streamGenerateContent?key={_GEMINI_API_KEY}&alt=sse"
    connector = aiohttp.TCPConnector(ssl=_ssl_ctx)
    async with aiohttp.ClientSession(connector=connector) as session:
        async with session.post(
            url, json=payload, timeout=aiohttp.ClientTimeout(total=60)
        ) as resp:
            if resp.status != 200:
                err = await resp.text()
                yield f"Error contacting Gemini (status {resp.status}): {err}"
                return
            async for raw_line in resp.content:
                line = raw_line.decode("utf-8").strip()
                if not line or not line.startswith("data:"):
                    continue
                json_str = line[len("data:"):].strip()
                if not json_str:
                    continue
                try:
                    chunk = _json.loads(json_str)
                except _json.JSONDecodeError:
                    continue
                token = _gemini_text_from_chunk(chunk)
                if token:
                    yield token
