import asyncio
import os
import signal
import sys
import subprocess
import time
from pathlib import Path
from typing import Optional, Set

try:
    from watchdog.observers import Observer
    from watchdog.events import FileSystemEventHandler, FileModifiedEvent, FileCreatedEvent, FileDeletedEvent
    _WATCHDOG_AVAILABLE = True
except ImportError:
    _WATCHDOG_AVAILABLE = False
    Observer = None
    FileSystemEventHandler = None


_RESTART_EXIT_CODE = 42
_CHILD_WORKER_ENV_KEY = "_HOTRELOAD_CHILD_WORKER"


_ReloadEventHandler = None

def _create_reload_handler(loop: asyncio.AbstractEventLoop, debounce_seconds: float):
    class _ReloadEventHandlerImpl(FileSystemEventHandler):
        def __init__(self, loop: asyncio.AbstractEventLoop, debounce_seconds: float = 0.5):
            self._loop = loop
            self._reload_triggered = False
            self._debounce_seconds = debounce_seconds
            self._pending_restart: Optional[asyncio.TimerHandle] = None
            self._changed_files: Set[str] = set()
            self._last_event_time = 0
        
        def on_any_event(self, event):
            if not event.src_path.endswith('.py'):
                return
            
            if event.is_directory or event.src_path.endswith('~') or '/.' in event.src_path:
                return

            self._last_event_time = time.time()
            self._changed_files.add(event.src_path)
            
            if self._pending_restart:
                self._pending_restart.cancel()
            
            self._pending_restart = self._loop.call_later(
                self._debounce_seconds,
                self._do_restart,
                event.src_path
            )

        def _do_restart(self, path: str):
            if self._reload_triggered:
                return
            
            self._reload_triggered = True
            print(f"检测到文件变化: {path} (共 {len(self._changed_files)} 个文件)", flush=True)
            self._loop.call_soon_threadsafe(_trigger_restart)
    
    return _ReloadEventHandlerImpl(loop, debounce_seconds)


def _trigger_restart():
    def force_exit():
        import time
        time.sleep(2)
        os._exit(_RESTART_EXIT_CODE)
    
    import threading
    threading.Thread(target=force_exit, daemon=True).start()
    
    os._exit(_RESTART_EXIT_CODE)


def _start_supervisor(root: Path, interval: float):
    while True:
        env = os.environ.copy()
        env[_CHILD_WORKER_ENV_KEY] = "1"
        
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
            proc.terminate()
            proc.wait()
            sys.exit(0)


class HotReload:
    _observer: Optional[Observer] = None
    _task: Optional[asyncio.Task] = None
    _watching = False

    @staticmethod
    def enable(root: Optional[Path] = None, interval: float = 0.8, debounce: float = 2.0) -> bool:
        if HotReload._watching:
            return True
        
        if not _WATCHDOG_AVAILABLE:
            return False
        
        if not os.environ.get(_CHILD_WORKER_ENV_KEY):
            root = (root or Path.cwd()).resolve()
            _start_supervisor(root, interval)
        
        signal.signal(signal.SIGTERM, lambda *_: sys.exit(0))
        
        root = (root or Path.cwd()).resolve()
        
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
    def disable():
        HotReload._watching = False
        if HotReload._observer:
            HotReload._observer.stop()
            HotReload._observer.join()
            HotReload._observer = None
        if HotReload._task and not HotReload._task.done():
            HotReload._task.cancel()
            HotReload._task = None
