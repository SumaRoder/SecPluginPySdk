import json
import logging
import traceback
from typing import Optional, Self, TYPE_CHECKING
from logging.handlers import QueueHandler, QueueListener
from queue import Queue
import importlib
import types

try:
    colorlog: Optional[types.ModuleType] = importlib.import_module("colorlog")
except Exception:
    colorlog = None

from .messenger import Messenger
_console_handler = logging.StreamHandler()
_console_handler.setLevel(logging.DEBUG)

if colorlog:
    _console_handler.setFormatter(colorlog.ColoredFormatter(
        '%(log_color)s[%(asctime)s.%(msecs)03d] %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S',
        log_colors={
            'DEBUG': 'white',
            'INFO': 'green',
            'WARNING': 'yellow',
            'ERROR': 'red',
            'CRITICAL': 'bold_red',
        }))
else:
    _console_handler.setFormatter(logging.Formatter(
        '[%(asctime)s.%(msecs)03d] %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'))

def _create_file_handler(path: str) -> logging.FileHandler:
     handler = logging.FileHandler(path, encoding="utf-8")
     handler.setLevel(logging.DEBUG)
     handler.setFormatter(logging.Formatter(
         '[%(asctime)s.%(msecs)03d] %(message)s',
         datefmt='%Y-%m-%d %H:%M:%S'))
     return handler

import threading
import weakref

class Logger:
    _lock = threading.Lock()
    _listener: Optional[QueueListener] = None
    _queue: Optional[Queue] = None
    _instances: weakref.WeakValueDictionary[str, "Logger"] = weakref.WeakValueDictionary()
    
    def __new__(cls, name: str = __name__, path: str = "app.log"):
        with cls._lock:
            if name in cls._instances:
                return cls._instances[name]
            instance = super().__new__(cls)
            cls._instances[name] = instance
            return instance
    
    def __init__(self, name: str = __name__, path: str = "app.log"):
        if hasattr(self, '_initialized'):
            return
        self._initialized = True
        
        with Logger._lock:
            if Logger._queue is None:
                Logger._queue = Queue()
                Logger._listener = QueueListener(
                    Logger._queue, 
                    _console_handler, 
                    _create_file_handler(path)
                )
                Logger._listener.start()
        
        self.logger = logging.getLogger(name)
        self.logger.setLevel(logging.DEBUG)
        self.logger.addHandler(QueueHandler(Logger._queue))
    
    @classmethod
    def shutdown(cls):
        if cls._listener:
            cls._listener.stop()
            cls._listener = None
    
    @staticmethod
    def _format_exception(e: Exception) -> str:
        return ''.join(traceback.format_exception(type(e), e, e.__traceback__)).strip()
    
    @staticmethod
    def get_logger(name: str) -> Self:
        pass

    def log(self, *msg, level=logging.INFO, main_tag="SecPlugin", tag=None, end=" "):
        if tag is None:
            tag = f"on{logging.getLevelName(level).capitalize()}Message"

        pieces = []
        for m in msg:
            if m is None:
                pieces.append("null")
            elif isinstance(m, (dict, list)):
                pieces.append(json.dumps(m, ensure_ascii=False))
            elif isinstance(m, Messenger):
                pieces.append(json.dumps(m.get_list(), ensure_ascii=False))
            elif isinstance(m, Exception):
                pieces.append(self._format_exception(m))
            else:
                pieces.append(str(m))

        self.logger.log(level, f"[{main_tag}::{tag}] {end.join(pieces)}")

    def info(self, *msg, main_tag="SecPlugin", tag=None):
        self.log(*msg, level=logging.INFO, main_tag=main_tag, tag=tag)

    def error(self, *msg, main_tag="SecPlugin", tag=None):
        self.log(*msg, level=logging.ERROR, main_tag=main_tag, tag=tag)

    def warning(self, *msg, main_tag="SecPlugin", tag=None):
        self.log(*msg, level=logging.WARNING, main_tag=main_tag, tag=tag)

    def debug(self, *msg, main_tag="SecPlugin", tag=None):
        self.log(*msg, level=logging.DEBUG, main_tag=main_tag, tag=tag)
