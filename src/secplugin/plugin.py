import json
import asyncio
import websockets
import re
import inspect
import random
import time
import threading
from queue import Queue

from .cmd import Cmd
from .messenger import Messenger
from .msg import Msg
from .logger import Logger
from .reload import HotReload
from .sender import Sender

class Plugin:
    def __init__(self,
                 url: str | None = None,
                 pid: str | None = None,
                 name: str | None = None,
                 token: str | None = None,
                 *,
                 max_workers: int = 4,
                 allow_thread: bool = False,
                 reload: bool = True,
                 max_retry: int = 5) -> None:
        self._ws_url: str | None = url
        self._reload = reload
        self._max_retry = max_retry
        self._allow_thread = allow_thread
        self._max_workers = max_workers
        
        self._plugin_pid = pid
        self._plugin_name = name
        self._plugin_token = token
        
        self._running = False
        self._ws = None
        self._seq = 0
        self._pending_responses: dict[int, asyncio.Future] = {}
        self._executor: ThreadPoolExecutor | None = None
        self._semaphore: asyncio.Semaphore | None = None
        self._logger: Logger | None = None
        self._sender: Sender | None = None
        self._on_msg_regex_handlers = {}
    
    async def main(self):
        if self._reload:
            try:
                HotReload.enable(self._logger)
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
                    await self.on_create(websocket)
                    msg_task = asyncio.create_task(self.on_msg_handler(websocket))
                    await self.ready(websocket)
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
    
    def get_sender(self):
        if not self._sender:
            self._sender = Sender(self)
        return self._sender
    
    def running(self):
        return self._running
    
    def closed(self):
        return not self._running
    
    async def ready(self, websocket):
        self._running = True
        resp = await self.send_ws_msg(Cmd.SyncOicq, {"pid": self._plugin_pid, "name": self._plugin_name, "token": self._plugin_token})
        if resp and resp.get("data").get("status"):
            self._logger.info(f"对接成功", tag="SyncOicq")
        else:
            self._logger.error(f"对接失败", tag="SyncOicq")
    
    async def on_create(self, websocket):
        pass
    
    async def on_msg_error(self, message):
        pass
    
    async def close(self):
        if self._reload:
            HotReload.disable()
        if self._allow_thread:
            self.executor.shutdown(wait=False)
        for seq, future in list(self._pending_responses.items()):
            if not future.done():
                future.cancel()
        self._pending_responses.clear()
        self._running = False
    
    async def on_close(self):
        pass
    
    async def send_ws_msg(self, cmd, data, rsp=True, timeout: float = 10) -> dict | None:
        if not self._running:
            return None
        
        payload = {
            "cmd": cmd,
            "rsp": rsp
        }
        if data:
            if isinstance(data, dict):
                payload["data"] = data
            elif isinstance(data, Messenger):
                payload["data"] = data.get_list()
        
        self._seq += 1
        seq = self._seq
        payload["seq"] = seq
        
        await self._ws.send(json.dumps(payload))
        
        if rsp:
            future = asyncio.get_event_loop().create_future()
            self._pending_responses[seq] = future
            
            try:
                response = await asyncio.wait_for(future, timeout=timeout)
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
    
    async def on_msg_handler(self, websocket):
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
                match cmd:
                    case Cmd.Response:
                        await self.on_resp_msg_handler(msg)
                    case Cmd.PushOicqMsg:
                        await self.do_msg_handler(messenger)
    
    @staticmethod
    def get_function_required_params_num(callback):
        sig = inspect.signature(callback)
        if any(p.kind in (p.VAR_POSITIONAL, p.VAR_KEYWORD) for p in sig.parameters.values()):
            raise TypeError(f"Function({callback.__name__}) cannot use *args or **kwargs")
        return sum(
            1 for param in sig.parameters.values()
            if param.default == inspect.Parameter.empty
            and param.kind in (param.POSITIONAL_ONLY, param.POSITIONAL_OR_KEYWORD)
        )
    
    async def on_resp_msg_handler(self, message):
        seq = message.get("seq")
        future = self._pending_responses.get(seq)
        if future is None:
            return
        if not future.done():
            future.set_result(message)
        else:
            self._logger.debug(f"Future for seq {seq} already done", tag="resp")
    
    async def do_msg_handler(self, messenger):
        text = messenger.get(Msg.Text)
        async with self._semaphore:
            for regex, (handler, rn) in self._on_msg_regex_handlers.items():
                matches = re.fullmatch(regex, text)
                if matches:
                    if asyncio.iscoroutinefunction(handler):
                        if rn == 1:
                            asyncio.create_task(handler(messenger))
                        elif rn == 2:
                            asyncio.create_task(handler(messenger, matches))
                    else:
                        if not self._allow_thread:
                            raise RuntimeError("Sync function was not allowed (allow_thread=False)")
                        loop = asyncio.get_running_loop()
                        if rn == 1:
                            await loop.run_in_executor(self._executor, handler, messenger)
                        elif rn == 2:
                            await loop.run_in_executor(self._executor, handler, messenger, matches)
    
    def run(self,
            url: str | None = None,
            pid: str | None = None,
            name: str | None = None,
            token: str | None = None,
            *,
            max_workers: int | None = None,
            allow_thread: bool | None = None,
            reload: bool | None = None,
            max_retry: int | None = None) -> None:
        self._ws_url = url or self._ws_url
        self._max_workers = max_workers if max_workers is not None else self._max_workers
        self._allow_thread = allow_thread if allow_thread is not None else self._allow_thread
        self._reload = reload if reload is not None else self._reload
        self._max_retry = max_retry if max_retry is not None else self._max_retry
        
        self._plugin_pid = pid
        self._plugin_name = name
        self._plugin_token = token
        
        self._logger = Logger()
        if self._allow_thread:
            self._executor = ThreadPoolExecutor(max_workers=self._max_workers)
        self._semaphore = asyncio.Semaphore(self._max_workers)

        try:
            asyncio.run(self.main())
        except KeyboardInterrupt:
            self._logger.info("已关闭", tag="close")
        except Exception as e:
            self._logger.error("异常：", e, tag="error")
