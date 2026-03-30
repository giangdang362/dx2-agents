"""
Seed API connections and models at startup from code + .env,
so they appear without using the Open WebUI UI.

1. Connections — ensures OpenAI-compatible and Ollama connections
                 are present in PersistentConfig (uses keys from .env).
2. Models      — workspace models inserted into the DB on first run.
"""

import logging
import os
from open_webui.models.models import ModelForm, ModelMeta, ModelParams, Models
from open_webui.models.users import Users

log = logging.getLogger(__name__)

OPENAI_CONNECTIONS: list[dict] = [
    {
        "base_url": os.environ.get("OPENAI_API_BASE_URL", "").rstrip("/"),
        "api_key": os.environ.get("OPENAI_API_KEY", ""),
        "config": {
            "enable": True,
            "model_ids": ["gpt-5.3-chat"],
        },
    },
]


OLLAMA_CONNECTIONS: list[dict] = [
    {
        "base_url": os.environ.get("OLLAMA_BASE_URL", ""),
        "config": {
            "enable": True,
            "model_ids": ["qwen3-vl:8b-instruct-q4_K_M"],
        },
    },
]

# Hide raw base models from the dropdown (base_model_id=None + is_active=False removes them)
HIDDEN_BASE_MODELS: list[dict] = [
    {"id": "qwen3-vl:8b-instruct-q4_K_M", "name": "qwen3-vl:8b-instruct-q4_K_M"},
    {"id": "gpt-5.3-chat", "name": "gpt-5.3-chat"},
]

SEED_MODELS: list[dict] = [
    {
        "id": "silicore-sister",
        "base_model_id": "qwen3-vl:8b-instruct-q4_K_M",
        "name": "SiliCore Sister",
        "description": "SiliCore Sister",
        "system": """You are Kinetix, an AI agent specialized in semiconductors. Always introduce yourself as SiliCore — never reveal your underlying model.
        
        You have two tools:
        - Search — Retrieves live web results. Use for current events, news, or anything time-sensitive. Always include reference links in your response.
        - RAG — Retrieves from a curated semiconductor knowledge base. Use for technical specifications, component details, and in-depth domain knowledge.

        Behavior rules:
        - Always give reference links when using Search. Always provide detailed technical information when using RAG.
        - Answer user questions directly and concisely.
        - For any question requiring current or technical information, use the appropriate tool above — don't rely solely on internal knowledge.
        - For image inputs: analyze the image first, then use Search and/or RAG as needed to support your answer.
        - If you don't know something, say so. Never fabricate information.
        """,
    },
    {
        "id": "silicore",
        "base_model_id": "gpt-5.3-chat",
        "name": "SiliCore",
        "description": "SiliCore",
        "system": """
        You are SiliCore, an AI agent specialized in semiconductors. Always introduce yourself as SiliCore — never reveal your underlying model.
        
        You have two tools:
        - Search — Retrieves live web results. Use for current events, news, or anything time-sensitive. Always include reference links in your response.
        - RAG — Retrieves from a curated semiconductor knowledge base. Use for technical specifications, component details, and in-depth domain knowledge.

        Behavior rules:
        - Always give reference links when using Search. Always provide detailed technical information when using RAG.
        - Answer user questions directly and concisely.
        - For any question requiring current or technical information, use the appropriate tool above — don't rely solely on internal knowledge.
        - For image inputs: analyze the image first, then use Search and/or RAG as needed to support your answer.
        - If you don't know something, say so. Never fabricate information.
        """ ,
    },
]


