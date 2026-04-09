from __future__ import annotations

from typing import Iterable, Optional

from sqlalchemy.orm import Session

from open_webui.models.groups import GroupModel, Groups
from open_webui.models.users import UserModel


MANAGED_AGENT_IDS = frozenset(
    {
        "meeting_room_agent_pipe",
        "orchestrator_pipe",
        "kinetix",
        "silicore",
    }
)

FALLBACK_GROUP_AGENT_ACCESS = {
    "CS-Staff": frozenset({"meeting_room_agent_pipe"}),
    "CS-Manager": MANAGED_AGENT_IDS,
    "Technical-Staff": frozenset({"kinetix", "silicore", "orchestrator_pipe"}),
    "Technical-Manager": MANAGED_AGENT_IDS,
    # Support the common typo so existing manual groups still work.
    "Techical-Staff": frozenset({"kinetix", "silicore", "orchestrator_pipe"}),
    "Techical-Manager": MANAGED_AGENT_IDS,
}


def get_managed_agent_id(agent_id: Optional[str]) -> Optional[str]:
    if not isinstance(agent_id, str):
        return None

    normalized_id = agent_id.strip()
    if not normalized_id:
        return None

    prefix = normalized_id.split(".", 1)[0]
    if prefix in MANAGED_AGENT_IDS:
        return prefix

    return normalized_id if normalized_id in MANAGED_AGENT_IDS else None


def _extract_allowed_agent_ids(value: object) -> set[str]:
    if not isinstance(value, list):
        return set()

    return {
        managed_agent_id
        for managed_agent_id in (get_managed_agent_id(item) for item in value)
        if managed_agent_id is not None
    }


def _get_group_agent_policy(
    group: GroupModel,
) -> tuple[bool, set[str]] | None:
    data = group.data if isinstance(group.data, dict) else None
    rbac = data.get("rbac") if data else None
    agent_access = None
    if isinstance(rbac, dict):
        agent_access = rbac.get("agentAccess") or rbac.get("agent_access")

    if isinstance(agent_access, dict):
        allow_all_agents = bool(
            agent_access.get("allowAllAgents") or agent_access.get("allow_all_agents")
        )
        allowed_agent_ids = _extract_allowed_agent_ids(
            agent_access.get("allowedAgentIds")
            or agent_access.get("allowed_agent_ids")
            or []
        )
        return allow_all_agents, allowed_agent_ids

    fallback_allowed_agent_ids = FALLBACK_GROUP_AGENT_ACCESS.get(group.name.strip())
    if fallback_allowed_agent_ids is None:
        return None

    return fallback_allowed_agent_ids == MANAGED_AGENT_IDS, set(
        fallback_allowed_agent_ids
    )


def get_user_managed_agent_scope(
    *,
    user_id: Optional[str] = None,
    groups: Optional[Iterable[GroupModel]] = None,
    db: Optional[Session] = None,
) -> tuple[bool, set[str]]:
    if groups is None:
        if not user_id:
            return False, set()
        groups = Groups.get_groups_by_member_id(user_id, db=db)

    allow_all_agents = False
    allowed_agent_ids: set[str] = set()

    for group in groups:
        policy = _get_group_agent_policy(group)
        if policy is None:
            continue

        group_allow_all_agents, group_allowed_agent_ids = policy
        if group_allow_all_agents:
            allow_all_agents = True

        allowed_agent_ids.update(group_allowed_agent_ids)

    if allow_all_agents:
        return True, set(MANAGED_AGENT_IDS)

    return False, allowed_agent_ids


def get_managed_agent_access_decision(
    user: UserModel,
    agent_id: Optional[str],
    *,
    groups: Optional[Iterable[GroupModel]] = None,
    db: Optional[Session] = None,
) -> bool | None:
    managed_agent_id = get_managed_agent_id(agent_id)
    if managed_agent_id is None:
        return None

    if user.role == "admin":
        return True

    allow_all_agents, allowed_agent_ids = get_user_managed_agent_scope(
        user_id=user.id,
        groups=groups,
        db=db,
    )
    return allow_all_agents or managed_agent_id in allowed_agent_ids
