"""The F8 assistant: Pydantic AI Agent over the local mirror.

The model never holds Fortnox credentials, never sees the Fortnox client and
only touches a read-only SQLite handle — write-safety is structural, not
behavioral, on every model vendor. The single deliberate exception is the
`trigger_sync` tool (F9 change 4): it can kick the existing local-mirror sync,
takes no parameters and returns only a status dict — no Fortnox payloads ever
reach the model."""

from dataclasses import dataclass, field

from pydantic_ai import Agent
from pydantic_ai.models.openrouter import OpenRouterModel, OpenRouterModelSettings
from pydantic_ai.providers.openrouter import OpenRouterProvider
from pydantic_ai.usage import UsageLimits

from ..config import settings
from .prompt import build_system_prompt

# Headroom for the F9 verify pass (change 2), not an invitation: the benchmark
# run used at most 6 requests. verify_draft spends from the verifier's own
# VERIFIER_LIMITS, so this mainly covers the extra main-agent round-trip.
USAGE_LIMITS = UsageLimits(request_limit=20, total_tokens_limit=600_000)


@dataclass
class AssistantDeps:
    """Injected into every tool via RunContext — no globals, fakeable in tests.

    Note: deliberately NO shared DB connection here. Tools run on threadpool
    threads (concurrently for parallel tool calls), and sqlite3 connections
    must not cross threads — query_ledger opens its own per call."""

    # domains surfaced by web_search this run; fetch_page also accepts these
    seen_domains: set[str] = field(default_factory=set)


def build_model() -> OpenRouterModel:
    return OpenRouterModel(
        settings.ai_model,
        provider=OpenRouterProvider(api_key=settings.openrouter_api_key),
    )


MODEL_SETTINGS = OpenRouterModelSettings(
    openrouter_reasoning={"enabled": True},
    openrouter_usage={"include": True},
    # best-effort prompt caching on providers that support it (Anthropic/Gemini).
    # Same TTL on both: Anthropic rejects a longer TTL after a shorter one,
    # and tool definitions are processed before system instructions.
    openrouter_cache_instructions="5m",
    openrouter_cache_tool_definitions="5m",
)

# No model here: it's built lazily per request (build_model), so the backend
# starts fine without an OpenRouter key and tests can inject TestModel.
agent: Agent[AssistantDeps, str] = Agent(
    deps_type=AssistantDeps,
    instructions=build_system_prompt(),
    model_settings=MODEL_SETTINGS,
    retries=2,
    name="fortnox-insights-assistant",
)

# Tool registration happens on import (they attach to `agent`).
from . import tools  # noqa: E402,F401  (import for side effect)
