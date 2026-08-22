from __future__ import annotations
from concurrent.futures import ThreadPoolExecutor
import json
import asyncio
from typing import Any, Callable, Optional, TYPE_CHECKING
import websockets
import re
import inspect
import random
from .cmd import Cmd
from .messenger import Messenger
from .msg import Msg
from .logger import Logger
from .reload import HotReload
from .sender import Sender
if TYPE_CHECKING:
    from websockets import ClientConnection  # type: ignore

from dataclasses import dataclass
from enum import Enum, auto

class ConcurrencyMode(Enum):
    SYNC = auto()
    ASYNC = auto()
    POOL = auto()

@dataclass
class HandlerConfig:
    mode: ConcurrencyMode = ConcurrencyMode.ASYNC
    max_concurrent: int = 0
    ordered: bool = False

class Plugin:
    def __init__(self,
                 url: str = "ws://127.0.0.1:24804",
                 pid: str = "io.github.sumaroder.secplugin",
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
        self._ws: Optional[ClientConnection] = None
        self._seq: int = 0
        self._pending_responses: dict[int, asyncio.Future] = {}
        self._executor: Optional[ThreadPoolExecutor] = None
        if self._allow_thread:
            self._executor = ThreadPoolExecutor(max_workers=self._max_workers)
        self._handler_semaphores: dict[str, asyncio.Semaphore] = {}
        self._ordered_queues: dict[str, asyncio.Queue] = {}
        self._ordered_workers: dict[str, asyncio.Task] = {}
        self._on_msg_handler_lock: asyncio.Lock = asyncio.Lock()
        self._on_send_wait_lock: asyncio.Lock = asyncio.Lock()
        self._log_path: Optional[str] = log_path
        if log_path is not None:
            self._logger: Logger = Logger(name = __name__, path = log_path)
        self._sender: Optional[Sender] = None
        self._on_msg_regex_handlers: dict[re.Pattern, tuple[Callable[..., Any], int]] = {}
        self._on_all_msg_handlers: list[tuple[Callable[..., Any], int]] = []
        self._local_send_wait_timeout: float = 15
    
    async def main(self):
        if self._reload:
            try:
                HotReload.enable()
                self._logger.info("热重载服务启动成功", tag="reload")
            except Exception as e:
                self._logger.error("热重载服务启动失败", e, tag="reload")
        
        self._logger.debug(f"开始连接 {self._ws_url}", tag="connect")
        retry_cnt = 0
        while retry_cnt <= self._max_retry:
            self._ws = None
            try:
                async with websockets.connect(self._ws_url, additional_headers={"Authorization": f"Bearer {self._plugin_token}"}) as websocket:
                    retry_cnt = 0
                    self._ws = websocket
                    self._logger.info(f"连接成功 {self._ws_url}", tag="connect")
                    
                    msg_handler_task = asyncio.create_task(
                        self.on_msg_handler(websocket)
                    )
                    
                    async with self._on_msg_handler_lock:
                        try:
                            await self.ready()
                            await self.on_create(websocket)
                        except RuntimeError as e:
                            msg_handler_task.cancel()
                            raise e
                    
                    try:
                        await msg_handler_task
                    except asyncio.CancelledError:
                        raise
            
            except (KeyboardInterrupt, asyncio.CancelledError):
                await self.on_close()
                await self.close()
                raise
            
            except (websockets.exceptions.ConnectionClosedError, websockets.exceptions.ConnectionClosed,
                    websockets.exceptions.InvalidMessage, websockets.exceptions.InvalidStatus,
                    OSError, asyncio.TimeoutError) as e:
                retry_cnt += 1
                wait = min(2 ** retry_cnt + random.random(), 60)
                self._logger.error(f"连接异常，{wait:.1f}s 后第 {retry_cnt} 次重连\n", e, tag="connect")
                await asyncio.sleep(wait)
            
            except Exception as e:
                self._logger.error("其他异常", e, tag="error")
                raise
            
            finally:
                if self._ws:
                    try:
                        await self._ws.close()
                    except Exception:
                        pass
                    self._ws = None
    
    def on_msg(self, regex=None, *,
               mode: ConcurrencyMode = ConcurrencyMode.ASYNC,
               max_concurrent: int = 0,
               ordered: bool = False
    ):
        config = HandlerConfig(
            mode=mode,
            max_concurrent=max_concurrent,
            ordered=ordered
        )
        
        if regex:
            compiled_pattern = re.compile(regex)
            if compiled_pattern in self._on_msg_regex_handlers:
                raise AttributeError("Repeat regex")
            
            def decorator(func):
                if not asyncio.iscoroutinefunction(func) and not self._allow_thread:
                    raise TypeError("Function must be async, or set `allow_thread` to `True`")
                rn = Plugin.get_function_required_params_num(func)
                self._on_msg_regex_handlers[compiled_pattern] = (func, rn, config)
                return func
            return decorator
        
        def decorator(func):
            if not asyncio.iscoroutinefunction(func) and not self._allow_thread:
                raise TypeError("Function must be async, or set `allow_thread` to `True`")
            rn = Plugin.get_function_required_params_num(func)
            self._on_all_msg_handlers.append((func, rn, config))
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
    
    async def on_create(self, websocket: ClientConnection):
        pass
    
    async def on_msg_error(self, message: str):
        pass
    
    async def close(self, timeout: float=10.0):
        self._logger.error("正在关闭", tag="close")
        self._running = False
        
        if self._reload:
            HotReload.disable()
        
        if self._allow_thread and self._executor is not None:
            self._executor.shutdown(wait=self._running)
        
        for seq, future in list(self._pending_responses.items()):
            if not future.done():
                future.cancel()
        self._pending_responses.clear()
        
        tasks = [t for t in asyncio.all_tasks() if t is not asyncio.current_task()]
        for task in tasks:
            task.cancel()
        if tasks:
            try:
                await asyncio.gather(*tasks, return_exceptions=True)
            except asyncio.CancelledError:
                pass
        
        for handler_id, worker in list(self._handler_ordered_workers.items()):
            if not worker.done():
                worker.cancel()
        self._handler_ordered_workers.clear()
        self._handler_ordered_queues.clear()
        self._handler_semaphores.clear()
        
        self._logger.info("已关闭", tag="close")
        if self._logger:
            self._logger.shutdown()
    
    async def on_close(self):
        pass
    
    async def send_ws_msg(self,
        cmd: Cmd | str,
        data: Optional[dict | Messenger] = None,
        rsp: bool = False,
        timeout: Optional[float] = None
    ) -> Optional[dict]:
        if not self._running:
            return
        if self._ws is None:
            raise RuntimeError("WebSocket is not connected")
        
        cmd_value = cmd.value if isinstance(cmd, Cmd) else cmd
        payload = { "cmd": cmd_value }
        if data is not None:
            if isinstance(data, Messenger):
                payload["data"] = data.get_list()
            else:
                payload["data"] = dict(data)
        if rsp:
            payload["rsp"] = True
            self._seq += 1
            seq = self._seq
            payload["seq"] = seq
        
        await self._ws.send(json.dumps(payload, ensure_ascii=False))
        if rsp:
            if not timeout:
                timeout = self._local_send_wait_timeout
            async with self._on_send_wait_lock:
                future = asyncio.get_event_loop().create_future()
                self._pending_responses[seq] = future
                
                try:
                    response = await asyncio.wait_for(future, timeout=timeout)
                    return response
                except asyncio.TimeoutError as e:
                    self._pending_responses.pop(seq, None)
                    raise asyncio.TimeoutError(f"Response timeout for seq={seq}") from e
                except asyncio.CancelledError as e:
                    self._pending_responses.pop(seq, None)
                    raise asyncio.CancelledError(f"Response future for seq={seq} was cancelled") from e
                finally:
                    self._pending_responses.pop(seq, None)
    
    async def on_unsupported_msg_handler(self, message: str):
        pass
    
    async def on_msg_handler(self, websocket: ClientConnection):
        try:
            async for raw_message in websocket:
                message: str
                if isinstance(raw_message, bytes):
                    message = raw_message.decode("utf-8")
                else:
                    message = raw_message
                
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
                    elif cmd == Cmd.Heartbeat:
                        await self.on_heartbeat_msg_handler()
        except asyncio.CancelledError:
            raise
        except (websockets.exceptions.ConnectionClosedError, websockets.exceptions.ConnectionClosed) as e:
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
        
        tasks: list[asyncio.Task] = []
        for (handler, rn, config) in self._on_all_msg_handlers:
            task = await self._dispatch_task(handler, rn, messenger, None, config)
            if task is not None:
                tasks.append(task)
        for regex, (handler, rn, config) in self._on_msg_regex_handlers.items():
            matches = re.fullmatch(regex, text)
            if matches:
                task = await self._dispatch_task(handler, rn, messenger, matches, config)
                if task is not None:
                    tasks.append(task)
        
        if tasks:
            results = await asyncio.gather(*tasks, return_exceptions=True)
            for i, result in enumerate(results):
                if isinstance(result, Exception):
                    self._logger.error(f"Handler {tasks[i].get_name()} raised exception", result, tag="msg_handler")
    
    async def _dispatch_task(self,
        handler: Callable[..., Any],
        rn: int,
        messenger: Messenger,
        matches: Optional[re.Match] = None,
        config: Optional[HandlerConfig] = None
    ) -> Optional[asyncio.Task]:
        config = config or HandlerConfig()
        
        if asyncio.iscoroutinefunction(handler):
            if rn == 0:
                coro = handler()
            elif rn == 1:
                coro = handler(messenger)
            else:
                coro = handler(messenger, matches)
        else:
            if not self._allow_thread:
                raise RuntimeError("Sync function was not allowed (allow_thread=False)")
            if rn == 0:
                fn = lambda: handler()
            elif rn == 1:
                fn = lambda: handler(messenger)
            else:
                fn = lambda: handler(messenger, matches)
        
        handler_id = id(handler)
        if config.ordered:
            if handler_id not in self._handler_ordered_workers or self._handler_ordered_workers[handler_id].done():
                self._handler_ordered_queues[handler_id] = asyncio.Queue()
                self._handler_ordered_workers[handler_id] = asyncio.create_task(
                    self._ordered_worker(handler_id, handler, config),
                    name=f"ordered_worker_{handler.__name__}"
                )
            future = asyncio.get_event_loop().create_future()
            await self._handler_ordered_queues[handler_id].put(
                (
                    coro if asyncio.iscoroutinefunction(handler) else fn,
                    future,
                    asyncio.iscoroutinefunction(handler)
                )
            )
            async def _wait_ordered():
                return await future
            return asyncio.create_task(_wait_ordered(), name=f"ordered_{handler.__name__}")
        if config.mode == ConcurrencyMode.POOL and config.max_concurrent > 0:
            sema = self._handler_semaphores.get(handler_id, None)
            if sema is None:
                sema = asyncio.Semaphore(config.max_concurrent)
                self._handler_semaphores[handler_id] = sema
            async def _pooled():
                async with sema:
                    if asyncio.iscoroutinefunction(handler):
                        return await coro
                    else:
                        loop = asyncio.get_running_loop()
                        return await loop.run_in_executor(self._executor, fn)
            return asyncio.create_task(_pooled(), name=f"pooled_{handler.__name__}")
        if config.mode == ConcurrencyMode.SYNC:
            if asyncio.iscoroutinefunction(handler):
                return await coro
            else:
                loop = asyncio.get_running_loop()
                return await loop.run_in_executor(self._executor, fn)
            return None
        loop = asyncio.get_running_loop()
        if asyncio.iscoroutinefunction(handler):
            return loop.create_task(coro, name=handler.__name__)
        else:
            return loop.run_in_executor(self._executor, fn) # type: ignore
    
    async def _ordered_worker(self,
        handler_id: int,
        handler: Callable[..., Any],
        config: HandlerConfig
    ):
        queue = self._handler_ordered_queues[handler_id]
        while True:
            try:
                item, future, is_coro = await queue.get()
                try:
                    if is_coro:
                        result = await item
                    else:
                        loop = asyncio.get_running_loop()
                        result = await loop.run_in_executor(self._executor, item)
                    if not future.done():
                        future.set_result(result)
                except Exception as e:
                    if not future.done():
                        future.set_exception(e)
                finally:
                    queue.task_done()
            except asyncio.CancelledError:
                while not queue.empty():
                    try:
                        _, fut, _ = queue.get_nowait()
                        if not fut.done():
                            fut.cancel()
                    except asyncio.QueueEmpty:
                        break
                raise
    
    async def on_heartbeat_msg_handler(self):
        await self.send_ws_msg(Cmd.Heartbeat)
    
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
        
        if self._allow_thread and self._executor is None:
            self._executor = ThreadPoolExecutor(max_workers=self._max_workers)
        if log_path is not None or not hasattr(self, '_logger') or not self._logger:
            self._logger = Logger(name = f"plugin_logger_{self._plugin_pid.replace('.', '_')}", path = log_path or self._log_path or "app.log")

        try:
            asyncio.run(self.main())
        except (KeyboardInterrupt, asyncio.CancelledError):
            pass
        except Exception as e:
            self._logger.error("异常：", e, tag="error")
        finally:
            self._running = False
