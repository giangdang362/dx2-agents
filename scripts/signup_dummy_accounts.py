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
DEFAULT_BASE_URL = os.environ.get("OPEN_WEBUI_BASE_URL", "http://localhost:8080")
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

EMAIL_TAKEN_MARKERS = (
    "already registered",
    "email taken",
    "email is already",
)


@dataclass(frozen=True)
class SignupAccount:
    group: str
    name: str
    email: str
    password: str


@dataclass(frozen=True)
class AccountResult:
    status: Literal["created", "existing", "failed"]
    detail: str
    user_id: str | None = None


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
                    group=group_name,
                    name=name,
                    email=email,
                    password=password,
                )
            )

        accounts_by_group[group_name] = group_accounts

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
    admin_headers: dict[str, str],
    timeout: float,
    verify_tls: bool,
) -> str:
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
        if isinstance(item, dict) and item.get("name") == group_name and item.get("id")
    ]
    if exact_matches:
        return str(exact_matches[0]["id"])

    create_response = send_request(
        session=session,
        method="POST",
        url=build_url(base_url, GROUP_CREATE_PATH),
        headers=admin_headers,
        json={
            "name": group_name,
            "description": f"Dummy batch group imported from {DEFAULT_DATA_FILE.name}",
        },
        timeout=timeout,
        verify_tls=verify_tls,
    )
    if not create_response.ok:
        raise RuntimeError(
            f"Could not create group '{group_name}': "
            f"{extract_error_detail(create_response)}"
        )

    created_group = create_response.json()
    group_id = created_group.get("id")
    if not group_id:
        raise RuntimeError(f"Group '{group_name}' was created without an id.")

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


def main() -> int:
    args = parse_args()
    try:
        accounts_by_group = load_accounts(args.data_file, args.groups)
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

        for group_name, group_accounts in accounts_by_group.items():
            try:
                group_id = get_or_create_group(
                    session=session,
                    base_url=args.base_url,
                    group_name=group_name,
                    admin_headers=admin_headers,
                    timeout=args.timeout,
                    verify_tls=verify_tls,
                )
            except RuntimeError as exc:
                failed += len(group_accounts)
                print(f"[failed]  {group_name} - {exc}")
                continue

            print(f"[group]   {group_name} -> {group_id}")

            group_user_ids: list[str] = []
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

                group_user_ids.append(user_id)

            deduped_user_ids = list(dict.fromkeys(group_user_ids))
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
            print(
                f"[assigned] {group_name} {len(deduped_user_ids)} user(s) -> {group_id}"
            )

    print(
        "Summary: "
        f"created={created}, existing={existing}, assigned={assigned}, "
        f"failed={failed}, total={total_accounts}"
    )
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
