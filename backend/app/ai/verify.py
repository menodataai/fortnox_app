"""The verifier agent behind `verify_draft` (F9 change 2).

A second, independent agent whose only job is to try to refute the numeric
claims in a draft answer before the main agent finalizes it. It re-derives
every load-bearing figure from the mirror (run_python / query_ledger /
calculate) rather than trusting the draft's own arithmetic, and checks
internal coherence and bracket/threshold logic. It cannot search the web.

Tool registration for this agent happens in tools.py (it shares the same
underlying run_python / query_ledger / calculate functions as the main agent),
which keeps all tool wiring in one place and avoids an import cycle.
"""

from pydantic import BaseModel
from pydantic_ai import Agent
from pydantic_ai.models.openrouter import OpenRouterModel
from pydantic_ai.providers.openrouter import OpenRouterProvider
from pydantic_ai.usage import UsageLimits

from ..config import settings
from .agent import MODEL_SETTINGS, AssistantDeps

# The verifier re-derives each headline number with its own tool calls, so it
# needs several round-trips (a request ≈ one tool step + the final structured
# output). 6 was too tight for a multi-number answer like Q4 and tripped the
# limit mid-verification; 14 gives room without letting it run away. If it
# still exhausts this, verify_draft degrades gracefully rather than aborting.
VERIFIER_LIMITS = UsageLimits(request_limit=14, total_tokens_limit=250_000)

VERIFIER_PROMPT = """\
You are a skeptical financial auditor. You receive a user question and a DRAFT
answer containing numeric claims. Your only job is to try to refute it. For
every number that carries the conclusion: re-derive it independently with
run_python / query_ledger / calculate — do not trust the draft's own
arithmetic. Check that every figure appearing in more than one place is
consistent, and that stated totals equal the sum of their stated parts. Check
bracket/threshold logic explicitly: a marginal rate applies only to the slice
of income above the threshold, never to a whole amount unless the whole amount
is above it. Mark each claim confirmed / wrong / incoherent / unverifiable,
with the re-derived value. You cannot search the web: if a claim rests on an
external parameter, mark it unverifiable and say what source the draft should
cite. Be terse.
"""


class Finding(BaseModel):
    claim: str      # the numeric/logical claim checked
    verdict: str    # "confirmed" | "wrong" | "incoherent" | "unverifiable"
    detail: str     # what the re-derivation showed, with numbers


class VerificationReport(BaseModel):
    findings: list[Finding]
    ok: bool        # True only if no "wrong"/"incoherent" findings


def build_model_for_verifier() -> OpenRouterModel:
    """Same as agent.build_model() but honoring AI_VERIFIER_MODEL, so the
    verify pass can run on a cheaper/different model than the main answer."""
    return OpenRouterModel(
        settings.ai_verifier_model or settings.ai_model,
        provider=OpenRouterProvider(api_key=settings.openrouter_api_key),
    )


verifier: Agent[AssistantDeps, VerificationReport] = Agent(
    deps_type=AssistantDeps,
    output_type=VerificationReport,
    instructions=VERIFIER_PROMPT,
    model_settings=MODEL_SETTINGS,
    retries=1,
    name="fortnox-insights-verifier",
)
