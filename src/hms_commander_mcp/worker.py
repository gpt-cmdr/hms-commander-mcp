"""Killable per-request workers bound import and parser time."""
import multiprocessing
import sys
import threading
from .contracts import ReadRequest, ReadResult
from .policy import Policy

# A worker has no shared HmsPrj or global project state. Limit parser concurrency
# so concurrent client requests cannot create unbounded child processes.
SLOTS = threading.BoundedSemaphore(2)


def _child(connection, roots, payload):
    try:
        sys.stdout = sys.stderr
        from .adapter import read_sections
        result = read_sections(Policy(roots), ReadRequest.model_validate(payload))
        connection.send((True, result.model_dump(mode="json")))
    except Exception as exc:
        # Errors are bounded and do not disclose a traceback or dump source text.
        connection.send((False, f"{type(exc).__name__}: {str(exc)[:600]}"))
    finally:
        connection.close()


def bounded_read(policy: Policy, request: ReadRequest) -> ReadResult:
    if not SLOTS.acquire(blocking=False):
        raise ValueError("Server is busy; retry one bounded request")
    parent = child = process = None
    try:
        context = multiprocessing.get_context("spawn")
        parent, child = context.Pipe(duplex=False)
        process = context.Process(target=_child, args=(child, list(policy.roots), request.model_dump()), daemon=True)
        process.start()
        child.close()
        if not parent.poll(request.timeout_seconds):
            raise ValueError("Request exceeded its time budget; use a narrower query or Python")
        try:
            ok, payload = parent.recv()
        except EOFError:
            raise ValueError("Reader exited without a result") from None
        if not ok:
            raise ValueError(payload)
        return ReadResult.model_validate(payload)
    finally:
        _cleanup(process, parent, child)


def _cleanup(process, parent, child):
    # Even allocation/start/termination/pipe-close failures release the slot.
    try:
        if process is not None and process.pid is not None:
            if process.is_alive():
                process.terminate()
            process.join(timeout=1)
            if process.is_alive():
                process.kill()
                process.join(timeout=1)
    finally:
        try:
            if parent is not None:
                parent.close()
        finally:
            try:
                if child is not None:
                    child.close()
            finally:
                SLOTS.release()


def _pypi_child(connection):
    try:
        sys.stdout = sys.stderr
        import json
        from urllib.request import Request, urlopen
        from packaging.version import Version
        versions = {}
        for package in ("hms-commander", "mcp"):
            request = Request(f"https://pypi.org/pypi/{package}/json", headers={"User-Agent": "hms-commander-mcp-version-check"})
            with urlopen(request, timeout=2) as response:
                data = response.read(512 * 1024 + 1)
            if len(data) > 512 * 1024:
                raise ValueError("Metadata exceeded version-check budget")
            payload = json.loads(data)
            stable = [Version(raw) for raw, files in payload["releases"].items()
                      if not Version(raw).is_prerelease and not Version(raw).is_devrelease
                      and any(not file.get("yanked", False) for file in files)]
            versions[package] = str(max(stable))
        connection.send((True, versions))
    except Exception as exc:
        connection.send((False, f"{type(exc).__name__}: {str(exc)[:200]}"))
    finally:
        connection.close()


def bounded_version_check() -> tuple[bool, dict | str]:
    if not SLOTS.acquire(blocking=False):
        return False, "Version check skipped: server is busy"
    parent = child = process = None
    try:
        context = multiprocessing.get_context("spawn")
        parent, child = context.Pipe(duplex=False)
        process = context.Process(target=_pypi_child, args=(child,), daemon=True)
        process.start()
        child.close()
        if not parent.poll(5):
            return False, "PyPI unavailable within the five-second metadata budget"
        try:
            return parent.recv()
        except EOFError:
            return False, "Metadata reader exited without a result"
    except (OSError, RuntimeError) as exc:
        return False, f"Metadata worker unavailable: {type(exc).__name__}"
    finally:
        _cleanup(process, parent, child)
