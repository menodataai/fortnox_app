"""read_reference tests (F9 change 5) — offline, zero tokens.

Covers listing, section search, full-read truncation and path-traversal
rejection over a temp reference-dir fixture.

Run: .venv/bin/python tests/test_reference.py
"""

import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.ai import reference  # noqa: E402
from app.config import settings  # noqa: E402


def _fixture_dirs() -> tuple[Path, Path]:
    ctx = Path(tempfile.mkdtemp()) / "context"
    docs = Path(tempfile.mkdtemp()) / "docs"
    ctx.mkdir(parents=True)
    docs.mkdir(parents=True)
    (ctx / "COMPANY_CONTEXT.md").write_text(
        "# Company context\n\nThe office rent is 14,500 kr/month.\n"
        + "\n".join(f"filler line {i}" for i in range(50)),
        encoding="utf-8",
    )
    (docs / "CASE_STUDY_BILFORMAN.md").write_text(
        "# Bilförmån audit\n\nKnown issue: 210 kr/mo over-report.\n", encoding="utf-8"
    )
    # a decoy the tool must never surface (not *.md)
    (docs / "secret.env").write_text("OPENROUTER_API_KEY=leak", encoding="utf-8")
    settings.context_dir = ctx
    settings.docs_dir = docs
    return ctx, docs


def test_list() -> None:
    docs = reference.list_docs()
    names = {d["name"] for d in docs}
    assert names == {"COMPANY_CONTEXT.md", "CASE_STUDY_BILFORMAN.md"}, names
    company = next(d for d in docs if d["name"] == "COMPANY_CONTEXT.md")
    assert company["first_heading"] == "Company context"
    assert company["size"] > 0
    print("list OK")


def test_read_full_and_truncate() -> None:
    out = reference.read_doc("CASE_STUDY_BILFORMAN.md")
    assert "210 kr/mo over-report" in out["content"]
    assert out["truncated"] is False

    orig = reference.MAX_DOC_CHARS
    reference.MAX_DOC_CHARS = 20
    try:
        out = reference.read_doc("COMPANY_CONTEXT.md")
        assert out["truncated"] is True and out["content"].endswith("[... truncated]")
    finally:
        reference.MAX_DOC_CHARS = orig
    print("read/truncate OK")


def test_search() -> None:
    out = reference.read_doc("COMPANY_CONTEXT.md", search=r"14,?500")
    assert "14,500" in out["matches"]
    assert "filler line 40" not in out["matches"]  # only the hit + context, not the far tail

    out = reference.read_doc("COMPANY_CONTEXT.md", search="no-such-string-here")
    assert out["matches"] == "(no matching sections)"
    print("search OK")


def test_traversal_rejected() -> None:
    for bad in ("../.env", "/etc/passwd", "..%2f..%2fsecret.env", "secret.env",
                "COMPANY_CONTEXT", "../docs/CASE_STUDY_BILFORMAN.md"):
        try:
            reference.read_doc(bad)
            raise AssertionError(f"should have rejected: {bad}")
        except ValueError:
            pass
    # invalid regex is a clean ValueError, not a crash
    try:
        reference.read_doc("COMPANY_CONTEXT.md", search="(unclosed")
        raise AssertionError("should have rejected bad regex")
    except ValueError:
        pass
    print("traversal rejected OK")


def main() -> None:
    _fixture_dirs()
    test_list()
    test_read_full_and_truncate()
    test_search()
    test_traversal_rejected()
    print("ALL REFERENCE TESTS PASSED")


if __name__ == "__main__":
    main()
