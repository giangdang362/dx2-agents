#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal

import requests


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DATA_FILE = (
    REPO_ROOT / "backend" / "open_webui" / "test" / "data" / "dummy_gmail_accounts.json"
)


def _default_backend_port() -> str:
    return (
        os.environ.get("OPEN_WEBUI_BACKEND_PORT")
        or os.environ.get("VITE_BACKEND_PORT")
        or os.environ.get("BACKEND_PORT")
        or os.environ.get("PORT")
        or "8080"
    )


def _default_base_url() -> str:
    explicit_base_url = os.environ.get("OPEN_WEBUI_BASE_URL") or os.environ.get(
        "WEBUI_URL"
    )
    if explicit_base_url:
        return explicit_base_url.rstrip("/")

    host = os.environ.get("OPEN_WEBUI_BACKEND_HOST") or os.environ.get(
        "OPEN_WEBUI_HOST", "localhost"
    )
    return f"http://{host}:{_default_backend_port()}"


DEFAULT_BASE_URL = _default_base_url()
DEFAULT_ADMIN_EMAIL = os.environ.get("OPEN_WEBUI_ADMIN_EMAIL") or os.environ.get(
    "WEBUI_ADMIN_EMAIL", ""
)
DEFAULT_ADMIN_PASSWORD = os.environ.get(
    "OPEN_WEBUI_ADMIN_PASSWORD"
) or os.environ.get("WEBUI_ADMIN_PASSWORD", "")
DEFAULT_ADMIN_API_KEY = os.environ.get("OPEN_WEBUI_ADMIN_API_KEY", "")

SIGNIN_PATH = "/api/v1/auths/signin"
SIGNUP_PATH = "/api/v1/auths/signup"
ADD_USER_PATH = "/api/v1/auths/add"
GROUPS_PATH = "/api/v1/groups/"
GROUP_CREATE_PATH = "/api/v1/groups/create"
USERS_PATH = "/api/v1/users/"
USERS_ALL_PATH = "/api/v1/users/all"
USER_SETTINGS_PATH = "/api/v1/users/user/settings"
USER_SETTINGS_UPDATE_PATH = "/api/v1/users/user/settings/update"

EMAIL_TAKEN_MARKERS = (
    "already registered",
    "email taken",
    "email is already",
)

RBAC_SCHEMA = "vn_b2b_team_agent_access/v1"
RBAC_TEAMS = ("CS", "Technical")
RBAC_LEVELS = {
    "staff": {"code": "L1", "name": "Staff", "rank": 1, "title": "Staff"},
    "manager": {"code": "L2", "name": "Manager", "rank": 2, "title": "Manager"},
}
RBAC_TEAM_ALIASES = {
    "cs": "CS",
    "customerservice": "CS",
    "technical": "Technical",
    "techical": "Technical",
}
RBAC_LEVEL_ALIASES = {
    "l1": "staff",
    "staff": "staff",
    "l2": "manager",
    "manager": "manager",
}
RBAC_AUDIT_FIELDS = (
    "user_id",
    "active_group_context",
    "resource",
    "action",
    "timestamp",
)
TEAM_AGENT_ACCESS = {
    "CS": ("meeting_room_agent_pipe",),
    "Technical": ("kinetix", "silicore", "orchestrator_pipe"),
}
ALL_AGENT_IDS = tuple(
    dict.fromkeys(
        agent_id
        for allowed_agent_ids in TEAM_AGENT_ACCESS.values()
        for agent_id in allowed_agent_ids
    )
)

MANAGER_WORKSPACE_PERMISSIONS = {
    "workspace": {
        "models": True,
        "knowledge": True,
        "prompts": True,
        "tools": True,
        "skills": True,
        "models_import": True,
        "models_export": True,
        "prompts_import": True,
        "prompts_export": True,
        "tools_import": True,
        "tools_export": True,
    }
}

EMPLOYEE_GROUP_PERMISSIONS = {
    "workspace": {
        "models": True,
        "knowledge": True,
        "prompts": True,
        "tools": True,
        "skills": True,
    }
}


PermissionProfile = Literal["auto", "manager", "employee"]


