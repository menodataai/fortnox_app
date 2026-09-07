"""Backing logic for the `read_reference` tool (F9 change 5).

Exposes the project's own knowledge to the agent: the grounding docs in
`context/` (company facts, Swedish-tax reference, glossary) and the design /
case-study docs in `docs/` (prior audits with VERIFIED values and known
misbookings). Read-only, markdown only.

Path safety: `name` is never joined to a directory. The set of readable files
is built by globbing the reference roots at call time; a name is served only
if it is an exact key in that map. Traversal / absolute paths simply aren't in
the map, so they're rejected.
"""

import re
from pathlib import Path

from ..config import PROJECT_ROOT, settings

MAX_DOC_CHARS = 30_000
CONTEXT_LINES = 10  # lines of context around each search hit


def _roots() -> list[Path]:
    # context first so its names win on a basename collision. In demo mode the
    # demo context comes first (its COMPANY_CONTEXT.md shadows the real one),
    # then the shared references (tax reference, glossary) from context/.
    roots = [settings.context_dir]
    if settings.demo_mode:
        roots.append(PROJECT_ROOT / "context")
    roots.append(settings.docs_dir)
    return roots


def _catalog() -> dict[str, Path]:
    """basename -> path for every *.md under the reference roots."""
    catalog: dict[str, Path] = {}
    for root in _roots():
        if not root.is_dir():
            continue
        for path in sorted(root.glob("*.md")):
            catalog.setdefault(path.name, path)  # first root wins
    return catalog


def _first_heading(text: str) -> str:
    for line in text.splitlines():
        s = line.strip()
        if s.startswith("#"):
            return s.lstrip("#").strip()
    return ""


def list_docs() -> list[dict]:
    """Listing mode: [{name, first_heading, size}] for every reference doc."""
    out = []
    for name, path in sorted(_catalog().items()):
        try:
            text = path.read_text(encoding="utf-8")
        except OSError:
            continue
        out.append({"name": name, "first_heading": _first_heading(text), "size": len(text)})
    return out


def read_doc(name: str, search: str | None = None) -> dict:
    """Read one doc by name. With `search` (a regex), return only matching
    sections (± context) instead of the whole file. Raises ValueError with the
    valid names if `name` is unknown."""
    catalog = _catalog()
    path = catalog.get(name)
    if path is None:
        raise ValueError(
            f"Unknown reference doc '{name}'. Valid names: "
            f"{', '.join(sorted(catalog)) or '(none)'}. "
            "Call read_reference with no arguments to list them."
        )

    text = path.read_text(encoding="utf-8")

    if search:
        try:
            pattern = re.compile(search, re.IGNORECASE)
        except re.error as e:
            raise ValueError(f"Invalid search regex: {e}") from None
        return {"name": name, "search": search, "matches": _search(text, pattern)}

    truncated = len(text) > MAX_DOC_CHARS
    return {
        "name": name,
        "content": text[:MAX_DOC_CHARS] + ("\n\n[... truncated]" if truncated else ""),
        "truncated": truncated,
    }


def _search(text: str, pattern: re.Pattern) -> str:
    lines = text.splitlines()
    keep: set[int] = set()
    for i, line in enumerate(lines):
        if pattern.search(line):
            keep.update(range(max(0, i - CONTEXT_LINES), min(len(lines), i + CONTEXT_LINES + 1)))
    if not keep:
        return "(no matching sections)"

    # emit contiguous blocks with a separator + a leading line number
    out: list[str] = []
    prev = None
    for i in sorted(keep):
        if prev is not None and i != prev + 1:
            out.append("...")
        out.append(f"{i + 1}: {lines[i]}")
        prev = i
    joined = "\n".join(out)
    if len(joined) > MAX_DOC_CHARS:
        joined = joined[:MAX_DOC_CHARS] + "\n[... truncated]"
    return joined
