import asyncio
import json
import logging
import time
import uuid
from typing import Optional

from open_webui.utils.orchestration_broadcast import publish

log = logging.getLogger(__name__)


def _user_can_access_model(user, model_id: str, request) -> bool:
    """Return True if user has read access to the given model."""
    from open_webui.utils.models import check_model_access

    model = request.app.state.MODELS.get(model_id)
    if not model:
        return False
    try:
        check_model_access(user, model)
        return True
    except Exception:
        return False


def _elapsed_ms(start_time: float) -> int:
    return int((time.time() - start_time) * 1000)


def _extract_tags(model: dict) -> list[str]:
    """Extract tag names from a model's metadata."""
    meta = model.get("info", {}).get("meta", {})
    tags = meta.get("tags", [])
    return [t.get("name", "") for t in tags if isinstance(t, dict) and t.get("name")]


def _match_keyword_triggers(user_message: str, worker_models: list[dict]) -> list[dict]:
    """Match user message keywords against agent tags and names."""
    if not user_message:
        return []

    msg_lower = user_message.lower()
    matches = []

    for model in worker_models:
        tags = _extract_tags(model)
        name = model.get("name", model["id"]).lower()
        matched_tags = [t for t in tags if t.lower() in msg_lower]

        # Also check if agent name appears in message
        name_match = name in msg_lower

        if matched_tags or name_match:
            matches.append({
                "agent_id": model["id"],
                "agent_name": model.get("name", model["id"]),
                "matched_tags": matched_tags,
                "name_match": name_match,
            })

    return matches


async def _emit(session_id: str, step: str, message: str, **kwargs):
    """Publish an orchestration event to all WebSocket subscribers."""
    try:
        await publish(
            {
                "step": step,
                "session_id": session_id,
                "message": message,
                "timestamp": time.time(),
                **kwargs,
            }
        )
    except Exception as e:
        log.warning(f"Failed to emit orchestration event: {e}")


async def route_to_agent(form_data: dict, user, request) -> Optional[tuple]:
    config = request.app.state.config

    if not config.ENABLE_ORCHESTRATOR:
        return None

    routing_model = config.ORCHESTRATOR_ROUTING_MODEL
    if not routing_model or routing_model not in request.app.state.MODELS:
        return None

    start_time = time.time()
    session_id = str(uuid.uuid4())

    worker_models = [
        model
        for model in request.app.state.MODELS.values()
        if model.get("owned_by") not in ("arena", "orchestrator")
        and not model.get("pipe")
        and model.get("info", {}).get("is_active", True)
    ]

    if not worker_models:
        return None

    # Extract user message
    user_message = ""
    for msg in reversed(form_data.get("messages", [])):
        if msg.get("role") == "user":
            content = msg.get("content", "")
            if isinstance(content, list):
                for part in content:
                    if isinstance(part, dict) and part.get("type") == "text":
                        user_message = part.get("text", "")
                        break
            else:
                user_message = content
            break

    agents = [
        {
            "id": model["id"],
            "name": model.get("name", model["id"]),
            "description": model.get("info", {}).get("meta", {}).get("description", ""),
        }
        for model in worker_models
    ]

    # Step 1: Analyzing message
    message_preview = user_message[:100] + ("..." if len(user_message) > 100 else "")
    await _emit(
        session_id,
        "session_start",
        f'Received message: "{message_preview}". Evaluating against {len(agents)} available agent(s).',
        start_time=start_time,
        elapsed_ms=_elapsed_ms(start_time),
        agent_count=len(agents),
    )

    # Step 2: Evaluate keyword/tag triggers
    keyword_matches = _match_keyword_triggers(user_message, worker_models)
    trigger_count = sum(len(_extract_tags(m)) for m in worker_models)

    await _emit(
        session_id,
        "evaluating_triggers",
        f"Scanned {trigger_count} trigger(s). "
        + (
            f"{len(keyword_matches)} keyword triggers matched."
            if keyword_matches
            else "No keyword triggers matched."
        ),
        elapsed_ms=_elapsed_ms(start_time),
        trigger_count=trigger_count,
        keyword_matches=keyword_matches,
    )

    # Step 3: AI analysis
    await _emit(
        session_id,
        "ai_analysis",
        f"Evaluating with AI routing model...",
        elapsed_ms=_elapsed_ms(start_time),
        agent_count=len(agents),
        agents=agents,
    )

    routing_form_data = {
        "model": routing_model,
        "messages": [
            {
                "role": "system",
                "content": config.ORCHESTRATOR_SYSTEM_PROMPT,
            },
            {
                "role": "user",
                "content": (
                    f"Available agents:\n{json.dumps(agents, indent=2)}\n\n"
                    f"User message: {user_message}\n\n"
                    "Respond with ONLY the agent id that should handle this message. "
                    "If none are suitable, respond with 'NONE'."
                ),
            },
        ],
        "stream": False,
    }

    try:
        from open_webui.utils.chat import generate_chat_completion

        response = await asyncio.wait_for(
            generate_chat_completion(
                request,
                routing_form_data,
                user,
                bypass_filter=True,
            ),
            timeout=10.0,
        )

        selected_id = response["choices"][0]["message"]["content"].strip()

        # Extract routing token usage
        routing_usage = response.get("usage", {})
        routing_tokens = {
            "in": routing_usage.get("prompt_tokens", 0),
            "out": routing_usage.get("completion_tokens", 0),
        }

        if selected_id == "NONE":
            await _emit(
                session_id,
                "no_specialist_match",
                "No keyword triggers matched and no clear specialist intent detected. "
                "The orchestrator will use the default General Assistant.",
                elapsed_ms=_elapsed_ms(start_time),
                routing_tokens=routing_tokens,
            )
            return None

        worker_ids = {m["id"] for m in worker_models}
        if selected_id in worker_ids:
            if not _user_can_access_model(user, selected_id, request):
                await _emit(
                    session_id,
                    "permission_denied",
                    "You don't have permission to access this agent. Please contact your admin.",
                    agent_id=selected_id,
                    elapsed_ms=_elapsed_ms(start_time),
                )
                return "PERMISSION_DENIED", session_id, start_time, routing_tokens

            selected_name = next(
                (a["name"] for a in agents if a["id"] == selected_id),
                selected_id,
            )

            # Emit specialist match
            await _emit(
                session_id,
                "specialist_match",
                f"Matched specialist agent: {selected_name}",
                agent_id=selected_id,
                agent_name=selected_name,
                elapsed_ms=_elapsed_ms(start_time),
                routing_tokens=routing_tokens,
            )

            # Emit agent active
            await _emit(
                session_id,
                "agent_active",
                f"Delegated to {selected_name}",
                agent_id=selected_id,
                agent_label=selected_name,
                agent_icon="🤖",
                agent_dept="",
                action="Handling request",
                elapsed_ms=_elapsed_ms(start_time),
                routing_tokens=routing_tokens,
            )
            return selected_id, session_id, start_time, routing_tokens

        log.warning(f"Orchestrator returned invalid model id: {selected_id!r}")

        await _emit(
            session_id,
            "no_specialist_match",
            f"No specialist agent matched by LLM analysis.",
            elapsed_ms=_elapsed_ms(start_time),
            routing_tokens=routing_tokens,
        )
        return None

    except asyncio.TimeoutError:
        log.warning("Orchestrator routing timed out after 10 seconds")
        await _emit(
            session_id,
            "no_specialist_match",
            "Routing timed out. Falling back to default.",
            elapsed_ms=_elapsed_ms(start_time),
        )
        return None
    except Exception as e:
        log.error(f"Orchestrator routing error: {e}")
        return None
