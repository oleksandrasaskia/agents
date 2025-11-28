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
import io
import threading
import contextlib


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


def _make_safe_builtins() -> dict:
    # Provide a tiny whitelist of safe builtins. This is deliberately small.
    allowed = [
        "True",
        "False",
        "None",
        "len",
        "range",
        "enumerate",
        "min",
        "max",
        "sum",
        "abs",
        "round",
        "print",
        "sorted",
        "list",
        "dict",
        "set",
        "tuple",
    ]
    builtins = {}
    src = __builtins__
    if isinstance(src, dict):
        for k in allowed:
            if k in src:
                builtins[k] = src[k]
    else:
        for k in allowed:
            if hasattr(src, k):
                builtins[k] = getattr(src, k)
    return builtins


def run_generated_code_inproc(code: str, store_api: object | None = None, timeout: int = 10) -> dict:
    """Execute generated code in-process with an injected `store` API.

    This runs `code` using `exec` in a controlled namespace where the
    following symbols are available:
      - `store`: the `erc3.store` module (if importable)
      - DTO classes from `erc3.store.dtos` (if importable)
      - `store_api`: the object passed in (if any) so code can call
        `store_api.dispatch()` or convenience helpers.

    The function captures stdout/stderr and returns a dict with
    `ok`, `stdout`, `stderr`, `error`, and `result` if the executed
    code assigned a top-level variable named `result`.

    SECURITY: This is NOT a secure sandbox. Running untrusted code with
    `exec` can execute arbitrary Python in your process. Only use locally
    with trusted or reviewed code.
    """
    ok, msg = validate_code(code)
    if not ok:
        return {"ok": False, "error": msg}

    # Prepare namespace with limited builtins and helpful imports
    namespace: dict = {}
    try:
        import erc3.store as _store_mod
        namespace["store"] = _store_mod
        # expose DTO classes for convenience
        try:
            from erc3.store import dtos as _dtos
            for name in dir(_dtos):
                if name.startswith("Req_") or name.startswith("Resp_"):
                    namespace[name] = getattr(_dtos, name)
        except Exception:
            pass
    except Exception:
        namespace["store"] = None

    if store_api is not None:
        namespace["store_api"] = store_api

    # restrict builtins
    namespace["__builtins__"] = _make_safe_builtins()

    stdout_buf = io.StringIO()
    stderr_buf = io.StringIO()

    exec_error = None
    exec_result = None

    def _worker():
        nonlocal exec_error, exec_result
        try:
            with contextlib.redirect_stdout(stdout_buf), contextlib.redirect_stderr(stderr_buf):
                exec(code, namespace)
            exec_result = namespace.get("result")
        except Exception as e:
            exec_error = e

    thread = threading.Thread(target=_worker, daemon=True)
    thread.start()
    thread.join(timeout=timeout)
    if thread.is_alive():
        return {"ok": False, "error": f"Execution timed out after {timeout}s"}

    stdout = stdout_buf.getvalue()
    stderr = stderr_buf.getvalue()

    if exec_error:
        return {"ok": False, "error": str(exec_error), "stdout": stdout, "stderr": stderr}

    return {"ok": True, "stdout": stdout, "stderr": stderr, "result": exec_result}


def example_using_store_api():
    """Example: show how to prepare a `store_api` and run generated code that uses it.

    This function is a runtime example only — it will not create a live
    `ERC3` or `StoreClient` instance. Replace the `store_api_mock` with a real
    `StoreClient` (e.g. `erc3.store.client.StoreClient(base_url)`) in your code.
    """
    # Minimal example code string that will be executed. It expects `store_api`
    # and `Req_AddProductToBasket` to be available in the namespace.
    example_code = '''
result = None
try:
    req = Req_AddProductToBasket(sku="SKU-LLM-1", quantity=1)
    resp = store_api.dispatch(req)
    print('Added', resp.model_dump())
    result = resp
except Exception as e:
    print('Error calling store API:', e)
    result = {'error': str(e)}
'''

    # Demonstration only: create a simple mock if you don't have a real client.
    class _MockResp:
        def model_dump(self):
            return {"line_count": 1, "item_count": 1}

    class _MockStoreApi:
        def dispatch(self, req):
            print('Mock dispatch called with', type(req).__name__, req.model_dump())
            return _MockResp()

    mock_store_api = _MockStoreApi()
    return run_generated_code_inproc(example_code, store_api=mock_store_api, timeout=5)


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
