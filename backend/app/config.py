from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

PROJECT_ROOT = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=PROJECT_ROOT / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Demo mode: run entirely from a seeded local mirror (backend/data-demo/)
    # with the fictional company in context-demo/ — no Fortnox account needed.
    # Seed with scripts/seed_demo.py, then start the backend with DEMO_MODE=1.
    demo_mode: bool = False

    fortnox_client_id: str = ""
    fortnox_client_secret: str = ""
    fortnox_redirect_uri: str = "http://localhost:8000/auth/callback"
    fortnox_scopes: str = "companyinformation invoice bookkeeping payment"

    backend_port: int = 8000
    frontend_origin: str = "http://localhost:5173"

    openrouter_api_key: str = ""
    ai_model: str = "anthropic/claude-opus-4.8"
    # Verifier agent (F9 change 2). Falls back to ai_model when blank.
    ai_verifier_model: str = ""
    tavily_api_key: str = ""
    ai_search_domains: str = (
        "skatteverket.se,www4.skatteverket.se,riksgalden.se,regeringen.se,"
        "bolagsverket.se,riksdagen.se,lagen.nu,bfn.se,verksamt.se,scb.se"
    )

    fortnox_auth_base: str = "https://apps.fortnox.se/oauth-v1"
    fortnox_api_base: str = "https://api.fortnox.se/3"

    # read_reference roots (F9 change 5). context/ holds the agent's grounding
    # knowledge (company + Swedish-tax reference); docs/ holds design docs and
    # the prior case-study audits. Both are exposed, context first.
    context_dir: Path = PROJECT_ROOT / "context"
    docs_dir: Path = PROJECT_ROOT / "docs"


settings = Settings()

# Demo mode gets its own data dir and grounding context so it can never touch
# (or leak) the real company's mirror.
DATA_DIR = PROJECT_ROOT / "backend" / ("data-demo" if settings.demo_mode else "data")
if settings.demo_mode:
    settings.context_dir = PROJECT_ROOT / "context-demo"