@dataclass(frozen=True)
class SignupAccount:
    group: str
    name: str
    email: str
    password: str


@dataclass(frozen=True)
class UserSeedPlan:
    name: str
    email: str
    password: str
    groups: tuple[str, ...]


@dataclass(frozen=True)
class AccountResult:
    status: Literal["created", "existing", "failed"]
    detail: str
    user_id: str | None = None


@dataclass(frozen=True)
class RbacGroupSpec:
    team: str
    level_code: str
    level_name: str
    level_rank: int
    level_title: str

    @property
    def canonical_name(self) -> str:
        return f"{self.team}-{self.level_name}"


@dataclass(frozen=True)
class GroupSeedConfig:
    name: str
    description: str
    permissions: dict[str, Any]
    data: dict[str, Any] | None = None


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Create dummy test users and load each JSON batch into its matching "
            "Open WebUI user group."
        )
    )
    parser.add_argument(
        "--base-url",
        default=DEFAULT_BASE_URL,
        help=f"Base URL for the running app. Default: {DEFAULT_BASE_URL}",
    )
    parser.add_argument(
        "--data-file",
        type=Path,
        default=DEFAULT_DATA_FILE,
        help=f"Path to the dummy account JSON file. Default: {DEFAULT_DATA_FILE}",
    )
    parser.add_argument(
        "--group",
        action="append",
        dest="groups",
        help="Optional group name to import. Repeat to import multiple groups.",
    )
    parser.add_argument(
        "--admin-email",
        default=DEFAULT_ADMIN_EMAIL,
        help=(
            "Admin email for group management. Defaults to OPEN_WEBUI_ADMIN_EMAIL "
            "or WEBUI_ADMIN_EMAIL."
        ),
    )
    parser.add_argument(
        "--admin-password",
        default=DEFAULT_ADMIN_PASSWORD,
        help=(
            "Admin password for group management. Defaults to "
            "OPEN_WEBUI_ADMIN_PASSWORD or WEBUI_ADMIN_PASSWORD."
        ),
    )
    parser.add_argument(
        "--admin-api-key",
        default=DEFAULT_ADMIN_API_KEY,
        help=(
            "Admin API key. If set, this is used instead of admin email/password."
        ),
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=15.0,
        help="Request timeout in seconds. Default: 15",
    )
    parser.add_argument(
        "--insecure",
        action="store_true",
        help="Disable TLS certificate verification.",
    )
    parser.add_argument(
        "--permission-profile",
        choices=("auto", "manager", "employee"),
        default="auto",
        help=(
            "Permission preset to apply to created/updated groups. "
            "Use 'manager' or 'employee' to force a preset for all groups, "
            "or 'auto' to infer from the group name. Team groups such as "
            "CS-Staff and Technical-Manager use the embedded RBAC policy instead."
        ),
    )
    return parser.parse_args()


def load_accounts(
    data_file: Path, selected_groups: list[str] | None
) -> dict[str, list[SignupAccount]]:
    if not data_file.is_file():
        raise FileNotFoundError(f"Data file not found: {data_file}")

    raw_data = json.loads(data_file.read_text(encoding="utf-8"))
    if not isinstance(raw_data, dict):
        raise ValueError("Dummy account file must be a JSON object keyed by group name.")

    available_groups = list(raw_data.keys())
    group_names = selected_groups or available_groups

    unknown_groups = [group for group in group_names if group not in raw_data]
    if unknown_groups:
        joined_unknown = ", ".join(unknown_groups)
        joined_available = ", ".join(available_groups) or "(none)"
        raise ValueError(
            f"Unknown group(s): {joined_unknown}. Available groups: {joined_available}"
        )

    accounts_by_group: dict[str, list[SignupAccount]] = {}
    for group_name in group_names:
        normalized_group_name = canonicalize_group_name(group_name)
        entries = raw_data[group_name]
        if not isinstance(entries, list):
            raise ValueError(f"Group '{group_name}' must contain a JSON array.")

        group_accounts: list[SignupAccount] = []
        for index, entry in enumerate(entries, start=1):
            if not isinstance(entry, dict):
                raise ValueError(
                    f"Entry {index} in group '{group_name}' must be a JSON object."
                )

            name = read_required_str(entry, "name", group_name, index)
            email = read_required_str(entry, "email", group_name, index).lower()
            password = read_required_str(entry, "password", group_name, index)
            group_accounts.append(
                SignupAccount(
                    group=normalized_group_name,
                    name=name,
                    email=email,
                    password=password,
                )
            )

        accounts_by_group.setdefault(normalized_group_name, []).extend(group_accounts)

    return accounts_by_group


