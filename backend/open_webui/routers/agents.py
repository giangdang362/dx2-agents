"""
REST endpoints for the Agents Directory.
"""

import logging
from typing import Optional

from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from open_webui.internal.db import get_session
from open_webui.models.access_grants import AccessGrants
from open_webui.services.agents import AgentRecord, get_all_agents
from open_webui.utils.auth import get_admin_user, get_verified_user

log = logging.getLogger(__name__)
router = APIRouter()


@router.get("/list", response_model=list[AgentRecord])
async def list_agents(
    user=Depends(get_verified_user),
    db: Session = Depends(get_session),
):
    """
    Return all agents visible to the current user.
    Admins see everything; regular users are filtered by access grants.
    """
    all_agents = await get_all_agents()

    if user.role == "admin":
        return all_agents

    agent_ids = [a.id for a in all_agents]
    accessible_ids = AccessGrants.get_accessible_resource_ids(
        user_id=user.id,
        resource_type="model",
        resource_ids=agent_ids,
        permission="read",
        db=db,
    )
    if accessible_ids is None:
        return []

    return [a for a in all_agents if a.id in accessible_ids]


@router.get("/discover")
async def discover_agents(
    user=Depends(get_admin_user),
):
    """
    Lightweight agent list for the orchestrator (admin-only).
    Returns dict keyed by agent ID with name, description, url, profile_image_url.
    """
    from open_webui.services.agents import get_agents_for_orchestrator

    return await get_agents_for_orchestrator()
