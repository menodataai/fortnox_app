# Contributing

Thanks for your interest! This project started as an in-house tool for
understanding one company's own finances — contributions that keep it useful
for small Swedish ABs are very welcome.

## Getting started

The fastest way to a working setup is demo mode — no Fortnox account needed:

```bash
cd backend
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
.venv/bin/python -m scripts.seed_demo
DEMO_MODE=1 .venv/bin/uvicorn app.main:app --reload --port 8000
# in another terminal:
cd frontend && npm install && npm run dev
```

The AI chat additionally needs an `OPENROUTER_API_KEY` in `.env` (and
`TAVILY_API_KEY` for web research) — everything else works without keys.

## Development notes

- **Tests** (`backend/tests/`) run offline — the agent loop is exercised with
  Pydantic AI's `TestModel`, zero tokens. Each file is a standalone script:
  `for t in tests/test_*.py; do .venv/bin/python $t; done`
- **Evals** hit real models against the author's real books, so they are kept
  local (`backend/evals/` is gitignored). If you touch answer quality, describe
  in the PR how you validated it — ideally against the demo dataset.
- Frontend API types are generated from the backend's OpenAPI schema:
  `npm run gen:types` (backend must be running).
- The mirror schema and analytics live in `backend/app/db.py` and
  `analytics.py`; every analytics function doubles as an AI tool, so keep
  signatures simple and outputs JSON-friendly.

## Ideas that would fit well

- Support for more Fortnox setups (other VAT periods, more voucher series,
  monthly VAT, brutto payroll vouchers)
- More BAS account explanations (`backend/app/bas.py`)
- Localization of the UI (Swedish)
- Report analyzer (F10 on the roadmap in `docs/FEATURES.md`)

## Pull requests

Keep PRs focused. If you're changing AI behavior, include a before/after
example (question + answer) and make sure the offline tests still pass.
Never commit real company data — `.env`, `backend/data/` and
`context/COMPANY_CONTEXT.md` are gitignored for a reason.