def read_required_str(
    entry: dict[str, Any], field: str, group_name: str, index: int
) -> str:
    value = entry.get(field)
    if not isinstance(value, str) or not value.strip():
        raise ValueError(
            f"Entry {index} in group '{group_name}' is missing a valid '{field}' value."
        )
    return value.strip()


def build_url(base_url: str, path: str) -> str:
    return f"{base_url.rstrip('/')}{path}"


def merge_nested_dicts(base: dict[str, Any], overrides: dict[str, Any]) -> dict[str, Any]:
    merged = dict(base)

    for key, value in overrides.items():
        existing = merged.get(key)
        if isinstance(existing, dict) and isinstance(value, dict):
            merged[key] = merge_nested_dicts(existing, value)
        else:
            merged[key] = value

    return merged


def normalize_lookup_token(value: str) -> str:
    return "".join(char for char in value.strip().lower() if char.isalnum())


def parse_rbac_group_name(group_name: str) -> RbacGroupSpec | None:
    team_part, separator, level_part = group_name.strip().partition("-")
    if not separator:
        return None

    team = RBAC_TEAM_ALIASES.get(normalize_lookup_token(team_part))
    level_key = RBAC_LEVEL_ALIASES.get(normalize_lookup_token(level_part))
    if not team or not level_key:
        return None

    level = RBAC_LEVELS[level_key]
    return RbacGroupSpec(
        team=team,
        level_code=level["code"],
        level_name=level["name"],
        level_rank=level["rank"],
        level_title=level["title"],
    )


def canonicalize_group_name(group_name: str) -> str:
    spec = parse_rbac_group_name(group_name)
    if spec:
        return spec.canonical_name
    return group_name.strip()


def build_user_seed_plans(
    accounts_by_group: dict[str, list[SignupAccount]]
) -> dict[str, UserSeedPlan]:
    plans_by_email: dict[str, dict[str, Any]] = {}

    for group_accounts in accounts_by_group.values():
        for account in group_accounts:
            existing = plans_by_email.get(account.email)
            if existing is None:
                plans_by_email[account.email] = {
                    "name": account.name,
                    "password": account.password,
                    "groups": [account.group],
                }
                continue

            if existing["name"] != account.name:
                raise ValueError(
                    "Conflicting names for the same email in dummy account data: "
                    f"{account.email}"
                )

            if existing["password"] != account.password:
                raise ValueError(
                    "Conflicting passwords for the same email in dummy account data: "
                    f"{account.email}"
                )

            existing["groups"].append(account.group)

    return {
        email: UserSeedPlan(
            name=payload["name"],
            email=email,
            password=payload["password"],
            groups=tuple(dict.fromkeys(payload["groups"])),
        )
        for email, payload in plans_by_email.items()
    }


def get_group_permissions(
    permission_profile: PermissionProfile, group_name: str
) -> dict[str, Any]:
    if permission_profile == "manager":
        return MANAGER_WORKSPACE_PERMISSIONS

    if permission_profile == "employee":
        return EMPLOYEE_GROUP_PERMISSIONS

    normalized_group_name = group_name.strip().lower()
    if "manager" in normalized_group_name:
        return MANAGER_WORKSPACE_PERMISSIONS

    return EMPLOYEE_GROUP_PERMISSIONS


def get_rbac_group_permissions(group_spec: RbacGroupSpec) -> dict[str, Any]:
    if group_spec.level_rank >= 2:
        return json.loads(json.dumps(MANAGER_WORKSPACE_PERMISSIONS))

    return json.loads(json.dumps(EMPLOYEE_GROUP_PERMISSIONS))


def get_group_agent_access(group_spec: RbacGroupSpec) -> tuple[bool, list[str]]:
    if group_spec.level_name == "Manager":
        return True, list(ALL_AGENT_IDS)

    return False, list(TEAM_AGENT_ACCESS[group_spec.team])


