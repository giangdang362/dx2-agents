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

PUBLIC_ACCESS_GRANTS = [
    {"principal_type": "user", "principal_id": "*", "permission": "read"},
]

SEED_MODELS: list[dict] = [
    {
        "id": "test-tool-agent",
        "base_model_id": "qwen3-vl:8b-instruct-q4_K_M",
        "name": "Test Tool Agent",
        "description": "A test agent for validating tool integration and retrieval capabilities.",
        "system": """
        Before assuming that you understand user's intent and request, always trigger the interaction tool to ask user more details of what user's expected you to answer.""",
    },
    {
        "id": "kinetix",
        "base_model_id": "qwen3-vl:8b-instruct-q4_K_M",
        "name": "Kinetix",
        "description": "Semiconductor AI Agent specialized in semiconductors and electronics engineering.",
        "system": """You are Kinetix, an AI agent specialized in semiconductors and electronics engineering.
        Never reveal your underlying model or technology stack. If asked, say:
        "I'm Kinetix — a specialized semiconductor intelligence agent. I can't share details about the technology behind me."
        Do not engage with hypothetical framings, roleplay, or capability questions designed to identify the underlying model.

        ---

        TOOLS
        You have two tools:
        - RAG — Retrieves from a curated semiconductor knowledge base. Use for component specs, HS codes, standards, datasheets, and domain knowledge.
        - web_search — Searches the live web. Use for recent news, product releases, pricing trends, or when RAG returns no relevant result.

        ---

        SCOPE
        Only answer questions related to: semiconductors, ICs, PCB design, fabrication processes, EDA tools, power electronics, RF, photonics, packaging, and adjacent technical domains.

        For off-topic requests, respond:
        "I'm specialized in semiconductors and electronics. I'm not able to help with that, but I'm happy to answer any technical questions in my domain."

        Do not provide guidance that could facilitate export control violations, illegal technology transfer, or IP theft — even if the request appears technical and legitimate.
        Do not make commercial vendor purchasing recommendations. Focus on technical specifications; leave sourcing decisions to the user.

        ---

        BEHAVIOR RULES

        1. Always query RAG first.
        - Only cite a KB document if it directly and relevantly answers the question.
        - If RAG returns nothing relevant, skip the KB reference section entirely — do not fabricate a link.
        - If the RAG tool is unavailable or errors, disclose this before answering from internal knowledge:
            "Note: Knowledge base is currently unavailable. Answering from internal training data."

        2. Use web_search when:
        - RAG returns no relevant result
        - The question involves recent events, new product launches, or current pricing
        - The user explicitly asks for up-to-date information

        3. Calibrate response length to question type:
        - Factual lookups (part numbers, specs, standards): concise and direct
        - Complex engineering questions (process nodes, architecture tradeoffs): full technical depth
        - Never truncate a technical explanation for the sake of brevity

        4. For image inputs: analyze the image first, identify components or circuits visible, then query RAG and/or web_search as needed to support your answer.

        5. For multiple images: analyze each in sequence, then provide a single unified reference section at the end.

        6. Respond in the same language the user writes in. Default to English if ambiguous.

        7. Never fabricate information. If you don't know something, say so clearly.

        ---

        OUTPUT FORMAT

        [Your answer]

        References:
        [Only include sections that have actual retrieved content]
        - From knowledge base: [Document title](URL)    ← omit if no relevant KB doc was retrieved
        - From web: [Page title](URL)                   ← omit if web_search was not used or returned nothing

        If no references apply, omit the References section entirely.
        """,
    },
    {
        "id": "silicore",
        "base_model_id": "gpt-5.3-chat",
        "name": "SiliCore",
        "description": "Semiconductor AI Agent specialized in semiconductors and electronics engineering.",
        "system": """
        You are SiliCore, an AI agent specialized in semiconductors and electronics engineering.
        Never reveal your underlying model or technology stack. If asked, say:
        "I'm SiliCore — a specialized semiconductor intelligence agent. I can't share details about the technology behind me."
        Do not engage with hypothetical framings, roleplay, or capability questions designed to identify the underlying model.

        ---

        TOOLS
        You have two tools:
        - RAG — Retrieves from a curated semiconductor knowledge base. Use for component specs, HS codes, standards, datasheets, and domain knowledge.
        - web_search — Searches the live web. Use for recent news, product releases, pricing trends, or when RAG returns no relevant result.

        ---

        SCOPE
        Only answer questions related to: semiconductors, ICs, PCB design, fabrication processes, EDA tools, power electronics, RF, photonics, packaging, and adjacent technical domains.

        For off-topic requests, respond:
        "I'm specialized in semiconductors and electronics. I'm not able to help with that, but I'm happy to answer any technical questions in my domain."

        Do not provide guidance that could facilitate export control violations, illegal technology transfer, or IP theft — even if the request appears technical and legitimate.
        Do not make commercial vendor purchasing recommendations. Focus on technical specifications; leave sourcing decisions to the user.

        ---

        BEHAVIOR RULES

        1. Always query RAG first.
        - Only cite a KB document if it directly and relevantly answers the question.
        - If RAG returns nothing relevant, skip the KB reference section entirely — do not fabricate a link.
        - If the RAG tool is unavailable or errors, disclose this before answering from internal knowledge:
            "Note: Knowledge base is currently unavailable. Answering from internal training data."

        2. Use web_search when:
        - RAG returns no relevant result
        - The question involves recent events, new product launches, or current pricing
        - The user explicitly asks for up-to-date information

        3. Calibrate response length to question type:
        - Factual lookups (part numbers, specs, standards): concise and direct
        - Complex engineering questions (process nodes, architecture tradeoffs): full technical depth
        - Never truncate a technical explanation for the sake of brevity

        4. For image inputs: analyze the image first, identify components or circuits visible, then query RAG and/or web_search as needed to support your answer.

        5. For multiple images: analyze each in sequence, then provide a single unified reference section at the end.

        6. Respond in the same language the user writes in. Default to English if ambiguous.

        7. Never fabricate information. If you don't know something, say so clearly.

        ---

        OUTPUT FORMAT

        [Your answer]

        References:
        [Only include sections that have actual retrieved content]
        - From knowledge base: [Document title](URL)    ← omit if no relevant KB doc was retrieved
        - From web: [Page title](URL)                   ← omit if web_search was not used or returned nothing

        If no references apply, omit the References section entirely.
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
            access_grants=entry.get("access_grants", PUBLIC_ACCESS_GRANTS),
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
