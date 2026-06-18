from __future__ import annotations

import asyncio
import os
import signal
import subprocess
import sys
import time
from importlib.util import find_spec
from pathlib import Path
from typing import TYPE_CHECKING, Optional, Set

if TYPE_CHECKING:
    from watchdog.observers.api import BaseObserver

_WATCHDOG_AVAILABLE = find_spec("watchdog") is not None
_RESTART_EXIT_CODE = 42

def _create_reload_handler(loop: asyncio.AbstractEventLoop, debounce_seconds: float):
    """创建文件监控事件处理器。"""
    from watchdog.events import FileSystemEventHandler as _Handler
    
    class _ReloadEventHandlerImpl(_Handler):
        def __init__(self, loop: asyncio.AbstractEventLoop, debounce_seconds: float = 0.5):
            self._loop = loop
            self._reload_triggered = False
            self._debounce_seconds = debounce_seconds
            self._pending_restart: Optional[asyncio.TimerHandle] = None
            self._changed_files: Set[str] = set()
        
        def on_any_event(self, event):
            src_path = getattr(event, 'src_path', '')
            if not src_path.endswith('.py'):
                return
            
            if getattr(event, 'is_directory', False) or src_path.endswith('~') or '/.' in src_path:
                return

            self._changed_files.add(src_path)
            
            if self._pending_restart:
                self._pending_restart.cancel()
            
            self._pending_restart = self._loop.call_later(
                self._debounce_seconds,
                self._do_restart,
                src_path
            )

        def _do_restart(self, path: str):
            if self._reload_triggered:
                return
            
            self._reload_triggered = True
            print(f"检测到文件变化: {path} (共 {len(self._changed_files)} 个文件)", flush=True)
            self._loop.call_soon_threadsafe(_trigger_restart)
    
    return _ReloadEventHandlerImpl(loop, debounce_seconds)


def _trigger_restart():
    """触发进程重启。"""
    def force_exit():
        time.sleep(2)
        os._exit(_RESTART_EXIT_CODE)
    
    import threading
    threading.Thread(target=force_exit, daemon=True).start()
    os._exit(_RESTART_EXIT_CODE)


def _start_supervisor(root: Path, interval: float) -> None:
    """启动监控进程，管理子工作进程。"""
    while True:
        env = os.environ.copy()
        env["_HOTRELOAD_CHILD_WORKER"] = "1"
        
        proc: Optional[subprocess.Popen] = None
        
        try:
            proc = subprocess.Popen(
                [sys.executable] + sys.argv,
                env=env,
                cwd=str(Path.cwd())
            )
            code = proc.wait()
            
            if code != _RESTART_EXIT_CODE:
                sys.exit(code)
                
        except KeyboardInterrupt:
            if proc is not None:
                proc.terminate()
                proc.wait()
            sys.exit(0)


class HotReload:
    """热重载管理器。"""
    
    _observer: Optional[BaseObserver] = None
    _task: Optional[asyncio.Task] = None
    _watching = False

    @staticmethod
    def enable(root: Optional[Path] = None, interval: float = 0.8, debounce: float = 2.0) -> bool:
        """启用热重载监控。
        
        Args:
            root: 监控根目录，默认为当前工作目录
            interval: 监控轮询间隔（秒）
            debounce: 防抖时间（秒）
            
        Returns:
            是否成功启用
        """
        if HotReload._watching:
            return True
        
        if not _WATCHDOG_AVAILABLE:
            return False
        
        if not os.environ.get("_HOTRELOAD_CHILD_WORKER"):
            root = (root or Path.cwd()).resolve()
            _start_supervisor(root, interval)
        
        signal.signal(signal.SIGTERM, lambda *_: sys.exit(0))
        
        root = (root or Path.cwd()).resolve()
        
        from watchdog.observers import Observer
        observer = Observer()
        handler = _create_reload_handler(asyncio.get_running_loop(), debounce)
        observer.schedule(handler, str(root), recursive=True)
        observer.start()
        
        HotReload._observer = observer
        HotReload._watching = True
        
        async def _dummy_watcher():
            while HotReload._watching:
                await asyncio.sleep(1)
        
        HotReload._task = asyncio.get_running_loop().create_task(
            _dummy_watcher(), name="hot-reload-watcher"
        )
        
        return True

    @staticmethod
    def disable() -> None:
        """禁用热重载监控。"""
        HotReload._watching = False
        if HotReload._observer:
            HotReload._observer.stop()
            HotReload._observer.join()
            HotReload._observer = None
        if HotReload._task and not HotReload._task.done():
            HotReload._task.cancel()
            HotReload._task = None