def build_rbac_group_description(group_spec: RbacGroupSpec) -> str:
    allow_all_agents, allowed_agent_ids = get_group_agent_access(group_spec)
    access_summary = "all managed agents" if allow_all_agents else ", ".join(
        allowed_agent_ids
    )
    return (
        f"Vietnam B2B {group_spec.team} {group_spec.level_title} group "
        f"({access_summary})."
    )


def build_rbac_group_data(group_spec: RbacGroupSpec) -> dict[str, Any]:
    allow_all_agents, allowed_agent_ids = get_group_agent_access(group_spec)

    return {
        "rbac": {
            "schema": RBAC_SCHEMA,
            "organization": "vietnam_b2b",
            "team": group_spec.team,
            "level": {
                "code": group_spec.level_code,
                "name": group_spec.level_name,
                "rank": group_spec.level_rank,
            },
            "agentAccess": {
                "allowAllAgents": allow_all_agents,
                "allowedAgentIds": allowed_agent_ids,
            },
            "requires_active_group_context": True,
            "audit": {
                "required": True,
                "fields": list(RBAC_AUDIT_FIELDS),
            },
        }
    }


def get_group_seed_configuration(
    permission_profile: PermissionProfile, group_name: str
) -> GroupSeedConfig:
    normalized_group_name = canonicalize_group_name(group_name)
    group_spec = parse_rbac_group_name(normalized_group_name)
    if group_spec:
        return GroupSeedConfig(
            name=group_spec.canonical_name,
            description=build_rbac_group_description(group_spec),
            permissions=get_rbac_group_permissions(group_spec),
            data=build_rbac_group_data(group_spec),
        )

    return GroupSeedConfig(
        name=normalized_group_name,
        description=normalized_group_name,
        permissions=get_group_permissions(permission_profile, normalized_group_name),
    )


def send_request(
    session: requests.Session,
    method: str,
    url: str,
    *,
    timeout: float,
    verify_tls: bool,
    **kwargs: Any,
) -> requests.Response:
    try:
        return session.request(
            method=method,
            url=url,
            timeout=timeout,
            verify=verify_tls,
            **kwargs,
        )
    except requests.RequestException as exc:
        raise RuntimeError(str(exc)) from exc


def extract_error_detail(response: requests.Response) -> str:
    try:
        payload = response.json()
    except ValueError:
        text = response.text.strip()
        return text or f"HTTP {response.status_code}"

    if isinstance(payload, dict):
        detail = payload.get("detail")
        if isinstance(detail, list):
            return "; ".join(str(item) for item in detail)
        if detail:
            return str(detail)

    return str(payload)


def is_existing_account_error(detail: str) -> bool:
    detail_lower = detail.lower()
    return any(marker in detail_lower for marker in EMAIL_TAKEN_MARKERS)


def authenticate_admin(
    session: requests.Session,
    base_url: str,
    admin_api_key: str,
    admin_email: str,
    admin_password: str,
    timeout: float,
    verify_tls: bool,
) -> dict[str, str]:
    if admin_api_key:
        return {"Authorization": f"Bearer {admin_api_key.strip()}"}

    if not admin_email or not admin_password:
        raise ValueError(
            "Group loading requires admin credentials. Pass --admin-api-key or "
            "--admin-email and --admin-password."
        )

    response = send_request(
        session=session,
        method="POST",
        url=build_url(base_url, SIGNIN_PATH),
        json={"email": admin_email, "password": admin_password},
        timeout=timeout,
        verify_tls=verify_tls,
    )

    if not response.ok:
        raise RuntimeError(f"Admin sign-in failed: {extract_error_detail(response)}")

    payload = response.json()
    token = payload.get("token")
    role = payload.get("role")
    if not token:
        raise RuntimeError("Admin sign-in succeeded but no token was returned.")
    if role != "admin":
        raise RuntimeError(f"Authenticated user is '{role}', not 'admin'.")

    return {"Authorization": f"Bearer {token}"}


