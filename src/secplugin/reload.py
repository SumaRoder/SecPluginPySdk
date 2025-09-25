import asyncio
import os
import signal
import sys
import time
from pathlib import Path
from typing import Dict, Optional
import aiofiles
from .logger import Logger
from concurrent.futures import ThreadPoolExecutor

_executor = ThreadPoolExecutor()

def _iter_py_files(root: Path):
    for p in root.rglob("*.py"):
        yield p.resolve()

async def _mtimes(root: Path) -> Dict[Path, float]:
    mt = {}
    for file in _iter_py_files(root):
        try:
            stat = await asyncio.get_running_loop().run_in_executor(
                _executor, os.stat, file
            )
            mt[file] = stat.st_mtime
        except (FileNotFoundError, OSError):
            continue
    return mt

def _has_changed(old: Dict[Path, float], new: Dict[Path, float]) -> bool:
    if len(old) != len(new):
        return True
    return any(old[f] != new[f] for f in new)


def _reexec():
    sys.stdout.flush()
    sys.stderr.flush()
    os.execv(sys.executable, [sys.executable] + sys.argv)

async def _watcher(logger, root: Path, interval: float = 0.8):
    old = await _mtimes(root)
    while True:
        await asyncio.sleep(interval)
        new = await _mtimes(root)
        if _has_changed(old, new):
            old = new
            print("文件被修改，发生热重载", flush=True)
            try:
                _reexec()
            except Exception as e:
                print("热重载失败", Logger._format_exception(e), flush=True)

class HotReload:
    _task: Optional[asyncio.Task] = None

    @staticmethod
    def enable(logger, root: Optional[Path] = None, interval: float = 0.8) -> None:
        if HotReload._task is not None and not HotReload._task.done():
            return

        root = (root or Path(os.getcwd())).resolve()

        signal.signal(signal.SIGTERM, lambda *_: sys.exit(0))

        loop = asyncio.get_running_loop()
        HotReload._task = loop.create_task(
            _watcher(logger, root, interval), name="hot-reload-watcher"
        )
    
    @staticmethod
    def disable():
        if HotReload._task and not HotReload._task.done():
            HotReload._task.cancel()
            HotReload._task = None
