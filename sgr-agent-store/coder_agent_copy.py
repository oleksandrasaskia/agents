"""Helper for running LLM-generated Python code safely.

This module provides small, pragmatic helpers to:
- validate a generated code string for suspicious constructs,
- write it to a file in a temporary directory,
- execute it with a timeout and capture stdout/stderr,
- and clean up the temporary file.

Security: this is NOT a secure sandbox. It prevents a few obvious dangerous
patterns but cannot safely run untrusted code. For production use, run inside
Docker, a VM, or a real sandboxing tool (gVisor, Firecracker, etc.).
"""
from __future__ import annotations

import re
import sys
import tempfile
import textwrap
from pathlib import Path
from subprocess import CompletedProcess, run
from typing import Tuple, Optional


_BANNED_PATTERNS = [
    r"\bsubprocess\b",
    r"\bos\.system\b",
    r"\b__import__\b",
    r"\beval\s*\(|\bexec\s*\(|\bcompile\s*\(",
    r"\bsocket\b",
    r"\brequests\b",
    r"\bftp\b",
    r"\bopen\s*\(",
]


def validate_code(code: str) -> Tuple[bool, Optional[str]]:
    """Quickly validate generated code for obviously unsafe tokens.

    Returns (ok, message). If ok is False, message explains why.
    This is a lightweight heuristic only.
    """
    for pat in _BANNED_PATTERNS:
        if re.search(pat, code):
            return False, f"Disallowed pattern found: {pat}"

    # Discourage very large single-file generations
    if len(code) > 20000:
        return False, "Generated code is too large"

    return True, None


def write_code_to_file(code: str, filename: Optional[str] = None, dir: Optional[Path] = None) -> Path:
    """Write `code` to a temporary file and return its Path.

    If `filename` is provided, it's used as the basename; otherwise a random
    temp filename is created. The file will be created inside `dir` (tempdir
    by default).
    """
    dir = dir or Path(tempfile.mkdtemp(prefix="generated_code_"))
    dir.mkdir(parents=True, exist_ok=True)
    fname = filename or "generated.py"
    path = dir / fname
    path.write_text(textwrap.dedent(code), encoding="utf-8")
    return path


def execute_code_file(path: Path, timeout: int = 10) -> CompletedProcess:
    """Execute a Python file and return a CompletedProcess with captured output.

    Uses the current Python interpreter (`sys.executable`). Raises
    `subprocess.TimeoutExpired` on timeout.
    """
    return run([sys.executable, str(path)], capture_output=True, text=True, timeout=timeout)


def run_generated_code(code: str, timeout: int = 10, filename: Optional[str] = None) -> dict:
    """Validate, write, execute generated Python code and return result dict.

    result contains: `ok` (bool), `stdout`, `stderr`, `returncode`, `error`.
    The `error` field contains validation error or exception text when present.
    """
    ok, msg = validate_code(code)
    if not ok:
        return {"ok": False, "error": msg}

    path = write_code_to_file(code, filename=filename)

    try:
        completed = execute_code_file(path, timeout=timeout)
        return {
            "ok": True,
            "stdout": completed.stdout,
            "stderr": completed.stderr,
            "returncode": completed.returncode,
            "path": str(path),
        }
    except Exception as exc:  # timeout, OSError, etc.
        return {"ok": False, "error": str(exc), "path": str(path)}


if __name__ == "__main__":
    # Demo: run a tiny generated snippet. Replace `demo_code` with a real LLM
    # produced string in a real integration.
    demo_code = '''
    # Simple demo code produced by an LLM
    print('Hello from generated code')
    for i in range(3):
        print('line', i)
    '''

    res = run_generated_code(demo_code, timeout=5)
    if res.get("ok"):
        print("--- STDOUT ---")
        print(res.get("stdout"))
        print("--- STDERR ---")
        print(res.get("stderr"))
    else:
        print("Execution failed:", res.get("error"))