def authenticate_user(
    session: requests.Session,
    base_url: str,
    email: str,
    password: str,
    timeout: float,
    verify_tls: bool,
) -> dict[str, str]:
    response = send_request(
        session=session,
        method="POST",
        url=build_url(base_url, SIGNIN_PATH),
        json={"email": email, "password": password},
        timeout=timeout,
        verify_tls=verify_tls,
    )

    if not response.ok:
        raise RuntimeError(
            f"User sign-in failed for {email}: {extract_error_detail(response)}"
        )

    payload = response.json()
    token = payload.get("token")
    if not token:
        raise RuntimeError(f"User sign-in for {email} succeeded but no token was returned.")

    return {"Authorization": f"Bearer {token}"}


def signup_account(
    session: requests.Session,
    base_url: str,
    account: SignupAccount,
    admin_headers: dict[str, str],
    timeout: float,
    verify_tls: bool,
) -> AccountResult:
    signup_response = send_request(
        session=session,
        method="POST",
        url=build_url(base_url, SIGNUP_PATH),
        json={
            "name": account.name,
            "email": account.email,
            "password": account.password,
        },
        timeout=timeout,
        verify_tls=verify_tls,
    )

    if signup_response.ok:
        payload = signup_response.json()
        return AccountResult(
            status="created",
            detail="signup succeeded",
            user_id=payload.get("id"),
        )

    detail = extract_error_detail(signup_response)
    if signup_response.status_code == 400 and is_existing_account_error(detail):
        return AccountResult(status="existing", detail=detail)

    if signup_response.status_code == 403:
        return add_user_as_admin(
            session=session,
            base_url=base_url,
            account=account,
            admin_headers=admin_headers,
            timeout=timeout,
            verify_tls=verify_tls,
            reason=detail,
        )

    return AccountResult(
        status="failed",
        detail=f"HTTP {signup_response.status_code}: {detail}",
    )


def add_user_as_admin(
    session: requests.Session,
    base_url: str,
    account: SignupAccount,
    admin_headers: dict[str, str],
    timeout: float,
    verify_tls: bool,
    reason: str,
) -> AccountResult:
    response = send_request(
        session=session,
        method="POST",
        url=build_url(base_url, ADD_USER_PATH),
        headers=admin_headers,
        json={
            "name": account.name,
            "email": account.email,
            "password": account.password,
            "role": "user",
        },
        timeout=timeout,
        verify_tls=verify_tls,
    )

    if response.ok:
        payload = response.json()
        return AccountResult(
            status="created",
            detail=f"created via admin add ({reason})",
            user_id=payload.get("id"),
        )

    detail = extract_error_detail(response)
    if response.status_code == 400 and is_existing_account_error(detail):
        return AccountResult(status="existing", detail=detail)

    return AccountResult(
        status="failed",
        detail=f"HTTP {response.status_code}: {detail}",
    )