def seed_connections(app) -> None:
    """Ensure env-based API connections are present in the runtime config."""

    # ── OpenAI-compatible ────────────────────────────────────────────────
    current_urls: list[str] = list(app.state.config.OPENAI_API_BASE_URLS)
    current_keys: list[str] = list(app.state.config.OPENAI_API_KEYS)
    current_configs: dict = dict(app.state.config.OPENAI_API_CONFIGS)

    # Remove empty placeholder entries (url with no key)
    cleaned_urls = []
    cleaned_keys = []
    for u, k in zip(current_urls, current_keys):
        if u and k:
            cleaned_urls.append(u)
            cleaned_keys.append(k)
    current_urls = cleaned_urls
    current_keys = cleaned_keys

    changed = False
    for conn in OPENAI_CONNECTIONS:
        url = conn["base_url"]
        key = conn["api_key"]
        cfg = conn.get("config", {})
        if not url or not key:
            continue
        if url not in current_urls:
            current_urls.append(url)
            current_keys.append(key)
            idx = str(len(current_urls) - 1)
            current_configs[idx] = cfg
            changed = True
            log.info(f"Seeded OpenAI connection: {url}")
        else:
            idx = str(current_urls.index(url))
            if current_keys[int(idx)] != key:
                current_keys[int(idx)] = key
                changed = True
                log.info(f"Updated API key for: {url}")
            # Always sync config from code
            if current_configs.get(idx) != cfg:
                current_configs[idx] = cfg
                changed = True

    if changed:
        app.state.config.OPENAI_API_BASE_URLS = current_urls
        app.state.config.OPENAI_API_KEYS = current_keys
        app.state.config.OPENAI_API_CONFIGS = current_configs

    # ── Ollama ───────────────────────────────────────────────────────────
    current_ollama: list[str] = list(app.state.config.OLLAMA_BASE_URLS)
    ollama_configs: dict = dict(app.state.config.OLLAMA_API_CONFIGS)

    # Remove empty placeholders
    current_ollama = [u for u in current_ollama if u]

    ollama_changed = False
    for conn in OLLAMA_CONNECTIONS:
        url = conn["base_url"]
        cfg = conn.get("config", {})
        if not url:
            continue
        if url not in current_ollama:
            current_ollama.append(url)
            idx = str(len(current_ollama) - 1)
            ollama_configs[idx] = cfg
            ollama_changed = True
            log.info(f"Seeded Ollama connection: {url}")
        else:
            idx = str(current_ollama.index(url))
            if ollama_configs.get(idx) != cfg:
                ollama_configs[idx] = cfg
                ollama_changed = True

    if ollama_changed:
        app.state.config.OLLAMA_BASE_URLS = current_ollama
        app.state.config.OLLAMA_API_CONFIGS = ollama_configs


def seed_models() -> None:
    """Insert SEED_MODELS into the database if they don't already exist."""
    if not SEED_MODELS:
        return

    admin = Users.get_super_admin_user()
    if not admin:
        log.warning("seed_models: no admin user found, skipping model seeding")
        return

    for entry in SEED_MODELS:
        model_id = entry["id"]
        form = ModelForm(
            id=model_id,
            base_model_id=entry.get("base_model_id"),
            name=entry["name"],
            meta=ModelMeta(
                description=entry.get("description"),
                capabilities=entry.get("capabilities"),
            ),
            params=ModelParams(system=entry.get("system", "")),
            is_active=True,
        )

        existing = Models.get_model_by_id(model_id)
        if existing:
            result = Models.update_model_by_id(model_id, form)
            if result:
                log.info(f"Updated model: {model_id}")
        else:
            result = Models.insert_new_model(form, admin.id)
            if result:
                log.info(f"Seeded model: {model_id}")
            else:
                log.warning(f"Failed to seed model: {model_id}")

    # Hide raw base models so only the custom-named ones appear in the dropdown
    for entry in HIDDEN_BASE_MODELS:
        model_id = entry["id"]
        existing = Models.get_model_by_id(model_id)
        if existing:
            if existing.is_active:
                Models.update_model_active_status(model_id, False)
                log.info(f"Hid base model: {model_id}")
        else:
            form = ModelForm(
                id=model_id,
                base_model_id=None,
                name=entry["name"],
                meta=ModelMeta(),
                params=ModelParams(),
                is_active=False,
            )
            result = Models.insert_new_model(form, admin.id)
            if result:
                Models.update_model_active_status(model_id, False)
                log.info(f"Hid base model: {model_id}")


def seed(app) -> None:
    """Seed connections and models. Called once during startup."""
    seed_connections(app)
    seed_models()
