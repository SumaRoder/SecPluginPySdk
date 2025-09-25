import json
import logging
import traceback
from logging.handlers import QueueHandler, QueueListener
from queue import Queue
import colorlog
from .messenger import Messenger

_console_handler = logging.StreamHandler()
_console_handler.setLevel(logging.DEBUG)
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

_file_handler = logging.FileHandler("app.log", encoding="utf-8")
_file_handler.setLevel(logging.DEBUG)
_file_handler.setFormatter(logging.Formatter(
    '[%(asctime)s.%(msecs)03d] %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'))

class Logger:
    _listener: QueueListener = None

    def __init__(self, name: str = __name__):
        self.log_queue = Queue()
        self.logger = logging.getLogger(name)
        self.logger.setLevel(logging.DEBUG)

        if Logger._listener is None:
            Logger._listener = QueueListener(
                self.log_queue, _console_handler, _file_handler)
            Logger._listener.start()
        self.logger.addHandler(QueueHandler(self.log_queue))

    @staticmethod
    def _format_exception(e: Exception) -> str:
        return ''.join(traceback.format_exception(type(e), e, e.__traceback__)).strip()

    def log(self, *msg, level=logging.INFO, main_tag="SecPlugin", tag=None):
        if tag is None:
            tag = f"on{logging.getLevelName(level).capitalize()}Message"

        pieces = []
        for m in msg:
            if m is None:
                pieces.append("null")
            elif isinstance(m, (dict, list)):
                pieces.append(json.dumps(m, ensure_ascii=False))
            elif isinstance(m, Messenger):
                pieces.append(json.dumps(m.getList(), ensure_ascii=False))
            elif isinstance(m, Exception):
                pieces.append(self._format_exception(m))
            else:
                pieces.append(str(m))

        self.logger.log(level, f"[{main_tag}::{tag}] {' '.join(pieces)}")

    def info(self, *msg, main_tag="SecPlugin", tag=None):
        self.log(*msg, level=logging.INFO, main_tag=main_tag, tag=tag)

    def error(self, *msg, main_tag="SecPlugin", tag=None):
        self.log(*msg, level=logging.ERROR, main_tag=main_tag, tag=tag)

    def warning(self, *msg, main_tag="SecPlugin", tag=None):
        self.log(*msg, level=logging.WARNING, main_tag=main_tag, tag=tag)

    def debug(self, *msg, main_tag="SecPlugin", tag=None):
        self.log(*msg, level=logging.DEBUG, main_tag=main_tag, tag=tag)