def get_or_create_group(
    session: requests.Session,
    base_url: str,
    group_name: str,
    permission_profile: PermissionProfile,
    admin_headers: dict[str, str],
    timeout: float,
    verify_tls: bool,
) -> str:
    group_config = get_group_seed_configuration(permission_profile, group_name)

    response = send_request(
        session=session,
        method="GET",
        url=build_url(base_url, GROUPS_PATH),
        headers=admin_headers,
        timeout=timeout,
        verify_tls=verify_tls,
    )
    if not response.ok:
        raise RuntimeError(f"Could not list groups: {extract_error_detail(response)}")

    payload = response.json()
    if not isinstance(payload, list):
        raise RuntimeError("Unexpected groups response payload.")

    exact_matches = [
        item
        for item in payload
        if isinstance(item, dict)
        and item.get("name") == group_config.name
        and item.get("id")
    ]
    if exact_matches:
        existing_group = exact_matches[0]
        group_id = str(existing_group["id"])
        existing_permissions = existing_group.get("permissions") or {}
        existing_data = existing_group.get("data") or {}
        existing_description = str(existing_group.get("description") or "").strip()
        merged_permissions = merge_nested_dicts(
            existing_permissions, group_config.permissions
        )
        merged_data = (
            merge_nested_dicts(existing_data, group_config.data)
            if group_config.data
            else existing_data
        )
        target_description = existing_description
        if not existing_description or existing_description == existing_group.get("name"):
            target_description = group_config.description

        if (
            merged_permissions != existing_permissions
            or merged_data != existing_data
            or target_description != existing_description
        ):
            update_response = send_request(
                session=session,
                method="POST",
                url=build_url(base_url, f"/api/v1/groups/id/{group_id}/update"),
                headers=admin_headers,
                json={
                    "name": existing_group.get("name") or group_config.name,
                    "description": target_description,
                    "permissions": merged_permissions,
                    "data": merged_data or None,
                },
                timeout=timeout,
                verify_tls=verify_tls,
            )
            if not update_response.ok:
                raise RuntimeError(
                    f"Could not update group '{group_config.name}' permissions: "
                    f"{extract_error_detail(update_response)}"
                )

        return group_id

    create_response = send_request(
        session=session,
        method="POST",
        url=build_url(base_url, GROUP_CREATE_PATH),
        headers=admin_headers,
        json={
            "name": group_config.name,
            "description": group_config.description,
            "permissions": group_config.permissions,
            "data": group_config.data,
        },
        timeout=timeout,
        verify_tls=verify_tls,
    )
    if not create_response.ok:
        raise RuntimeError(
            f"Could not create group '{group_config.name}': "
            f"{extract_error_detail(create_response)}"
        )

    created_group = create_response.json()
    group_id = created_group.get("id")
    if not group_id:
        raise RuntimeError(f"Group '{group_config.name}' was created without an id.")

    return str(group_id)


def find_exact_user(users: list[dict[str, Any]], email: str) -> dict[str, Any] | None:
    email_lower = email.lower()
    for user in users:
        if isinstance(user, dict) and str(user.get("email", "")).lower() == email_lower:
            return user
    return None


def resolve_user_id_by_email(
    session: requests.Session,
    base_url: str,
    email: str,
    admin_headers: dict[str, str],
    timeout: float,
    verify_tls: bool,
) -> str | None:
    response = send_request(
        session=session,
        method="GET",
        url=build_url(base_url, USERS_PATH),
        headers=admin_headers,
        params={"query": email},
        timeout=timeout,
        verify_tls=verify_tls,
    )
    if not response.ok:
        raise RuntimeError(f"Could not search users: {extract_error_detail(response)}")

    payload = response.json()
    if isinstance(payload, dict):
        user = find_exact_user(payload.get("users", []), email)
        if user and user.get("id"):
            return str(user["id"])

    all_users_response = send_request(
        session=session,
        method="GET",
        url=build_url(base_url, USERS_ALL_PATH),
        headers=admin_headers,
        timeout=timeout,
        verify_tls=verify_tls,
    )
    if not all_users_response.ok:
        raise RuntimeError(
            f"Could not list users for exact lookup: "
            f"{extract_error_detail(all_users_response)}"
        )

    all_users_payload = all_users_response.json()
    if isinstance(all_users_payload, list):
        user = find_exact_user(all_users_payload, email)
        if user and user.get("id"):
            return str(user["id"])

    return None


def add_users_to_group(
    session: requests.Session,
    base_url: str,
    group_id: str,
    user_ids: list[str],
    admin_headers: dict[str, str],
    timeout: float,
    verify_tls: bool,
) -> None:
    response = send_request(
        session=session,
        method="POST",
        url=build_url(base_url, f"/api/v1/groups/id/{group_id}/users/add"),
        headers=admin_headers,
        json={"user_ids": user_ids},
        timeout=timeout,
        verify_tls=verify_tls,
    )
    if not response.ok:
        raise RuntimeError(
            f"Could not add users to group {group_id}: {extract_error_detail(response)}"
        )


def get_user_settings(
    session: requests.Session,
    base_url: str,
    user_headers: dict[str, str],
    timeout: float,
    verify_tls: bool,
) -> dict[str, Any]:
    response = send_request(
        session=session,
        method="GET",
        url=build_url(base_url, USER_SETTINGS_PATH),
        headers=user_headers,
        timeout=timeout,
        verify_tls=verify_tls,
    )
    if not response.ok:
        raise RuntimeError(f"Could not fetch user settings: {extract_error_detail(response)}")

    payload = response.json()
    if isinstance(payload, dict):
        return payload

    return {}


