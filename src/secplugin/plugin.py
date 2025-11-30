from __future__ import annotations
from concurrent.futures import ThreadPoolExecutor
import json
import asyncio
from typing import Any, Callable, Optional, TYPE_CHECKING
try:
    import websockets # type: ignore
except ImportError:
    raise ImportError("Missing dependency 'websockets'. Please install it via 'pip install websockets'.")

from websockets.exceptions import ConnectionClosedError
if TYPE_CHECKING:
    try:
        # websockets>=10
        from websockets.legacy.client import WebSocketClientProtocol  # type: ignore
    except Exception:
        # older versions
        from websockets.client import WebSocketClientProtocol  # type: ignore

import re
import inspect
import random

from .cmd import Cmd
from .messenger import Messenger
from .msg import Msg
from .logger import Logger
from .reload import HotReload
from .sender import Sender

class Plugin:
    def __init__(self,
                 url: str = "ws://127.0.0.1:24804",
                 pid: str = "com.sumaroder.plugin",
                 name: str = "SecPlugin",
                 token: str = "SecretToken",
                 *,
                 max_workers: int = 4,
                 allow_thread: bool = False,
                 reload: bool = True,
                 max_retry: int = 5,
                 log_path: Optional[str] = "app.log"
    ) -> None:
        self._reload: bool = reload
        self._max_retry: int = max_retry
        self._allow_thread: bool = allow_thread
        self._max_workers: int = max_workers

        self._ws_url: str = url
        self._plugin_pid: str = pid
        self._plugin_name: str = name
        self._plugin_token: str = token
        
        self._running: bool = False
        self._ws: Optional[WebSocketClientProtocol] = None
        self._seq: int = 0
        self._pending_responses: dict[int, asyncio.Future] = {}
        self._executor: Optional[ThreadPoolExecutor] = None
        self._semaphore: asyncio.Semaphore = asyncio.Semaphore(self._max_workers)
        self._on_msg_handler_lock: asyncio.Lock = asyncio.Lock()
        self._on_send_wait_lock: asyncio.Lock = asyncio.Lock()
        self._log_path: Optional[str] = log_path
        if log_path is not None:
            self._logger: Logger = Logger(name = __name__, path = log_path)
        self._sender: Optional[Sender] = None
        self._on_msg_regex_handlers: dict[re.Pattern, tuple[Callable[..., Any], int]] = {}
        self._local_send_wait_timeout: float = 15
    
    async def main(self):
        if self._reload:
            try:
                HotReload.enable()
                self._logger.info(f"热重载服务启动成功", tag="reload")
            except Exception as e:
                self._logger.error(f"热重载服务启动失败", e, tag="reload")
        self._logger.debug(f"开始连接 {self._ws_url}", tag="connect")
        retry_cnt = 0
        while retry_cnt <= self._max_retry:
            try:
                async with websockets.connect(self._ws_url) as websocket:
                    retry_cnt = 0
                    self._ws = websocket
                    self._logger.info(f"连接成功 {self._ws_url}", tag="connect")
                    async with self._on_msg_handler_lock:
                        try:
                            asyncio.create_task(self.on_msg_handler(websocket))
                        except RuntimeError as e:
                            raise e
                    await self.ready()
                    await self.on_create(websocket)
                    while True:
                        await asyncio.sleep(1)
            except Exception as e:
                retry_cnt += 1
                wait = min(2 ** retry_cnt + random.random(), 60)
                self._logger.error(f"连接异常，{wait:.1f}s 后第 {retry_cnt} 次重连\n", e, tag="connect")
                await asyncio.sleep(wait)
            finally:
                await self.close()
                await self.on_close()
    
    def on_msg(self, regex):
        compiled_pattern = re.compile(regex)
        if compiled_pattern in self._on_msg_regex_handlers:
            raise AttributeError("Repeat regex")
        def decorator(func):
            if not asyncio.iscoroutinefunction(func) and not self._allow_thread:
                raise TypeError("Function must be async, or set `allow_thread` to `True`")
            rn = Plugin.get_function_required_params_num(func)
            self._on_msg_regex_handlers[compiled_pattern] = (func, rn)
            return func
        return decorator
    
    def get_logger(self) -> Logger:
        if not self._logger:
            self._logger = Logger()
        return self._logger

    def get_local_send_wait_timeout(self) -> float:
        return self._local_send_wait_timeout

    def set_local_send_wait_timeout(self, timeout: float) -> None:
        self._local_send_wait_timeout = timeout

    def get_sender(self) -> Sender:
        if not self._sender:
            self._sender = Sender(self)
        return self._sender
    
    def running(self) -> bool:
        return self._running
    
    def closed(self) -> bool:
        return not self._running
    
    async def ready(self):
        self._running = True
        resp = await self.send_ws_msg(Cmd.SyncOicq, {"pid": self._plugin_pid, "name": self._plugin_name, "token": self._plugin_token})
        if resp is not None and resp \
            and resp.get("data", None) is not None and resp.get("data", {}) \
            and resp.get("data", {}).get("status", False):
            self._logger.info(f"对接成功", tag="SyncOicq")
        else:
            self._logger.error(f"对接失败", tag="SyncOicq")
    
    async def on_create(self, websocket: WebSocketClientProtocol):
        pass
    
    async def on_msg_error(self, message: str):
        pass
    
    async def close(self):
        if self._reload:
            HotReload.disable()
        if self._allow_thread and self._executor is not None:
            self._executor.shutdown(wait = False)
        for seq, future in list(self._pending_responses.items()):
            if not future.done():
                future.cancel()
        self._pending_responses.clear()
        for task in asyncio.all_tasks():
            if task is not asyncio.current_task():
                task.cancel()
        self._running = False
    
    async def on_close(self):
        pass
    
    async def send_ws_msg(self, cmd: Cmd | str, data: dict | Messenger, rsp: bool = True, timeout: float = 0) -> Optional[dict]:
        if not self._running:
            return
        
        cmd_value = cmd.value if isinstance(cmd, Cmd) else cmd

        payload = {
            "cmd": cmd_value,
            "rsp": rsp
        }
        if data:   
            if isinstance(data, Messenger):
                payload["data"] = data.get_list()
            else:
                payload["data"] = data
        
        self._seq += 1
        seq = self._seq
        payload["seq"] = seq
        
        if self._ws is None:
            raise RuntimeError("WebSocket is not connected")
        await self._ws.send(json.dumps(payload))
        
        if rsp:
            if not timeout:
                timeout = self._local_send_wait_timeout
            async with self._on_send_wait_lock:
                future = asyncio.get_event_loop().create_future()
                self._pending_responses[seq] = future
                
                try:
                    response = await asyncio.wait_for(future, timeout = timeout)
                    return response
                except asyncio.TimeoutError:
                    self._pending_responses.pop(seq, None)
                    raise TimeoutError(f"Response timeout for seq={seq}")
                except asyncio.CancelledError:
                    self._pending_responses.pop(seq, None)
                    raise
                finally:
                    self._pending_responses.pop(seq, None)
    
    async def on_unsupported_msg_handler(self, message: str):
        pass
    
    async def on_msg_handler(self, websocket: WebSocketClientProtocol):
        try:
            async for message in websocket:
                try:
                    msg = json.loads(message)
                except json.JSONDecodeError:
                    msg = None
                    await self.on_msg_error(message)
                    await self.on_unsupported_msg_handler(message)
                if msg:
                    cmd = msg.get("cmd", None)
                    messenger = Messenger(msg.get("data", []))
                    self._logger.debug(message, tag="onMsg")
                    if cmd == Cmd.Response:
                        await self.on_resp_msg_handler(msg)
                    elif cmd == Cmd.PushOicqMsg:
                        await self.do_msg_handler(messenger)
        except ConnectionClosedError as e:
            raise RuntimeError("WebSocket connection closed") from e
    
    @staticmethod
    def get_function_required_params_num(callback: Callable[..., Any]) -> int:
        sig = inspect.signature(callback)
        if any(p.kind in (p.VAR_POSITIONAL, p.VAR_KEYWORD) for p in sig.parameters.values()):
            raise TypeError(f"Function({callback.__name__}) cannot use *args or **kwargs")
        return sum(
            1 for param in sig.parameters.values()
            if param.default == inspect.Parameter.empty
            and param.kind in (param.POSITIONAL_ONLY, param.POSITIONAL_OR_KEYWORD)
        )
    
    async def on_resp_msg_handler(self, message: dict):
        seq = message.get("seq")
        if seq is not None and seq in self._pending_responses:
            future = self._pending_responses.get(seq)
            if future is None:
                return
            if not future.done():
                future.set_result(message)
            else:
                self._logger.debug(f"Future for seq {seq} already done", tag="resp")
    
    async def do_msg_handler(self, messenger: Messenger):
        text = messenger.get_msg(Msg.Text)
        async with self._semaphore:
            for regex, (handler, rn) in self._on_msg_regex_handlers.items():
                matches = re.fullmatch(regex, text)
                if matches:
                    if asyncio.iscoroutinefunction(handler):
                        if rn == 1:
                            task = asyncio.create_task(handler(messenger))
                        elif rn == 2:
                            task = asyncio.create_task(handler(messenger, matches))
                    else:
                        if not self._allow_thread:
                            raise RuntimeError("Sync function was not allowed (allow_thread=False)")
                        loop = asyncio.get_running_loop()
                        if rn == 1:
                            await loop.run_in_executor(self._executor, handler, messenger)
                        elif rn == 2:
                            await loop.run_in_executor(self._executor, handler, messenger, matches)
    
    def run(self,
            url: Optional[str] = None,
            pid: Optional[str] = None,
            name: Optional[str] = None,
            token: Optional[str] = None,
            *,
            max_workers: Optional[int] = None,
            allow_thread: Optional[bool] = None,
            reload: Optional[bool] = None,
            max_retry: Optional[int] = None,
            log_path: Optional[str] = None
    ) -> None:
        self._ws_url = url or self._ws_url
        if max_workers is not None:
            self._max_workers = max_workers
            self._semaphore = asyncio.Semaphore(self._max_workers)
        self._allow_thread = allow_thread or self._allow_thread
        self._reload = reload or self._reload
        self._max_retry = max_retry or self._max_retry
        
        self._plugin_pid = pid or self._plugin_pid
        self._plugin_name = name or self._plugin_name
        self._plugin_token = token or self._plugin_token
        
        if self._allow_thread:
            self._executor = ThreadPoolExecutor(max_workers=self._max_workers)
        if log_path is not None or not hasattr(self, '_logger') or not self._logger:
            self._logger = Logger(name = __name__, path = log_path or self._log_path or "app.log")

        try:
            asyncio.run(self.main())
        except KeyboardInterrupt:
            self._logger.info("已关闭", tag="close")
        except Exception as e:
            self._logger.error("异常：", e, tag="error")
