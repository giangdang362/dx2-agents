"""
Agent aggregation service.

Single source of truth for discovering agents from all sources
(OpenAI connections, pipe functions, workspace models) with
deduplication and fallback logic.
"""

import logging
import ssl
from typing import Optional

import aiohttp
import certifi
from pydantic import BaseModel

log = logging.getLogger(__name__)

_ssl_ctx = ssl.create_default_context(cafile=certifi.where())


class AgentRecord(BaseModel):
    id: str
    name: str
    description: str = ""
    profile_image_url: str = ""
    source: str = "connection"  # "connection" | "function" | "workspace"
    is_active: bool = True
    tags: list[dict] = []
    base_model_id: Optional[str] = None
    workspace_model_id: Optional[str] = None
    connection_url: Optional[str] = None
    owned_by: Optional[str] = None


async def _fetch_connection_agents() -> dict[str, AgentRecord]:
    """Fetch agents from OpenAI-compatible connections."""
    agents: dict[str, AgentRecord] = {}
    try:
        from open_webui.config import OPENAI_API_BASE_URLS, OPENAI_API_KEYS

        base_urls: list[str] = OPENAI_API_BASE_URLS.value or []
        api_keys: list[str] = OPENAI_API_KEYS.value or []

        connector = aiohttp.TCPConnector(ssl=_ssl_ctx)
        for i, base_url in enumerate(base_urls):
            key = api_keys[i] if i < len(api_keys) else ""
            try:
                async with aiohttp.ClientSession(
                    connector=connector, connector_owner=False
                ) as session:
                    async with session.get(
                        f"{base_url}/models",
                        headers={"Authorization": f"Bearer {key}"},
                        timeout=aiohttp.ClientTimeout(total=5),
                    ) as resp:
                        if resp.status != 200:
                            continue
                        data = await resp.json()
                for model in data.get("data", []):
                    model_id = model.get("id", "")
                    if not model_id:
                        continue
                    agents[model_id] = AgentRecord(
                        id=model_id,
                        name=model.get("name", model_id),
                        description=model.get("description", ""),
                        profile_image_url="",
                        source="connection",
                        connection_url=base_url,
                        owned_by=model.get("owned_by", ""),
                    )
            except Exception as e:
                log.warning(f"Failed to query {base_url}: {e!r}")
                continue
        await connector.close()
    except Exception as e:
        log.warning(f"Cannot import Open WebUI config for connections: {e!r}")

    return agents


def _fetch_function_agents() -> tuple[dict[str, AgentRecord], set[str]]:
    """
    Fetch agents from active pipe functions.

    Returns (agents_dict, function_id_prefixes).
    function_id_prefixes contains raw function IDs so we can detect
    manifold sub-pipe workspace models (e.g. "my_pipe.sub-id" belongs
    to function "my_pipe").
    """
    agents: dict[str, AgentRecord] = {}
    fn_prefixes: set[str] = set()
    try:
        from open_webui.models.functions import Functions

        for fn in Functions.get_functions_by_type("pipe", active_only=True) or []:
            fn_prefixes.add(fn.id)
            meta = fn.meta or {}
            description = ""
            if isinstance(meta, dict):
                description = meta.get("description", "")
            elif hasattr(meta, "description"):
                description = meta.description or ""

            agents[fn.id] = AgentRecord(
                id=fn.id,
                name=fn.name,
                description=description,
                source="function",
                is_active=True,
            )
    except Exception as e:
        log.warning(f"Failed to load pipe functions: {e!r}")

    return agents, fn_prefixes


def _fetch_workspace_models() -> list:
    """Fetch all workspace models from the DB."""
    try:
        from open_webui.models.models import Models

        return Models.get_all_models() or []
    except Exception as e:
        log.warning(f"Failed to load workspace models: {e!r}")
        return []


def _merge_field(workspace_val: Optional[str], base_val: str) -> str:
    """Use workspace value if non-empty, otherwise fall back to base."""
    if workspace_val and workspace_val.strip():
        return workspace_val
    return base_val


def _extract_tags(meta) -> list[dict]:
    """Extract tags from a model's meta field."""
    if meta is None:
        return []
    raw = None
    if isinstance(meta, dict):
        raw = meta.get("tags", [])
    elif hasattr(meta, "tags"):
        raw = getattr(meta, "tags", [])
    if not raw:
        return []
    return [t if isinstance(t, dict) else {"name": t} for t in raw]