def update_user_settings(
    session: requests.Session,
    base_url: str,
    user_headers: dict[str, str],
    settings: dict[str, Any],
    timeout: float,
    verify_tls: bool,
) -> None:
    response = send_request(
        session=session,
        method="POST",
        url=build_url(base_url, USER_SETTINGS_UPDATE_PATH),
        headers=user_headers,
        json=settings,
        timeout=timeout,
        verify_tls=verify_tls,
    )
    if not response.ok:
        raise RuntimeError(f"Could not update user settings: {extract_error_detail(response)}")


def build_group_context(group_name: str) -> dict[str, Any]:
    group_spec = parse_rbac_group_name(group_name)
    if not group_spec:
        return {"group": group_name}

    allow_all_agents, allowed_agent_ids = get_group_agent_access(group_spec)
    return {
        "group": group_spec.canonical_name,
        "team": group_spec.team,
        "level": {
            "code": group_spec.level_code,
            "name": group_spec.level_name,
            "rank": group_spec.level_rank,
        },
        "agentAccess": {
            "allowAllAgents": allow_all_agents,
            "allowedAgentIds": allowed_agent_ids,
        },
    }


def build_user_rbac_settings(group_names: list[str]) -> dict[str, Any]:
    normalized_group_names = list(dict.fromkeys(group_names))
    available_contexts = [
        build_group_context(group_name) for group_name in normalized_group_names
    ]
    active_group_context = normalized_group_names[0] if len(normalized_group_names) == 1 else None

    active_team_context: str | None = None
    if active_group_context:
        active_context = available_contexts[0]
        if isinstance(active_context, dict):
            active_team_context = active_context.get("team")

    return {
        "ui": {
            "rbac": {
                "schema": RBAC_SCHEMA,
                "requiresActiveGroupContext": True,
                "mustSelectActiveGroupContext": len(normalized_group_names) > 1,
                "activeGroupContext": active_group_context,
                "activeTeamContext": active_team_context,
                "availableGroupContexts": available_contexts,
                "auditLog": {
                    "required": True,
                    "fields": list(RBAC_AUDIT_FIELDS),
                },
            }
        }
    }


def seed_user_rbac_context(
    session: requests.Session,
    base_url: str,
    user_plan: UserSeedPlan,
    group_names: list[str],
    timeout: float,
    verify_tls: bool,
) -> str | None:
    user_headers = authenticate_user(
        session=session,
        base_url=base_url,
        email=user_plan.email,
        password=user_plan.password,
        timeout=timeout,
        verify_tls=verify_tls,
    )
    existing_settings = get_user_settings(
        session=session,
        base_url=base_url,
        user_headers=user_headers,
        timeout=timeout,
        verify_tls=verify_tls,
    )
    updated_settings = merge_nested_dicts(
        existing_settings,
        build_user_rbac_settings(group_names),
    )
    update_user_settings(
        session=session,
        base_url=base_url,
        user_headers=user_headers,
        settings=updated_settings,
        timeout=timeout,
        verify_tls=verify_tls,
    )

    unique_group_names = list(dict.fromkeys(group_names))
    if len(unique_group_names) == 1:
        return unique_group_names[0]

    return None


