"""Heavy parsing in a short-lived helper process, so its memory goes back to the system.

Python keeps memory it has used: a parse that briefly needs 50 MB leaves the server 50 MB bigger, and the arenas
it touched stay fragmented. Measured 2026-11-25 on the M1: Python's live data about 160 MB, the process 245-377 MB,
swinging with every big download. In a helper process the memory is returned when the helper exits.

One helper serves a burst of jobs (the news, protest and aircraft feeds come every 2-20 minutes) and exits once it
has been idle for IDLE_S seconds, or after MAX_JOBS jobs, so it exists for a few seconds at a time, not all day.
Starting one costs a Python start plus the imports of the job's module (well under a second on the M1).

A job is a plain top-level function of a module that is cheap to import, with arguments and result that pickle.
"""
import asyncio
import concurrent.futures
import multiprocessing
import threading
import time
from concurrent.futures.process import BrokenProcessPool

IDLE_S = 20
MAX_JOBS = 25

_lock = threading.Lock()
_pool: concurrent.futures.ProcessPoolExecutor | None = None
_busy = 0
_last = 0.0


def _get() -> concurrent.futures.ProcessPoolExecutor:
    global _pool
    if _pool is None:
        # spawn: a fresh interpreter, not a copy of the server's memory (macOS's default too)
        _pool = concurrent.futures.ProcessPoolExecutor(max_workers=1, mp_context=multiprocessing.get_context("spawn"),
                                                       max_tasks_per_child=MAX_JOBS)
    return _pool


def _drop(kill: bool = False) -> None:
    """Let the helper go (call with the lock held). `kill` for one that hangs or broke."""
    global _pool
    pool, _pool = _pool, None
    if pool is None:
        return
    if kill:
        for p in list((getattr(pool, "_processes", None) or {}).values()):
            try:
                p.terminate()
            except Exception:
                pass
    pool.shutdown(wait=False, cancel_futures=True)


def _close_if_idle() -> None:
    with _lock:
        if _busy == 0 and time.monotonic() - _last >= IDLE_S - 0.5:
            _drop()


def run_sync(fn, *args, timeout: float = 300):
    """Run `fn(*args)` in the helper and return its result. Blocks: call it from a worker thread (see `run`)."""
    global _busy, _last
    with _lock:
        pool = _get()
        _busy += 1
    try:
        return pool.submit(fn, *args).result(timeout=timeout)
    except (BrokenProcessPool, concurrent.futures.TimeoutError):
        with _lock:
            if _pool is pool:
                _drop(kill=True)
        raise
    finally:
        with _lock:
            _busy -= 1
            _last = time.monotonic()
        t = threading.Timer(IDLE_S, _close_if_idle)
        t.daemon = True
        t.start()


async def run(fn, *args, timeout: float = 300):
    """`run_sync` from async code, without blocking the event loop."""
    return await asyncio.to_thread(run_sync, fn, *args, timeout=timeout)


def shutdown() -> None:
    with _lock:
        _drop()