async def get_all_agents() -> list[AgentRecord]:
    """
    Aggregate agents from all sources with deduplication.

    Priority: workspace overrides > connections > functions.
    Fallback: blank workspace fields inherit from the base model.
    """
    # Step 1: connection agents
    agents = await _fetch_connection_agents()

    # Step 2: function agents (skip if ID already exists from connections)
    fn_agents, fn_prefixes = _fetch_function_agents()
    for fid, agent in fn_agents.items():
        if fid not in agents:
            agents[fid] = agent

    # Step 3: workspace models — merge or add
    workspace_models = _fetch_workspace_models()
    for wm in workspace_models:
        if wm.id == "orchestrator":
            continue

        wm_desc = ""
        wm_avatar = ""
        wm_tags: list[dict] = []
        if wm.meta:
            if isinstance(wm.meta, dict):
                wm_desc = wm.meta.get("description", "") or ""
                wm_avatar = wm.meta.get("profile_image_url", "") or ""
            else:
                wm_desc = getattr(wm.meta, "description", "") or ""
                wm_avatar = getattr(wm.meta, "profile_image_url", "") or ""
            wm_tags = _extract_tags(wm.meta)

        # Check if this workspace model is a manifold sub-pipe of a known
        # function.  Manifold IDs look like "{function_id}.{sub_pipe_id}".
        # When we find one, it *replaces* the raw function entry so there
        # is no duplicate.
        parent_fn_id: str | None = None
        if "." in wm.id:
            prefix = wm.id.split(".")[0]
            if prefix in fn_prefixes:
                parent_fn_id = prefix

        if wm.base_model_id is None:
            # Case A: direct override (same ID as a base model)
            if wm.id in agents:
                if not wm.is_active:
                    del agents[wm.id]
                    continue
                base = agents[wm.id]
                base.name = _merge_field(wm.name, base.name)
                base.description = _merge_field(wm_desc, base.description)
                base.profile_image_url = _merge_field(wm_avatar, base.profile_image_url)
                if wm_tags:
                    base.tags = wm_tags
                base.workspace_model_id = wm.id
            elif parent_fn_id and parent_fn_id in agents:
                # Manifold sub-pipe: replace the raw function entry
                parent = agents.pop(parent_fn_id)
                if not wm.is_active:
                    continue
                agents[wm.id] = AgentRecord(
                    id=wm.id,
                    name=_merge_field(wm.name, parent.name),
                    description=_merge_field(wm_desc, parent.description),
                    profile_image_url=_merge_field(wm_avatar, parent.profile_image_url),
                    source="function",
                    is_active=True,
                    tags=wm_tags if wm_tags else parent.tags,
                    workspace_model_id=wm.id,
                )
            else:
                # Pure workspace-only model (no matching base)
                if not wm.is_active:
                    continue
                agents[wm.id] = AgentRecord(
                    id=wm.id,
                    name=wm.name,
                    description=wm_desc,
                    profile_image_url=wm_avatar,
                    source="workspace",
                    is_active=wm.is_active,
                    tags=wm_tags,
                    workspace_model_id=wm.id,
                )
        else:
            # Case B: derived model (base_model_id is set)
            if not wm.is_active or wm.id in agents:
                continue
            # Inherit from base model if fields are blank
            base_agent = agents.get(wm.base_model_id)
            # Also check if base_model_id is a manifold parent
            if not base_agent and wm.base_model_id in fn_prefixes:
                base_agent = agents.get(wm.base_model_id)
            base_desc = base_agent.description if base_agent else ""
            base_avatar = base_agent.profile_image_url if base_agent else ""

            agents[wm.id] = AgentRecord(
                id=wm.id,
                name=wm.name,
                description=_merge_field(wm_desc, base_desc),
                profile_image_url=_merge_field(wm_avatar, base_avatar),
                source="workspace",
                is_active=True,
                tags=wm_tags,
                base_model_id=wm.base_model_id,
                workspace_model_id=wm.id,
                owned_by=base_agent.owned_by if base_agent else None,
            )

    return list(agents.values())


async def get_agents_for_orchestrator() -> dict[str, dict]:
    """
    Return agents in the format expected by the orchestrator pipe:
    {agent_id: {"name", "description", "url", "profile_image_url"}}
    """
    all_agents = await get_all_agents()
    result: dict[str, dict] = {}
    for agent in all_agents:
        if agent.id == "orchestrator":
            continue
        result[agent.id] = {
            "name": agent.name,
            "description": agent.description,
            "url": agent.connection_url,  # None for non-connection agents
            "profile_image_url": agent.profile_image_url,
        }
    return result
