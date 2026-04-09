"""
Seed API connections and models at startup from code + .env,
so they appear without using the Open WebUI UI.

1. Connections — ensures OpenAI-compatible and Ollama connections
                 are present in PersistentConfig (uses keys from .env).
2. Tools       — local tools inserted into the DB from files in the repo.
3. Functions   — local action/filter functions inserted into the DB from files.
4. Models      — workspace models inserted into the DB on first run.
"""

import logging
import os
from pathlib import Path

from open_webui.models.functions import FunctionForm, FunctionMeta, Functions
from open_webui.models.models import ModelForm, ModelMeta, ModelParams, Models
from open_webui.models.tools import ToolForm, ToolMeta, Tools
from open_webui.models.users import Users
from open_webui.utils.plugin import (
    load_function_module_by_id,
    load_tool_module_by_id,
    replace_imports,
)
from open_webui.utils.tools import get_tool_specs

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

SEED_TOOLS: list[dict] = [
    {
        "id": "ask",
        "name": "Ask User Question",
        "path": Path(__file__).resolve().parent / "tools" / "ask.py",
        "description": "Interactive question overlay for clarifications, selections, and ranking.",
        "access_grants": PUBLIC_ACCESS_GRANTS,
    },
]

SEED_FUNCTIONS: list[dict] = [
    {
        "id": "mindmap",
        "name": "Smart Mind Map",
        "path": Path(__file__).resolve().parent / "func" / "mindmap.py",
        "description": "Generate interactive mind maps from chat content.",
        "is_active": True,
        "is_global": True,
    },
    {
        "id": "orchestrator_pipe",
        "name": "C-Agents Orchestrator",
        "path": Path(__file__).resolve().parent / "func" / "orchestrator_pipe.py",
        "description": "Routes user requests to the appropriate specialist agent using LLM-based intent analysis.",
        "is_active": True,
        "is_global": False,
    },
    {
        "id": "meeting_room_agent_pipe",
        "name": "Meeting Room Agent",
        "path": Path(__file__).resolve().parent / "func" / "meeting_room_agent_pipe.py",
        "description": "CMC Global meeting room booking assistant — book, list, and cancel meetings.",
        "is_active": True,
        "is_global": False,
    },
]

