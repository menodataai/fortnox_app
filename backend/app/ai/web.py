"""Web research tools: Tavily search restricted to authoritative Swedish
sources, and page fetch with the allowlist enforced in our code — no model,
on any vendor, can fetch arbitrary URLs."""

from urllib.parse import urlparse

import httpx

from ..config import settings

MAX_PAGE_CHARS = 32_000  # ~8k tokens


def allowed_domains() -> list[str]:
    return [d.strip().lower() for d in settings.ai_search_domains.split(",") if d.strip()]


def host_allowed(url: str, extra_domains: set[str] | None = None) -> bool:
    host = (urlparse(url).hostname or "").lower()
    if not host:
        return False
    domains = set(allowed_domains()) | (extra_domains or set())
    return any(host == d or host.endswith("." + d) for d in domains)


async def tavily_search(query: str, max_results: int = 5) -> list[dict]:
    """Search via Tavily with include_domains pinned to the allowlist.
    Returns [{title, url, snippet}]."""
    if not settings.tavily_api_key:
        raise RuntimeError("TAVILY_API_KEY is not configured.")
    async with httpx.AsyncClient(timeout=20) as client:
        resp = await client.post(
            "https://api.tavily.com/search",
            json={
                "api_key": settings.tavily_api_key,
                "query": query,
                "max_results": max(1, min(max_results, 8)),
                "include_domains": allowed_domains(),
            },
        )
        resp.raise_for_status()
        data = resp.json()
    return [
        {"title": r.get("title", ""), "url": r.get("url", ""), "snippet": r.get("content", "")}
        for r in data.get("results", [])
    ]


async def fetch_page_text(url: str, extra_domains: set[str] | None = None) -> str:
    """Fetch one page and extract readable text (trafilatura), truncated."""
    if not url.lower().startswith(("http://", "https://")):
        raise ValueError("Only http(s) URLs can be fetched.")
    if not host_allowed(url, extra_domains):
        raise ValueError(
            f"Host not in the allowlist ({', '.join(sorted(allowed_domains()))}). "
            "Use web_search first — domains surfaced by search results become fetchable."
        )
    async with httpx.AsyncClient(timeout=25, follow_redirects=True) as client:
        resp = await client.get(url, headers={"User-Agent": "FortnoxInsights/0.2 (personal analytics)"})
        resp.raise_for_status()
        html = resp.text

    import trafilatura  # deferred: import is slow

    text = trafilatura.extract(html, output_format="markdown", url=url) or ""
    if not text.strip():
        raise ValueError("Could not extract readable text from that page.")
    if len(text) > MAX_PAGE_CHARS:
        text = text[:MAX_PAGE_CHARS] + "\n\n[... truncated]"
    return text
