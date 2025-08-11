import asyncio
import inspect
import re
from threading import Lock
import threading
import time
import traceback
from typing import Any, Pattern, Union
import json
import colorlog
import websockets
import concurrent
import logging
from .messenger import Messenger
from .msg import Msg
from .cmd import Cmd

class Plugin:
    def __init__(self,
                 ws_url: str,
                 token: str,
                 max_workers: int=4,
                 log_send_wss: bool=False):
        self.running = False

        self.seq = 1
        self.seq_lock = Lock()
        self.ws_url = ws_url
        self.token = token
        self.log_send_wss = log_send_wss

        self.ws = None
        self.max_workers = max_workers
        self.executor = concurrent.futures.ThreadPoolExecutor(max_workers=max_workers)

        self.handlers = {"onMsg": [], "onCmd": []}
        self.handlers_lock = Lock()

        self._setup_logging()

        self.last_heartbeat = int(time.time())
        self.total_heartbeat = 0

    def _setup_logging(self):
        self.logger = logging.getLogger(__name__)
        self.logger.setLevel(logging.DEBUG)

        for handler in self.logger.handlers[:]:
            self.logger.removeHandler(handler)

        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.DEBUG)
        console_formatter = colorlog.ColoredFormatter(
            '%(log_color)s[%(asctime)s.%(msecs)03d] %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S',
            log_colors={
                'DEBUG': 'white',
                'INFO': 'green',
                'WARNING': 'yellow',
                'ERROR': 'red',
                'CRITICAL': 'bold_red',
            }
        )
        console_handler.setFormatter(console_formatter)
        self.logger.addHandler(console_handler)

        file_handler = logging.FileHandler("app.log", encoding="utf-8")
        file_handler.setLevel(logging.DEBUG)
        file_formatter = logging.Formatter(
            '[%(asctime)s.%(msecs)03d] %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        file_handler.setFormatter(file_formatter)
        self.logger.addHandler(file_handler)

    def _format_exception(self, e: Exception) -> str:
        if isinstance(e, Exception):
            return ''.join(traceback.format_exception(type(e), e, e.__traceback__)).strip()
        return str(e)

    def log(self,
            msg: Any,
            level: int=logging.INFO,
            main_tag: str="SecPlugin",
            tag: str=None):
        if tag is None:
            level_name = logging.getLevelName(level)
            tag = f"on{level_name.capitalize()}Message"

        if msg is None:
            msg = "null"
        elif isinstance(msg, dict) or isinstance(msg, list):
            msg = json.dumps(msg, ensure_ascii=False)
        elif isinstance(msg, Messenger):
            msg = json.dumps(msg.getList(), ensure_ascii=False)
        elif not isinstance(msg, str):
            msg = str(msg)
        elif isinstance(msg, Exception):
            msg = self._format_exception(msg)

        formatted_msg = f"[{main_tag}::{tag}] {msg}"
        self.logger.log(level, formatted_msg)

    def getSeq(self, next: bool=True) -> int:
        with self.seq_lock:
            if next:
                self.seq += 1
            return self.seq

    async def _run(self) -> None:
        try:
            self.log(f"正在连接 {self.ws_url}", tag="onConnectWebSocket")
            await self.onConnectWebSocket()
        except asyncio.CancelledError:
            self.log("断开连接", tag="onDisconnectWebSocket")
        finally:
            if self.ws:
                await self.ws.close()
                self.log("关闭连接", tag="onDisconnectWebSocket")

    def start(self) -> None:
        try:
            self.running = True

            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            task = loop.create_task(self._run())

            try:
                loop.run_until_complete(task)
            except KeyboardInterrupt:
                task.cancel()
                loop.run_until_complete(task)
            finally:
                loop.close()
        except Exception as e:
            self.log(e, tag="onStartError", level=logging.ERROR)
        finally:
            self.onClose()

    async def onConnectWebSocket(self) -> None:
        if not self.running:
            return
        try:
            async with websockets.connect(self.ws_url) as websocket:
                self.ws = websocket
                self.onOpen()
                self.log("连接成功", tag="onConnectWebSocket")

                async for msg in websocket:
                    try:
                        message = json.loads(msg)
                    except json.JSONDecodeError as e:
                        self.log(e, level=logging.WARNING)
                    await self.onRecvWssHandler(message)
        except Exception as e:
            self.log(e, tag="onConnectWebSocket", level=logging.ERROR)

    def onOpen(self) -> None:
        """
        向 Secluded 发送同步上线(SyncOicq)消息包
        """
        if not self.running:
            return
        try:
            self.sendWss("SyncOicq",
                         {"pid": "com.plugin.sumaplugin", "name": "SumaPlugin", "token": self.token})
        except Exception as e:
            self.log(e, tag="onOpen", level=logging.ERROR)

    def onClose(self) -> None:
        if self.running:
            self.running = False
        self.executor.shutdown(wait=True)
        self.log("插件已关闭", tag="onClose")

    def sendHeartbeat(self):
        if not self.running:
            return
        try:
            self.sendWss("Heartbeat")
        except Exception as e:
            self.log(e, tag="sendHeartbeat", level=logging.ERROR)

    def sendWss(self,
                      cmd: str,
                      data: Union['Messenger', dict]|None=None,
                      rsp: bool=True):
        if not self.running:
            return
        if not cmd:
            return

        msg = {
            "seq": self.getSeq(),
            "cmd": cmd,
            "rsp": rsp
        }
        if data:
            if isinstance(data, dict):
                msg["data"] = data
            elif data.getList():
                msg["data"] = data.getList()

        message = json.dumps(msg)
        if self.log_send_wss:
            self.log(msg, tag="onSendWss", level=logging.DEBUG)
        try:
            loop = asyncio.get_running_loop()
            loop.create_task(self.ws.send(message))
        except RuntimeError:
            asyncio.run(self.ws.send(message))
        except Exception as e:
            self.log(e, tag="onSendWss", level=logging.ERROR)

    def sendMsg(self,
                      messenger: 'Messenger',
                      text: str) -> None:
        if not self.running:
            return
        try:
            reply = Messenger.getBaseMessenger(messenger)
            reply.add(Msg.Text, text)
            self.log(reply, tag="onSendMsg", level=logging.DEBUG)
            self.sendWss(Cmd.SendOicqMsg, reply)
        except Exception as e:
            self.log(e, tag="onSendMsg", level=logging.ERROR)

    def onMsg(self,
              msg: Union[str, Pattern]):
        compiled_pattern = re.compile(msg)
        def decorator(func):
            with self.handlers_lock:
                self.handlers["onMsg"].append((
                    compiled_pattern,
                    func
                ))
            return func
        return decorator

    async def onRecvWssHandler(self,
                               msg: dict) -> None:
        if not self.running:
            return
        cmd = msg.get("cmd")
        await self.onCmdHandler(msg)
        if cmd == Cmd.PushOicqMsg:
            messenger = Messenger(msg.get("data", []))
            if messenger.has(Msg.System):
                await self.onSystemMsgHandler(messenger)
            else:
                await self.onMsgHandler(messenger)

    async def onCmdHandler(self,
                           msg: dict) -> None:
        if not self.running:
            return
        msg_time = int(time.time())
        cmd = msg.get("cmd")
        messenger = Messenger(msg.get("data", []))
        match cmd:
            case Cmd.Response:
                await self.onRespMsgHandler(msg)
            case Cmd.Heartbeat:
                self.log("接收到心跳包", tag="onHeartbeat")
                self.log(f"距上次接收到 {msg_time - self.last_heartbeat} 秒", tag="onHeartbeat")
                self.last_heartbeat = msg_time
                self.total_heartbeat += 1
                self.log(f"总计心跳次数 {self.total_heartbeat}", tag="onHeartbeat")
                self.sendHeartbeat()
            case Cmd.PushOicqMsg:
                pass # 该类消息已被分配在 onSystemMsgHandler 和 onMsgHandler 内处理

    async def onRespMsgHandler(self,
                               msg: dict) -> None:
        if not self.running:
            return
        if isinstance(msg.get("data"), dict):
            if "status" in msg.get("data"):
                if msg.get("data").get("status"):
                    self.log("对接成功", tag="onSyncOicq")
                    return
                else:
                    self.log("对接失败", tag="onSyncOicq", level=logging.ERROR)
                    return
        self.log(f"应答包 {msg}", tag="onCmdHandler", level=logging.DEBUG)

    async def onSystemMsgHandler(self,
                                 messenger: 'Messenger') -> None:
        if not self.running:
            return
        if messenger.has(Msg.Goline) or messenger.has(Msg.Offline) or messenger.has(Msg.Heartbeat) or messenger.has(Msg.OntimeTask):
            await self.onAccountEvent(messenger)
        else:
            self.log(f"未被处理的系统消息 {messenger}", tag="onSystemMsgHandler", level=logging.WARNING)

    async def onMsgHandler(self,
                           messenger: 'Messenger') -> None:
        if not self.running:
            return
        try:
            msg_type = ""
            if messenger.has(Msg.Group):
                msg_type = Msg.Group
            elif messenger.has(Msg.Friend):
                msg_type = Msg.Friend
            elif messenger.has(Msg.Temp):
                msg_type = Msg.Temp
            elif messenger.has(Msg.Guild):
                msg_type = Msg.Guild

            text = ""
            for dat in messenger.getList():
                if Msg.Text in dat:
                    text += dat.get(Msg.Text)
                if Msg.Img in dat:
                    text += f"[图片={dat.get(Msg.Img)}]"
                if Msg.Url in dat:
                    text += f"[链接={dat.get(Msg.Url)}]"
            if not text:
                text = "该消息类型暂不支持显示，请切换QQ查看"
                self.log(messenger, tag="onUnsupportedMsg", level=logging.WARNING)
            else:
                self.log(f"{messenger.get("UinName")}: {text}", tag=f"on{msg_type.capitalize()}Msg", level=logging.DEBUG)

            await self.doMsgHandler(messenger)
        except Exception as e:
            self.log(e, tag="onMsgHandler", level=logging.ERROR)

    async def doMsgHandler(self,
                           messenger: 'Messenger') -> None:
        if not self.running:
            return
        start_time = int(round(time.time() * 1000))
        print_time = False
        try:
            for regex, callback in self.handlers["onMsg"]:
                match = re.fullmatch(regex, messenger.get(Msg.Text))
                if match:
                    sig = inspect.signature(callback)
                    required_count = sum(
                        1 for param in sig.parameters.values()
                        if param.default == inspect.Parameter.empty
                        and param.kind in (param.POSITIONAL_ONLY, param.POSITIONAL_OR_KEYWORD)
                    )
                    loop = asyncio.get_running_loop()
                    if required_count == 1:
                        if asyncio.iscoroutinefunction(callback):
                            await callback(messenger)
                        else:
                            await loop.run_in_executor(self.executor, callback, messenger)
                    elif required_count == 2:
                        if asyncio.iscoroutinefunction(callback):
                            await callback(messenger, match)
                        else:
                            await loop.run_in_executor(self.executor, callback, messenger, match)
                    print_time = True
        except Exception as e:
            self.log(e, tag="doMsgHandler", level=logging.ERROR)
        if print_time:
            end_time = int(round(time.time() * 1000))
            self.log(f"消息处理耗时 {(end_time - start_time) / 1000} 秒", tag="doMsgHandler")

    async def onAccountEvent(self,
                             messenger: 'Messenger') -> None:
        if not self.running:
            return
        log_msg = f"{messenger.get(Msg.Account)} "
        non_set = log_msg
        if messenger.has(Msg.Goline):
            log_msg += f"账号状态变更为上线({messenger.get(Msg.GolineMode)})"
        elif messenger.has(Msg.Offline):
            log_msg += "账号状态变更为下线"
        elif messenger.has(Msg.Heartbeat):
            log_msg += "账号发生心跳"
        elif messenger.has(Msg.OntimeTask):
            log_msg += "账号触发定时任务"
        if log_msg and log_msg != non_set:
            self.log(log_msg, tag="onAccountEvent", level=logging.DEBUG)
