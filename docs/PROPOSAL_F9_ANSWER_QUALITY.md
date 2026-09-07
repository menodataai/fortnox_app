# Proposal: F8 answer-quality upgrades (F9 groundwork)

> **Implementation status (2026-07-31): IMPLEMENTED.** All five changes plus
> the prompt upgrades shipped. `read_reference` reads BOTH `context/` (the
> agent's grounding knowledge — company + Swedish-tax reference) and `docs/`
> (design docs + the case-study audits), since the knowledge docs were moved
> to `context/` after this proposal was written — see Change 5 / Config below.
> Acceptance is measured by `backend/evals/f9_answer_quality_evals.py` (local,
> gitignored — it encodes the case-study questions): the four questions in one
> session, scored against the criteria at the bottom and the 10-trait rubric;
> run it with a synced mirror + keys. Offline coverage:
> `backend/tests/test_sandbox.py`, `test_reference.py`, and the extended
> `test_agent_flow.py` (all zero-token).

*Implementation proposal, 2026-07-31. Derived from the benchmark comparison in
`CASE_STUDY_COST_ANALYSIS_TRACE.md`, where the in-app assistant was run on the
same four questions as a reference agent (Claude Code) and scored against a
10-trait rubric. This document specifies the changes an implementing agent
should make. Read the case study first — every change below traces to a
confirmed defect or root cause there (the recorded chat session in
`chat_messages` holds the full evidence).*

## Decision context (why this shape)

Considered and **rejected**: migrating the assistant to the Claude Agent SDK.
Reasons: it locks the app to Anthropic models (we keep OpenRouter + `AI_MODEL`
switching and the per-model eval workflow), its built-in tools are
filesystem/bash-shaped (wrong for a web backend over financial data), and it
would replace working product plumbing (SSE protocol, `chat_messages`
persistence, TestModel offline tests). None of the observed failures was a
framework limitation — they were missing tools, missing context, and missing
prompt rules. So: **extend the existing Pydantic AI layer.**

Constraints that must survive every change:

- OpenRouter + Pydantic AI stay; no Anthropic-SDK or Node dependencies.
- The model never sees Fortnox credentials; ledger access stays read-only
  by construction (one narrow, explicit exception in change 4).
- The SSE protocol in `ai/router.py` is unchanged (the frontend depends on it).
- Offline tests keep running with `TestModel` (zero tokens).

## Root cause → change map

| # | Root cause (from case study) | Change |
|---|---|---|
| 1 | No code execution — expression-only `calculate` forces chained calls, payslip interpolation, no pivots | **1. `run_python` sandbox tool** |
| 2 | No coherence/verify pass — two confirmed numeric defects shipped | **2. `verify_draft` tool + verifier agent** |
| 3 | Research depth not enforced — 2026 reforms missed with budget to spare | **3a. prompt: parameter enumeration rule** |
| 4 | Evidence-last habit — hedged on VAT where one voucher settles it | **3b. prompt: evidence-before-hedging rule** |
| 5 | No sync capability — "pull latest data" silently unfulfillable | **4. `trigger_sync` tool** |
| 6 | No access to `docs/` case studies — known findings (a verified benefit over-report) never surfaced | **5. `read_reference` tool** |
| 7 | Clarify-vs-assume tuning — Q3 stalled on a clarifying question | **3c. prompt: assume-and-deliver rule (amends Hard rule 1)** |

Implement in the order 1 → 3 → 5 → 4 → 2 (2 depends on 1; 3 and 5 are cheap
and independent).

---

## Change 1 — `run_python` sandbox tool

**Goal.** Let the agent run short Python scripts against a read-only copy of
the mirror: pivot tables (month × category), statutory tax functions,
multi-step arithmetic — replacing chains of `calculate` calls and
"interpolate from payslips" shortcuts.

### Files

- New: `backend/app/ai/sandbox.py` (execution machinery)
- Edit: `backend/app/ai/tools.py` (registration)
- Edit: `backend/app/ai/prompt.py` (TOOL_GUIDE addition, see change 3)
- New tests: `backend/tests/test_sandbox.py`

### Design

Execute the model-supplied script in a **subprocess** (never in-process —
`exec()` in the backend process is out of the question):

```
subprocess.run([sys.executable, "-I", "-E", wrapper_path, script_via_stdin], ...)
```

- `-I` (isolated: no site-packages, no user site, no cwd on path) + `-E`
  (ignore PYTHONPATH etc.).
- **Wrapper script** (a small fixed file, part of the repo, e.g.
  `sandbox_runner.py`): runs first inside the subprocess and, before
  exec'ing the user code:
  1. **Disables networking**: replaces `socket.socket`, `socket.create_connection`
     and `socket.getaddrinfo` with functions that raise `RuntimeError("network
     disabled in sandbox")`. (Best-effort but effective: user code runs after
     the patch and `-I` prevents preloading tricks.)
  2. **Opens the mirror read-only**: `sqlite3.connect("file:<path>?mode=ro",
     uri=True)`; injects into the script's globals as `db` plus a helper
     `q(sql, params=()) -> list[tuple]` and `qd(sql, params=()) -> list[dict]`.
     The path arrives via a command-line arg from the parent, not an env var
     the model controls.
  3. Imports and injects `decimal.Decimal` as `D` for exact arithmetic.
  4. `exec()`s the user script read from stdin in a fresh globals dict.
- **Resource limits** via `preexec_fn` using `resource.setrlimit`:
  `RLIMIT_CPU = 10s`. (Skip `RLIMIT_AS` — unreliable on macOS; the wall-clock
  timeout is the real guard.) Parent-side `timeout=15` seconds; on expiry kill
  and report.
- **Environment**: pass a minimal env (`{"PATH": ""}` essentially); do not
  inherit the backend's env (it may hold API keys).
- **Output**: capture stdout and stderr, cap each at ~20,000 chars with an
  explicit `"...[truncated]"` marker. Return
  `{"stdout": ..., "stderr": ..., "exit_code": ...}` to the model as the tool
  result — do **not** raise `ModelRetry` on nonzero exit; the model needs the
  traceback to fix its script (Pydantic AI would otherwise burn its 2 retries).

### Registration (tools.py)

```python
@agent.tool_plain
def run_python(script: str) -> dict:
    """Run a short Python script in a sandbox with read-only access to the
    mirror database. Use for anything beyond one-line arithmetic: pivot
    tables (e.g. month x category cost matrices), tax computations with
    brackets, iterative reconciliation. Available in the script's namespace:
      q(sql, params=()) -> list of tuples (read-only SELECT on the mirror)
      qd(sql, params=()) -> list of dicts
      db -> the sqlite3 connection; D -> decimal.Decimal
    Standard library only (json, statistics, datetime, collections, math...).
    No network, no filesystem writes, 10s CPU limit. print() your results —
    stdout is returned. On errors the traceback comes back: fix and retry."""
    return sandbox.run(script)
```

`calculate` stays for one-liners (cheaper, exact-decimal semantics).

### Security notes for the implementer

- The subprocess gets the same OS user; the meaningful guarantees are:
  read-only DB URI, no inherited secrets in env, no network, CPU/wall
  timeouts, and output caps. Filesystem writes by the script are not blocked
  by the OS — mitigate by running with `cwd` set to a fresh temp dir
  (`tempfile.mkdtemp`) that is deleted afterwards, and state clearly in the
  system prompt/docstring that writes are not persisted.
- SQLite `mode=ro` on the URI makes writes fail at the driver level even
  though the file is user-writable — add a test asserting `INSERT` raises.

### Tests (`test_sandbox.py`, offline)

1. Happy path: script prints a computed dict → appears in `stdout`.
2. `q()` works against a temp mirror db fixture; `INSERT`/`UPDATE` via `db`
   raises `sqlite3.OperationalError`.
3. Network blocked: `urllib.request.urlopen(...)` in a script → error in
   `stderr` mentioning the sandbox.
4. Infinite loop → killed by timeout, result says so, call returns < 20s.
5. Output cap: script printing 1 MB → truncated marker present.
6. Env leak: script printing `os.environ` shows no `OPENROUTER_API_KEY` /
   `FORTNOX_*` values.

---

## Change 2 — verification pass (`verify_draft` tool)

**Goal.** Catch exactly the two defect classes that shipped in the benchmark:
(a) a quantitatively wrong claim (a benefit's state-tax effect overstated
several-fold by taxing the full benefit at the marginal rate when only a small
slice of income sat above the brytpunkt) and (b) internal incoherence (the
company-side saving stated with two different totals in different sections).

### Approach: self-verification via a tool (not an output validator)

The answer streams to the user token-by-token, so a post-hoc validator can't
retract it. Instead the **main agent calls a `verify_draft` tool before
writing its final answer**, enforced by a prompt hard rule (change 3d). The
tool runs a *second, independent agent* and returns findings the main agent
must resolve before answering.

### Files

- New: `backend/app/ai/verify.py`
- Edit: `backend/app/ai/tools.py` (registration), `backend/app/ai/agent.py`
  (nothing structural — verifier gets its own module-level Agent), `prompt.py`
  (hard rule, change 3d)
- New tests: extend `backend/tests/test_agent_flow.py`

### verify.py sketch

```python
from pydantic import BaseModel
from pydantic_ai import Agent
from pydantic_ai.usage import UsageLimits

class Finding(BaseModel):
    claim: str          # the numeric/logical claim checked
    verdict: str        # "confirmed" | "wrong" | "incoherent" | "unverifiable"
    detail: str         # what the re-derivation showed, with numbers

class VerificationReport(BaseModel):
    findings: list[Finding]
    ok: bool            # True only if no "wrong"/"incoherent" findings

VERIFIER_LIMITS = UsageLimits(request_limit=6, total_tokens_limit=150_000)

verifier: Agent[AssistantDeps, VerificationReport] = Agent(
    deps_type=AssistantDeps,
    output_type=VerificationReport,
    instructions=VERIFIER_PROMPT,
    retries=1,
    name="fortnox-insights-verifier",
)
# register ONLY these tools on the verifier: query_ledger, calculate,
# run_python (reuse the same underlying functions from tools.py — factor the
# plain functions out so both agents can register them).
```

`VERIFIER_PROMPT` (write it verbatim into the module):

> You are a skeptical financial auditor. You receive a user question and a
> DRAFT answer containing numeric claims. Your only job is to try to refute
> it. For every number that carries the conclusion: re-derive it
> independently with run_python / query_ledger / calculate — do not trust the
> draft's own arithmetic. Check that every figure appearing in more than one
> place is consistent, and that stated totals equal the sum of their stated
> parts. Check bracket/threshold logic explicitly: a marginal rate applies
> only to the slice of income above the threshold, never to a whole amount
> unless the whole amount is above it. Mark each claim confirmed / wrong /
> incoherent / unverifiable, with the re-derived value. You cannot search the
> web: if a claim rests on an external parameter, mark it unverifiable and
> say what source the draft should cite. Be terse.

### Tool registration (tools.py)

```python
@agent.tool
async def verify_draft(ctx: RunContext[AssistantDeps], question: str, draft: str) -> dict:
    """MANDATORY before finalizing any answer that contains computed numbers
    (totals, tax effects, projections, comparisons). Pass the user's question
    and your draft answer (or a compressed list of every numeric claim + how
    you derived it). An independent auditor re-derives the numbers and
    returns findings; fix every 'wrong'/'incoherent' finding before you
    answer, and mention material corrections."""
    result = await verify.verifier.run(
        f"QUESTION:\n{question}\n\nDRAFT:\n{draft}",
        model=build_model_for_verifier(),
        deps=ctx.deps,
        usage_limits=verify.VERIFIER_LIMITS,
    )
    return result.output.model_dump()
```

- `build_model_for_verifier()`: same as `build_model()` but honoring a new
  optional `AI_VERIFIER_MODEL` env (falls back to `AI_MODEL`). Add to
  `config.py` + `.env.example`.
- Raise the **main** agent's budget to accommodate the pass:
  `USAGE_LIMITS = UsageLimits(request_limit=20, total_tokens_limit=600_000)`
  in `agent.py`. The benchmark run used at most 6 requests, so this is
  headroom, not an invitation.
- Cost control: the prompt rule (3d) scopes mandatory verification to answers
  with computed numbers; chit-chat and single-lookup answers skip it.

### Tests

- With `TestModel` on both agents: assert `verify_draft` is registered, that
  calling it invokes the verifier agent, and that the SSE stream still
  completes (existing `test_agent_flow.py` patterns).
- Unit-test the findings plumbing: a stub verifier returning one `wrong`
  finding surfaces it in the tool result dict.

---

## Change 3 — prompt upgrades (`prompt.py`)

All in `HARD_RULES` / `TOOL_GUIDE`. Keep the numbering contiguous.

**3a. Parameter enumeration (new hard rule).**

> **Enumerate parameters before computing.** Before any tax/regulatory
> computation, list every year-specific parameter the result depends on
> (thresholds, rates, basbelopp, rule changes in force this year). Verify
> EACH with web_search/fetch_page and cite it, or explicitly label it
> "assumed". If a rule changed recently (new year, reform), search for the
> current year's version by name before relying on last year's logic.

**3b. Evidence before hedging (new hard rule).**

> **Query before you hedge.** Never write "it depends on how it was booked"
> or "confirm with your accountant whether X" when the mirror can settle X —
> pull the voucher/rows first (e.g. a VAT split is visible in the voucher's
> 26xx rows). Hedge only on things the data genuinely cannot show. The
> accountant disclaimer (rule 6) is for judgment calls, not for facts you
> declined to look up.

**3c. Assume-and-deliver (REPLACE hard rule 1).** Current rule 1 ("Clarify
before fetching... ask ONE short clarifying question") caused the Q3 stall.
New text:

> **Prefer a stated assumption over a blocking question.** If a question has
> a defensible default reading, state the assumption in one line, deliver the
> full answer under it, and invite correction ("if you meant X instead, say
> so and I'll redo it"). Ask a clarifying question first ONLY when the answer
> would change materially between readings and no default is defensible.
> Never stall on details that scale linearly (hours/week, one vs two people)
> — answer for the default and show the per-unit sensitivity.

**3d. Verification gate (new hard rule, with change 2).**

> **Verify before finalizing.** Any answer whose conclusion rests on computed
> numbers must go through verify_draft first. Fix every wrong/incoherent
> finding; if a finding changes a number materially, say so in the answer.
> Sanity rules the verifier will enforce — pre-check them yourself: a total
> must equal the sum of its stated parts; the same quantity must not appear
> with two values; marginal rates apply only to the slice above a threshold.

**3e. TOOL_GUIDE additions.**

> - Use run_python (not chained calculate calls) for anything with more than
>   two arithmetic steps: pivots, bracket computations, reconciliations.
>   Build month × category matrices in one script.
> - When the user asks about "actual" vs booked costs, sweep the whole year
>   for periodisering/avskrivning rows before excluding anything, and show
>   the excluded items separately rather than silently dropping them.
> - Check read_reference at the start of any car/benefit/payroll question —
>   prior audits (e.g. CASE_STUDY_BILFORMAN) contain verified values and
>   known data-quality issues you must not re-derive wrong.
> - If last_sync (in the user-turn context) is not today and the question is
>   about current state, call trigger_sync first.

`build_system_prompt()` is `lru_cache`d per process; no other change needed.

---

## Change 4 — `trigger_sync` tool

**Goal.** "Pull latest data" becomes fulfillable instead of silently ignored.

### Design

`backend/app/sync.py` already has the machinery: module-level `state`,
`asyncio.Lock`, `async def run()`. The tool wraps it:

```python
@agent.tool_plain
async def trigger_sync() -> dict:
    """Refresh the local mirror from Fortnox (same as the UI's sync button).
    Use when the user asks for the latest data, or when last_sync predates
    today and the question concerns current state. Takes ~10-30s. Returns
    the sync result including last_sync and per-entity counts."""
    from .. import sync
    if sync.state["status"] == "running":
        ...  # wait for the in-flight sync instead of starting another
    await sync.run()          # sync.run() already no-ops via its lock if racing
    return {k: sync.state[k] for k in ("status", "error", "counts", "last_sync")}
```

Implementation notes:

- Check how `sync.run()` behaves when called concurrently with the UI (the
  `_lock` in sync.py) and reuse that; if it returns immediately while a sync
  is running, poll `sync.state` with `asyncio.sleep(1)` up to ~90s.
- On `status == "error"` return the error text (no `ModelRetry` — the model
  should tell the user, not retry).
- **This is the single deliberate exception** to "the Fortnox client is not
  reachable from the tool layer". Keep the exception narrow: the tool takes
  no parameters and returns only the sync status dict — no Fortnox payloads
  flow to the model. Update the module docstring in `tools.py` and the
  comment in `agent.py` to name this exception explicitly.
- Invalidate the prompt cache facts if needed: `build_system_prompt` is
  cached and contains year coverage; a sync that adds a new financial year
  won't appear until process restart. Acceptable — note it in a comment.

### Tests

- Stub `sync.run` / `sync.state`; assert the tool reports done/error states
  and doesn't double-start a running sync.

---

## Change 5 — `read_reference` tool

**Goal.** Give the agent the project's own knowledge: `docs/*.md` case
studies and design docs (the bilförmån audit's verified values, known
misbookings, prior analyses).

### Design

```python
@agent.tool_plain
def read_reference(name: str | None = None, search: str | None = None) -> dict:
    """Read the project's reference docs (prior audits and case studies with
    VERIFIED findings — e.g. correct bilförmån basis, known misbookings).
    Call with no args to list available docs with one-line summaries. Pass
    name to read one (optionally search=<regex> to return only matching
    sections). Check here before re-deriving anything a prior audit already
    settled."""
```

- Reference roots: `settings.context_dir` (default `<repo>/context`) **and**
  `settings.docs_dir` (default `<repo>/docs`), globbed in that order (added to
  `config.py`; the backend already resolves `../.env`, follow that pattern).
  As-built, `read_reference` exposes both so the agent gets the grounding
  knowledge in `context/` *and* the case-study audits in `docs/`.
- **Path safety**: `name` must match an allowlist built by globbing
  `*.md` under the reference roots at call time — never join user-supplied
  paths. Reject anything else with `ModelRetry` listing valid names.
- Listing mode returns `[{name, first_heading, size}]`.
- Reading returns the file, capped at ~30,000 chars; with `search=`, return
  the matching lines ± 10 lines of context per match instead.
- Include this proposal and the trace case study in what it can read —
  they're useful context, no redaction needed (single-user local app).

### Tests

- Traversal attempts (`../.env`, absolute paths, `..%2f`) rejected.
- Listing and section search over a temp docs dir fixture.

---

## Config summary

| Key | Where | Default | Purpose |
|---|---|---|---|
| `AI_VERIFIER_MODEL` | `.env` / `config.py` | falls back to `AI_MODEL` | cheaper/different model for the verifier |
| `context_dir` | `config.py` | `<repo>/context` | read_reference root (grounding knowledge) |
| `docs_dir` | `config.py` | `<repo>/docs` | read_reference root (design docs + case studies) |
| `USAGE_LIMITS` | `agent.py` | `request_limit=20, total_tokens_limit=600_000` | headroom for the verify pass |

`.env.example` must document `AI_VERIFIER_MODEL`.

## Acceptance criteria

Run the protocol in `CASE_STUDY_COST_ANALYSIS_TRACE.md` (same four questions,
one session, POST `/api/chat`), extract the trace from `chat_messages`, and
check:

1. **Q1** delivers a month × category matrix (salary / car / travel /
   services / other per month) built via `run_python`, excludes all
   periodisering + depreciation, flags July incomplete, and shows excluded
   items separately.
2. **Q2** proves the VAT treatment from at least one voucher's 26xx rows
   (e.g. the car-lease voucher showing exactly half the VAT reclaimed) — no
   "confirm with your accountant whether the 50% split was booked" hedge.
3. **Q3** delivers a complete FCF answer under a stated one-consultant
   assumption (no blocking clarifying question) and tests the user's cost
   assumption against the actual run-rate from the ledger.
4. **Q4** computes both scenarios with the statutory bracket logic (state
   tax only on the slice above brytpunkten — the car-benefit saving must
   come out ≈ 20% × (income − brytpunkt), NOT marginal-rate × full benefit),
   contains no self-contradictory totals, cites 2026-specific parameters
   (jobbskatteavdrag plateau/max, current 3:12 rules) with sources, and
   surfaces the case study's known benefit over-report via read_reference.
5. `verify_draft` appears in the trace of every numeric answer; at least the
   Q4 trace shows findings being produced.
6. All existing tests plus the new ones pass offline
   (`backend/tests`, TestModel, zero tokens).
7. Re-score both traces against the 10-trait rubric; target ≥ 8/10 traits
   satisfied (was ~5/10).

## Non-goals

- No Claude Agent SDK / Anthropic SDK integration; no Node.
- No write access of any kind to Fortnox; `trigger_sync` only refreshes the
  local mirror through the existing sync path.
- No frontend changes (the SSE protocol already renders new tools' calls
  generically in the trace drawer).
- No third-party packages inside the sandbox (stdlib only) — revisit only if
  matrix work proves to need pandas.