def main() -> int:
    args = parse_args()
    try:
        accounts_by_group = load_accounts(args.data_file, args.groups)
        user_seed_plans = build_user_seed_plans(accounts_by_group)
    except (FileNotFoundError, ValueError, json.JSONDecodeError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1

    total_accounts = sum(len(accounts) for accounts in accounts_by_group.values())
    if total_accounts == 0:
        print("No accounts found to import.", file=sys.stderr)
        return 1

    verify_tls = not args.insecure

    with requests.Session() as session:
        try:
            admin_headers = authenticate_admin(
                session=session,
                base_url=args.base_url,
                admin_api_key=args.admin_api_key,
                admin_email=args.admin_email,
                admin_password=args.admin_password,
                timeout=args.timeout,
                verify_tls=verify_tls,
            )
        except (ValueError, RuntimeError) as exc:
            print(f"Error: {exc}", file=sys.stderr)
            return 1

        print(f"Data file: {args.data_file}")
        print(f"Base URL: {args.base_url.rstrip('/')}")
        print(f"Groups to process: {len(accounts_by_group)}")
        print(f"Accounts to process: {total_accounts}")

        created = 0
        existing = 0
        assigned = 0
        failed = 0
        context_seeded = 0
        context_failed = 0
        assigned_groups_by_email: dict[str, list[str]] = {}

        for group_name, group_accounts in accounts_by_group.items():
            try:
                group_id = get_or_create_group(
                    session=session,
                    base_url=args.base_url,
                    group_name=group_name,
                    permission_profile=args.permission_profile,
                    admin_headers=admin_headers,
                    timeout=args.timeout,
                    verify_tls=verify_tls,
                )
            except RuntimeError as exc:
                failed += len(group_accounts)
                print(f"[failed]  {group_name} - {exc}")
                continue

            print(f"[group]   {group_name} -> {group_id}")

            resolved_accounts: list[tuple[SignupAccount, str]] = []
            for account in group_accounts:
                result = signup_account(
                    session=session,
                    base_url=args.base_url,
                    account=account,
                    admin_headers=admin_headers,
                    timeout=args.timeout,
                    verify_tls=verify_tls,
                )

                if result.status == "created":
                    created += 1
                    print(f"[created] {account.group} {account.email} - {result.detail}")
                elif result.status == "existing":
                    existing += 1
                    print(f"[exists]  {account.group} {account.email} - {result.detail}")
                else:
                    failed += 1
                    print(f"[failed]  {account.group} {account.email} - {result.detail}")
                    continue

                user_id = result.user_id
                if not user_id:
                    try:
                        user_id = resolve_user_id_by_email(
                            session=session,
                            base_url=args.base_url,
                            email=account.email,
                            admin_headers=admin_headers,
                            timeout=args.timeout,
                            verify_tls=verify_tls,
                        )
                    except RuntimeError as exc:
                        failed += 1
                        print(
                            f"[failed]  {account.group} {account.email} - "
                            f"could not resolve user id: {exc}"
                        )
                        continue

                if not user_id:
                    failed += 1
                    print(
                        f"[failed]  {account.group} {account.email} - "
                        "user exists but no matching user id was found"
                    )
                    continue

                resolved_accounts.append((account, user_id))

            deduped_user_ids = list(
                dict.fromkeys(user_id for _, user_id in resolved_accounts)
            )
            if not deduped_user_ids:
                print(f"[group]   {group_name} - no users available for assignment")
                continue

            try:
                add_users_to_group(
                    session=session,
                    base_url=args.base_url,
                    group_id=group_id,
                    user_ids=deduped_user_ids,
                    admin_headers=admin_headers,
                    timeout=args.timeout,
                    verify_tls=verify_tls,
                )
            except RuntimeError as exc:
                failed += len(deduped_user_ids)
                print(f"[failed]  {group_name} - {exc}")
                continue

            assigned += len(deduped_user_ids)
            for email in dict.fromkeys(account.email for account, _ in resolved_accounts):
                assigned_groups_by_email.setdefault(email, []).append(group_name)
            print(
                f"[assigned] {group_name} {len(deduped_user_ids)} user(s) -> {group_id}"
            )

        for email, group_names in assigned_groups_by_email.items():
            user_plan = user_seed_plans.get(email)
            if not user_plan:
                continue

            try:
                active_group_context = seed_user_rbac_context(
                    session=session,
                    base_url=args.base_url,
                    user_plan=user_plan,
                    group_names=group_names,
                    timeout=args.timeout,
                    verify_tls=verify_tls,
                )
                context_seeded += 1
                print(
                    f"[context] {email} active_group="
                    f"{active_group_context or 'explicit-switch-required'}"
                )
            except RuntimeError as exc:
                context_failed += 1
                print(f"[failed]  {email} - could not seed RBAC context: {exc}")

    print(
        "Summary: "
        f"created={created}, existing={existing}, assigned={assigned}, "
        f"failed={failed}, context_seeded={context_seeded}, "
        f"context_failed={context_failed}, total={total_accounts}"
    )
    return 1 if failed or context_failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