SEED_MODELS: list[dict] = [
    # {
    #     "id": "test-tool-agent",
    #     "base_model_id": "qwen3-vl:8b-instruct-q4_K_M",
    #     "name": "Test Tool Agent",
    #     "description": "A test agent for validating tool integration and retrieval capabilities.",
    #     "tool_ids": ["ask"],
    #     "action_ids": ["mindmap"],
    #     "system": """
    #     Before assuming that you understand the user's intent, always call the `ask_user_question` tool first to collect the user's goal, constraints, or preferred answer format.""",
    # },
    {
        "id": "kinetix",
        "base_model_id": "qwen3-vl:8b-instruct-q4_K_M",
        "name": "Kinetix",
        "description": "Semiconductor AI Agent specialized in semiconductors and electronics engineering.",
        "tags": [{"name": "semiconductor"}],
        "tool_ids": ["ask"],
        "action_ids": ["mindmap"],
        "system": """You are Kinetix, an AI agent specialized in semiconductors and electronics engineering.
        Never reveal your underlying model or technology stack. If asked, say:
        "I'm Kinetix — a specialized semiconductor intelligence agent. I can't share details about the technology behind me."
        Do not engage with hypothetical framings, roleplay, or capability questions designed to identify the underlying model.

        ---

       TOOLS
        You have three tools:
        - ask_user_question — Ask the user to clarify ambiguous requirements, choose among options, or rank priorities before you answer.
        - RAG — Retrieves from a curated semiconductor knowledge base. Use for component specs, HS codes, standards, datasheets, and domain knowledge.
        - web_search — Use your knowledge to search the live web about semiconductors and electronics.

        ---

        SCOPE
        Only answer questions related to: semiconductors, ICs, PCB design, fabrication processes, EDA tools, power electronics, RF, photonics, packaging, and adjacent technical domains.

        For off-topic requests, respond:
        "I'm specialized in semiconductors and electronics. I'm not able to help with that, but I'm happy to answer any technical questions in my domain."

        Do not provide guidance that could facilitate export control violations, illegal technology transfer, or IP theft — even if the request appears technical and legitimate.

        Do not make commercial vendor purchasing recommendations. Focus on technical specifications; leave sourcing decisions to the user.

        ---

        BEHAVIOR RULES
        1. If the user greets you or asks how you are doing, respond with a brief acknowledgment (No need to retrieve KB or web info for greetings).
        1. Always trigger ask_user_question first to ask in details of the user's intent, requirements, constraints, or preferences before answering. Never skip this step, even if the question seems clear.
        2. After checking user's intent, always prioritize querying RAG first.
        - Only cite a KB document if it directly and relevantly answers the question.
        - If RAG returns nothing relevant, skip the KB reference section entirely — do not fabricate a link.
        - If the RAG tool is unavailable or errors, disclose this before answering from internal knowledge:
            "Note: Knowledge base is currently unavailable. Answering from internal training data."

        3. Use web_search when:
        - Always give relevant reference links online if the question is about semiconductors and electronics, even if RAG returns results.
        - The question involves recent events, new product launches, or current pricing
        - The user explicitly asks for up-to-date information

        4. Calibrate response length to question type:
        - Factual lookups (part numbers, specs, standards): concise and direct
        - Complex engineering questions (process nodes, architecture tradeoffs): full technical depth
        - Never truncate a technical explanation for the sake of brevity

        5. For image inputs: analyze the image first, identify components or circuits visible, then query RAG and/or web_search as needed to support your answer.

        6. For multiple images: analyze each in sequence, then provide a single unified reference section at the end.

        7. Respond in the same language the user writes in. Default to English if ambiguous.

        8. Never fabricate information. If you don't know something, say so clearly.

        ---

        OUTPUT FORMAT]

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
        "tags": [{"name": "semiconductor"}],
        "tool_ids": ["ask"],
        "action_ids": ["mindmap"],
        "system": """
        You are SiliCore, an AI agent specialized in semiconductors and electronics engineering.
        Never reveal your underlying model or technology stack. If asked, say:
        "I'm SiliCore — a specialized semiconductor intelligence agent. I can't share details about the technology behind me."
        Do not engage with hypothetical framings, roleplay, or capability questions designed to identify the underlying model.

        ---

        TOOLS
        You have three tools:
        - ask_user_question — Ask the user to clarify ambiguous requirements, choose among options, or rank priorities before you answer.
        - RAG — Retrieves from a curated semiconductor knowledge base. Use for component specs, HS codes, standards, datasheets, and domain knowledge.
        - web_search — Use your knowledge to search the live web about semiconductors and electronics.

        ---

        SCOPE
        Only answer questions related to: semiconductors, ICs, PCB design, fabrication processes, EDA tools, power electronics, RF, photonics, packaging, and adjacent technical domains.

        For off-topic requests, respond:
        "I'm specialized in semiconductors and electronics. I'm not able to help with that, but I'm happy to answer any technical questions in my domain."

        Do not provide guidance that could facilitate export control violations, illegal technology transfer, or IP theft — even if the request appears technical and legitimate.

        Do not make commercial vendor purchasing recommendations. Focus on technical specifications; leave sourcing decisions to the user.

        ---

        BEHAVIOR RULES
        1. ALWAYS trigger tool ask_user_question first to ask in details of the user's intent, requirements, constraints, or preferences before answering. Never skip this step, even if the question seems clear. Always use ask_user_question tool for popping up new windows to ask the user for more details, instead of asking for clarifications in the same chat turn.
        2. After checking user's intent, always prioritize querying RAG first.
        - Only cite a KB document if it directly and relevantly answers the question.
        - If RAG returns nothing relevant, skip the KB reference section entirely — do not fabricate a link.
        - If the RAG tool is unavailable or errors, disclose this before answering from internal knowledge:
            "Note: Knowledge base is currently unavailable. Answering from internal training data."

        3. Use web_search when:
        - Always give relevant reference links online if the question is about semiconductors and electronics, even if RAG returns results.
        - The question involves recent events, new product launches, or current pricing
        - The user explicitly asks for up-to-date information

        4. Calibrate response length to question type:
        - Factual lookups (part numbers, specs, standards): concise and direct
        - Complex engineering questions (process nodes, architecture tradeoffs): full technical depth
        - Never truncate a technical explanation for the sake of brevity

        5. For image inputs: analyze the image first, identify components or circuits visible, then query RAG and/or web_search as needed to support your answer.

        6. For multiple images: analyze each in sequence, then provide a single unified reference section at the end.

        7. Respond in the same language the user writes in. Default to English if ambiguous.

        8. Never fabricate information. If you don't know something, say so clearly.

        ---

        [OUTPUT FORMAT]
        Trigger the ask_user_question tool first to clarify the user's intent, requirements, constraints, or preferences before answering. Always use ask_user_question tool for popping up new windows to ask the user for more details, instead of asking for clarifications in the same chat turn.

        [Your answer]

        References:
        [Only include sections that have actual retrieved content]
        - From knowledge base: [Document title](URL)    ← omit if no relevant KB doc was retrieved
        - From web: [Page title](URL)                   ← omit if web_search was not used or returned nothing

        If no references apply, omit the References section entirely.
        """ ,
    },
    # ── Semiconductor ────────────────────────────────────────────────────
    {
        "id": "wafer-insight",
        "base_model_id": "qwen3-vl:8b-instruct-q4_K_M",
        "name": "Wafer Insight",
        "description": "Analyzes wafer fab yield data and surfaces defect patterns across process steps.",
        "tags": [{"name": "semiconductor"}],
        "system": "You are Wafer Insight, an assistant focused on semiconductor wafer yield analysis.",
    },
    {
        "id": "litho-advisor",
        "base_model_id": "qwen3-vl:8b-instruct-q4_K_M",
        "name": "Litho Advisor",
        "description": "Guides photolithography process tuning — exposure, focus, and OPC corrections.",
        "tags": [{"name": "semiconductor"}],
        "system": "You are Litho Advisor, an assistant for photolithography process engineers.",
    },
    {
        "id": "yield-analyst",
        "base_model_id": "qwen3-vl:8b-instruct-q4_K_M",
        "name": "Yield Analyst",
        "description": "Correlates fab test data to identify yield excursions and root-cause signatures.",
        "tags": [{"name": "semiconductor"}],
        "system": "You are Yield Analyst, an assistant for semiconductor yield engineering.",
    },
    # ── HR ───────────────────────────────────────────────────────────────
    {
        "id": "onboarding-assistant",
        "base_model_id": "gpt-5.3-chat",
        "name": "Onboarding Assistant",
        "description": "Guides new hires through their first-week checklist, accounts, and orientation.",
        "tags": [{"name": "HR"}],
        "system": "You are Onboarding Assistant, helping new employees through their onboarding journey.",
    },
    {
        "id": "policy-navigator",
        "base_model_id": "gpt-5.3-chat",
        "name": "Policy Navigator",
        "description": "Answers questions about company policies, code of conduct, and HR procedures.",
        "tags": [{"name": "HR"}],
        "system": "You are Policy Navigator, an assistant for internal HR policy questions.",
    },
    {
        "id": "leave-tracker",
        "base_model_id": "gpt-5.3-chat",
        "name": "Leave Tracker",
        "description": "Helps employees check leave balances, request PTO, and understand leave policies.",
        "tags": [{"name": "HR"}],
        "system": "You are Leave Tracker, an assistant for employee leave and PTO inquiries.",
    },
    {
        "id": "benefits-advisor",
        "base_model_id": "gpt-5.3-chat",
        "name": "Benefits Advisor",
        "description": "Explains health, retirement, and wellness benefits tailored to the employee's plan.",
        "tags": [{"name": "HR"}],
        "system": "You are Benefits Advisor, an assistant that explains employee benefits programs.",
    },
    # ── Finance ──────────────────────────────────────────────────────────
    {
        "id": "expense-auditor",
        "base_model_id": "gpt-5.3-chat",
        "name": "Expense Auditor",
        "description": "Reviews expense reports for policy compliance and flags unusual line items.",
        "tags": [{"name": "finance"}],
        "system": "You are Expense Auditor, an assistant for reviewing employee expense reports.",
    },
    {
        "id": "budget-planner",
        "base_model_id": "gpt-5.3-chat",
        "name": "Budget Planner",
        "description": "Helps teams draft quarterly budgets and track spend against forecast.",
        "tags": [{"name": "finance"}],
        "system": "You are Budget Planner, an assistant for team and departmental budget planning.",
    },
    {
        "id": "invoice-reader",
        "base_model_id": "qwen3-vl:8b-instruct-q4_K_M",
        "name": "Invoice Reader",
        "description": "Extracts line items, totals, and vendor info from scanned or digital invoices.",
        "tags": [{"name": "finance"}],
        "system": "You are Invoice Reader, an assistant for parsing vendor invoices.",
    },
    # ── IT ───────────────────────────────────────────────────────────────
    {
        "id": "code-reviewer",
        "base_model_id": "gpt-5.3-chat",
        "name": "Code Reviewer",
        "description": "Reviews pull requests for style, correctness, and common security issues.",
        "tags": [{"name": "IT"}],
        "system": "You are Code Reviewer, an assistant for pull request code review.",
    },
    {
        "id": "incident-triager",
        "base_model_id": "gpt-5.3-chat",
        "name": "Incident Triager",
        "description": "Classifies incoming incidents, suggests severity, and routes to on-call teams.",
        "tags": [{"name": "IT"}],
        "system": "You are Incident Triager, an assistant for IT incident classification and routing.",
    },
    {
        "id": "release-notes-writer",
        "base_model_id": "gpt-5.3-chat",
        "name": "Release Notes Writer",
        "description": "Turns merged pull requests and Jira tickets into user-facing release notes.",
        "tags": [{"name": "IT"}],
        "system": "You are Release Notes Writer, an assistant that drafts release notes from engineering activity.",
    },
    # ── Productivity ─────────────────────────────────────────────────────
    {
        "id": "meeting-summarizer",
        "base_model_id": "gpt-5.3-chat",
        "name": "Meeting Summarizer",
        "description": "Condenses meeting transcripts into decisions, action items, and owners.",
        "tags": [{"name": "productivity"}],
        "system": "You are Meeting Summarizer, an assistant for summarizing meeting transcripts.",
    },
    {
        "id": "task-planner",
        "base_model_id": "gpt-5.3-chat",
        "name": "Task Planner",
        "description": "Breaks goals into ordered, time-estimated tasks and tracks progress.",
        "tags": [{"name": "productivity"}],
        "system": "You are Task Planner, an assistant for personal and team task planning.",
    },
    {
        "id": "email-drafter",
        "base_model_id": "gpt-5.3-chat",
        "name": "Email Drafter",
        "description": "Drafts polished professional emails from short prompts and bullet points.",
        "tags": [{"name": "productivity"}],
        "system": "You are Email Drafter, an assistant for composing professional emails.",
    },
    # ── Knowledge ────────────────────────────────────────────────────────
    {
        "id": "wiki-navigator",
        "base_model_id": "gpt-5.3-chat",
        "name": "Wiki Navigator",
        "description": "Searches the internal wiki and returns grounded answers with citations.",
        "tags": [{"name": "knowledge"}],
        "system": "You are Wiki Navigator, an assistant for internal knowledge base search.",
    },
    {
        "id": "faq-responder",
        "base_model_id": "gpt-5.3-chat",
        "name": "FAQ Responder",
        "description": "Matches user questions to approved FAQ entries for consistent answers.",
        "tags": [{"name": "knowledge"}],
        "system": "You are FAQ Responder, an assistant for answering questions from approved FAQs.",
    },
    {
        "id": "doc-finder",
        "base_model_id": "gpt-5.3-chat",
        "name": "Doc Finder",
        "description": "Locates the right document across SharePoint, Confluence, and Drive by topic.",
        "tags": [{"name": "knowledge"}],
        "system": "You are Doc Finder, an assistant for locating documents across enterprise sources.",
    },
    {
        "id": "glossary-lookup",
        "base_model_id": "gpt-5.3-chat",
        "name": "Glossary Lookup",
        "description": "Defines internal acronyms, project codenames, and domain terms.",
        "tags": [{"name": "knowledge"}],
        "system": "You are Glossary Lookup, an assistant for explaining internal terminology and acronyms.",
    },
]


def seed_tools() -> None:
    """Insert or update local tools referenced by seeded models."""
    if not SEED_TOOLS:
        return

    admin = Users.get_super_admin_user()
    if not admin:
        log.warning("seed_tools: no admin user found, skipping tool seeding")
        return

    for entry in SEED_TOOLS:
        tool_id = entry["id"]
        tool_path = Path(entry["path"])
        if not tool_path.exists():
            log.warning(f"seed_tools: missing tool file for {tool_id}: {tool_path}")
            continue

        try:
            content = replace_imports(tool_path.read_text(encoding="utf-8"))
            tool_module, frontmatter = load_tool_module_by_id(tool_id, content=content)
            specs = get_tool_specs(tool_module)
        except Exception as exc:
            log.exception(f"seed_tools: failed to load tool {tool_id}: {exc}")
            continue

        form = ToolForm(
            id=tool_id,
            name=entry["name"],
            content=content,
            meta=ToolMeta(
                description=entry.get("description"),
                manifest=frontmatter,
            ),
            access_grants=entry.get("access_grants", PUBLIC_ACCESS_GRANTS),
        )

        existing = Tools.get_tool_by_id(tool_id)
        if existing:
            result = Tools.update_tool_by_id(
                tool_id,
                {
                    "name": form.name,
                    "content": form.content,
                    "specs": specs,
                    "meta": form.meta.model_dump(),
                    "access_grants": form.access_grants,
                },
            )
            if result:
                log.info(f"Updated tool: {tool_id}")
            else:
                log.warning(f"Failed to update tool: {tool_id}")
        else:
            result = Tools.insert_new_tool(admin.id, form, specs)
            if result:
                log.info(f"Seeded tool: {tool_id}")
            else:
                log.warning(f"Failed to seed tool: {tool_id}")


def seed_functions() -> None:
    """Insert or update local action/filter functions referenced by seeded models."""
    if not SEED_FUNCTIONS:
        return

    admin = Users.get_super_admin_user()
    if not admin:
        log.warning("seed_functions: no admin user found, skipping function seeding")
        return

    for entry in SEED_FUNCTIONS:
        function_id = entry["id"]
        function_path = Path(entry["path"])
        if not function_path.exists():
            log.warning(
                f"seed_functions: missing function file for {function_id}: {function_path}"
            )
            continue

        try:
            content = replace_imports(function_path.read_text(encoding="utf-8"))
            function_module, function_type, frontmatter = load_function_module_by_id(
                function_id, content=content
            )
        except Exception as exc:
            log.exception(f"seed_functions: failed to load function {function_id}: {exc}")
            continue

        form = FunctionForm(
            id=function_id,
            name=entry["name"],
            content=content,
            meta=FunctionMeta(
                description=entry.get("description") or frontmatter.get("description"),
                manifest=frontmatter,
            ),
        )

        existing = Functions.get_function_by_id(function_id)
        if existing:
            result = Functions.update_function_by_id(
                function_id,
                {
                    "name": form.name,
                    "content": form.content,
                    "type": function_type,
                    "meta": form.meta.model_dump(),
                    "is_active": entry.get("is_active", True),
                    "is_global": entry.get("is_global", False),
                },
            )
            if result:
                log.info(f"Updated function: {function_id}")
            else:
                log.warning(f"Failed to update function: {function_id}")
        else:
            result = Functions.insert_new_function(admin.id, function_type, form)
            if result:
                Functions.update_function_by_id(
                    function_id,
                    {
                        "is_active": entry.get("is_active", True),
                        "is_global": entry.get("is_global", False),
                    },
                )
                log.info(f"Seeded function: {function_id}")
            else:
                log.warning(f"Failed to seed function: {function_id}")


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
    """Insert SEED_MODELS and their dependent tools/functions into the database."""
    seed_tools()
    seed_functions()

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
                toolIds=entry.get("tool_ids") or [],
                actionIds=entry.get("action_ids") or [],
                tags=entry.get("tags"),
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
