import asyncio
import concurrent.futures
import json
import re
import websockets
from typing import Callable, Dict, List, Pattern, Tuple, Optional, Any, Union, Coroutine

class SecPlugin:
    """
    WebSocket 插件框架。
    """

    def __init__(self, ws_url: str = "ws://127.0.0.1:24804", secret: str = "SecretToken") -> None:
        """
        构造器。

        Args:
            ws_url (str): WebSocket服务器地址。
            secret (str): 连接用的密钥。
        """
        self.ws_url = ws_url
        self.secret = secret
        self.seq = 1
        self.handlers: Dict[str, Callable[..., Union[None, Coroutine[Any, Any, None]]]] = {}
        self.msg_handlers: List[Tuple[Pattern[str], Callable]] = []
        self.executor = concurrent.futures.ThreadPoolExecutor(max_workers=4)
        self.websocket: Optional[websockets.WebSocketClientProtocol] = None

    def onCmd(self, cmd_name: str) -> Callable[[Callable], Callable]:
        """
        装饰器：注册命令回调。

        Args:
            cmd_name (str): 命令名称。

        Returns:
            Callable: 装饰器函数。
        """
        def decorator(func: Callable) -> Callable:
            self.handlers[cmd_name] = func
            return func
        return decorator

    def onMsg(self, pattern: str) -> Callable[[Callable], Callable]:
        """
        装饰器：注册消息正则匹配回调。

        Args:
            pattern (str): 正则表达式字符串。

        Returns:
            Callable: 装饰器函数。
        """
        compiled = re.compile(pattern)

        def decorator(func: Callable) -> Callable:
            self.msg_handlers.append((compiled, func))
            return func
        return decorator

    async def send(self, cmd: str, data: Any) -> None:
        """
        发送WebSocket包。

        Args:
            cmd (str): 命令名称。
            data (Any): 命令数据内容。
        """
        if not self.websocket:
            print("Websocket未连接，发送失败")
            return
        msg = {
            'cmd': cmd,
            'seq': self.seq,
            'data': data,
            'rsp': True,
        }
        message = json.dumps(msg)
        try:
            await self.websocket.send(message)
            print(f"已发送消息: {message}")
            self.seq += 1
        except Exception as e:
            print("发送消息异常:", e)

    async def sendMsg(self, data: Dict[str, Any], text: str) -> None:
        """
        自适应发送回复消息。

        Args:
            data (Dict[str, Any]): 原始接收消息数据。
            text (str): 要回复的文本。
        """
        if not isinstance(data.get("data"), list) or len(data["data"]) == 0:
            print("sendMsg:参数data格式异常，缺少data字段包含列表")
            return

        base_info = data["data"][0]
        reply_content = []
        if "Group" in base_info:
            reply_content = [
                {
                    "Account": base_info.get("Account"),
                    "Group": "Group",
                    "GroupId": base_info.get("GroupId")
                },
                {
                    "Text": text
                }
            ]
        elif "Friend" in base_info:
            reply_content = [
                {
                    "Account": base_info.get("Account"),
                    "Friend": "Friend",
                    "Uin": base_info.get("Uin")
                },
                {
                    "Text": text
                }
            ]
        elif "Temp" in base_info:
            reply_content = [
                {
                    "Account": base_info.get("Account"),
                    "Temp": "Temp",
                    "GroupId": base_info.get("GroupId"),
                    "Uin": base_info.get("Uin")
                },
                {
                    "Text": text
                }
            ]
        elif "Guild" in base_info:
            reply_content = [
                {
                    "Account": base_info.get("Account"),
                    "Guild": "Guild",
                    "GuildId": base_info.get("GuildId"),
                    "ChannelId": base_info.get("ChannelId")
                },
                {
                    "Text": text
                }
            ]

        if reply_content:
            await self.send("SendOicqMsg", reply_content)

    async def handle_message(self, message: str) -> None:
        """
        处理收到的消息，分发命令和匹配正则调用回调。

        Args:
            message (str): JSON字符串格式消息。
        """
        try:
            data = json.loads(message)
        except json.JSONDecodeError:
            print("收到非JSON消息:", message)
            return

        cmd = data.get("cmd")
        handler = self.handlers.get(cmd)
        if not handler:
            print(f"No handler for cmd: {cmd}")
            return

        if asyncio.iscoroutinefunction(handler):
            await handler(data)
        else:
            loop = asyncio.get_running_loop()
            await loop.run_in_executor(self.executor, handler, data)

        if cmd == "PushOicqMsg":
            text_to_match = "\n".join(m.get("Text", "") for m in data.get("data", []))
            for regex, callback in self.msg_handlers:
                match = regex.search(text_to_match)
                if match:
                    if asyncio.iscoroutinefunction(callback):
                        await callback(data, match)
                    else:
                        loop = asyncio.get_running_loop()
                        await loop.run_in_executor(self.executor, callback, data, match)

    async def connect(self, uri: str) -> None:
        """
        异步连接 WebSocket，开始消息监听。

        Args:
            uri (str): WebSocket地址。
        """
        async with websockets.connect(uri) as websocket:
            self.websocket = websocket
            print(f"连接到 {uri}")
            await self.send(cmd="SyncOicq",
                            data={"pid": "motherfucker plugin", "name": "a shit by SumaRoder", "token": self.secret})
            async for message in websocket:
                asyncio.create_task(self.handle_message(message))

    async def _run(self) -> None:
        try:
            await self.connect(self.ws_url)
        except asyncio.CancelledError:
            print("连接任务被取消")
        finally:
            if self.websocket:
                await self.websocket.close()
                print("WebSocket连接已关闭")

    def start(self) -> None:
        """
        启动事件循环并连接 WebSocket 服务。
        """
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        task = loop.create_task(self._run())

        try:
            loop.run_until_complete(task)
        except KeyboardInterrupt:
            print("收到退出信号，正在关闭...")
            task.cancel()
            loop.run_until_complete(task)
        finally:
            loop.close()
            print("事件循环已关闭")
