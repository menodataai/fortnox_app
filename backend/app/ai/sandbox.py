"""Out-of-process Python sandbox behind the `run_python` tool (F9 change 1).

The model's script runs in a locked-down child interpreter — never `exec()`ed
in the backend process. Guarantees, in order of how much they matter:

  - read-only mirror handle (SQLite `mode=ro`; writes fail at the driver);
  - no inherited secrets — the child gets a scrubbed env (no OPENROUTER/FORTNOX);
  - no network — sandbox_runner patches `socket` before any user code runs;
  - CPU limit (RLIMIT_CPU) + wall-clock timeout (the real guard);
  - output caps so a runaway print() can't flood the model context.

Filesystem writes by the script are NOT blocked by the OS, so the child runs
in a throwaway temp cwd that is deleted afterwards — writes don't persist.
"""

import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

from .. import db

RUNNER = Path(__file__).with_name("sandbox_runner.py")

CPU_LIMIT_S = 10          # RLIMIT_CPU inside the child
WALL_TIMEOUT_S = 15       # parent-side kill; the real guard
MAX_OUTPUT_CHARS = 20_000

try:  # POSIX only; degrade gracefully where setrlimit is unavailable
    import resource
except ImportError:  # pragma: no cover — Windows
    resource = None  # type: ignore[assignment]


def _limit_resources() -> None:
    """preexec_fn — runs in the child after fork, before exec. setrlimit is a
    single async-signal-safe syscall, so it's safe here."""
    if resource is not None:
        resource.setrlimit(resource.RLIMIT_CPU, (CPU_LIMIT_S, CPU_LIMIT_S))


def _cap(text: str | None) -> str:
    text = text or ""
    if len(text) > MAX_OUTPUT_CHARS:
        return text[:MAX_OUTPUT_CHARS] + "\n...[truncated]"
    return text


def run(script: str) -> dict:
    """Execute `script` in the sandbox. Returns
    {"stdout", "stderr", "exit_code"} — never raises on a script error (the
    model needs the traceback to self-correct)."""
    workdir = tempfile.mkdtemp(prefix="sandbox-")
    try:
        proc = subprocess.run(
            [sys.executable, "-I", "-E", str(RUNNER), str(db.DB_PATH)],
            input=script,
            capture_output=True,
            text=True,
            cwd=workdir,
            env={"PATH": ""},  # scrub the backend env (API keys live there)
            timeout=WALL_TIMEOUT_S,
            preexec_fn=_limit_resources if resource is not None else None,
        )
        return {
            "stdout": _cap(proc.stdout),
            "stderr": _cap(proc.stderr),
            "exit_code": proc.returncode,
        }
    except subprocess.TimeoutExpired as e:
        return {
            "stdout": _cap(e.stdout if isinstance(e.stdout, str) else None),
            "stderr": f"Sandbox killed: exceeded {WALL_TIMEOUT_S}s wall-clock limit.",
            "exit_code": -1,
        }
    finally:
        shutil.rmtree(workdir, ignore_errors=True)
