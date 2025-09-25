import os, sys, time, threading, importlib, traceback
from pathlib import Path
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

_watcher_thread = None
_shutdown = object()
_mtimes = {}

def _iter_modules(root: Path):
    main_file = Path(sys.modules['__main__'].__file__).resolve()
    yield main_file
    for m in list(sys.modules.values()):
        f = getattr(m, '__file__', None)
        if f and f.endswith('.py'):
            yield Path(f).resolve()

def _reload():
    main_mod = sys.modules['__main__']
    main_file = Path(main_mod.__file__).resolve()
    for p in _iter_modules(main_file.parent):
        if not p.exists():
            continue
        mtime = p.stat().st_mtime
        old = _mtimes.get(p, 0)
        if mtime > old:
            _mtimes[p] = mtime
            if p == main_file:
                continue
            name = None
            for k, v in sys.modules.items():
                if getattr(v, '__file__', None) == str(p):
                    name = k
                    break
            if name:
                try:
                    importlib.reload(sys.modules[name])
                except Exception:
                    traceback.print_exc()
    try:
        with open(main_file, 'rb') as f:
            code = compile(f.read(), main_file, 'exec')
            exec(code, main_mod.__dict__)
    except Exception:
        traceback.print_exc()

class Handler(FileSystemEventHandler):
    def on_modified(self, ev):
        if ev.src_path.endswith('.py'):
            print('[watchdog] changed', ev.src_path)
            _reload()

def _watch(root: Path, interval=None):
    o = Observer()
    o.schedule(Handler(), str(root), recursive=True)
    o.start()
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        o.stop()
    o.join()


class HotReload:
    @staticmethod
    def enable(root='.', interval=0.5):
        global _watcher_thread
        if _watcher_thread and _watcher_thread.is_alive():
            print('[autoreload] already enabled')
            return
        root = Path(root).resolve()
        _watcher_thread = threading.Thread(
            target=_watch, args=(root, interval), daemon=True)
        _watcher_thread.start()
        print('[autoreload] watching', root)
