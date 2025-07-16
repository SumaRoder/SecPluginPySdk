from typing import Union
import websockets
import asyncio
import threading
import traceback
from time import sleep
from datetime import datetime
from json import dumps, loads
import queue
import logging
from logging.handlers import QueueHandler, QueueListener
from .Msg import Msg
from .Messenger import Messenger
from websockets.legacy.client import WebSocketClientProtocol
from typing import Any

class PluginConfig:
    """
    插件配置数据结构。

    Attributes:
        WS_URL (str): Secluded配置的WebSocket协议地址。
        PID (str): 插件和Secluded对接的唯一ID。
        NAME (str): 插件名称。
        TOKEN (str): Secluded配置的WebSocket密钥。
        PING_INTERVAL (Optional[int]): 每隔一段时间(单位秒)对WebSocket对方发送一次Ping帧，如果对方没有在规定时间内返回Pong WebSocket自动重连，填None代表不进行Ping。
        LOG_LEVEL (int): 日志的详细程度。0 简略模式，1 详细模式，2 原始模式。
    """
    WS_URL = "ws://127.0.0.1:24804"
    PID = "com.sumaroder.secplugin"
    NAME = "SumaPlugin"
    TOKEN = "SecretToken"
    PING_INTERVAL = None
    LOG_LEVEL = 0

class SecPlugin:
    """
    插件主类，请继承重写此类。
    """

    def __init__(self, config: PluginConfig = PluginConfig()):
        """
        初始化SecPlugin。

        Args:
            config (PluginConfig, optional): 插件配置，默认为PluginConfig()。
        """
        self.seq: int = 1
        self.ws: Any = None
        self.log_queue: queue.Queue[Any] = queue.Queue()
        self.running: bool = True
        self.config: PluginConfig = config
        self.GolineModes: dict[str, list[str]] = {
            "SA": ["Scan Android", "安卓手表"],
            "PA": ["Password Android", "安卓手机"],
            "PP": ["Password Pad", "安卓平板"],
            "SL": ["Scan Linux", "企鹅扫码"],
            "PL": ["Password Linux", "企鹅密码"],
            "PO": ["Password Official", "官方人机"]
        }
        self._setup_logging()

    def _setup_logging(self):
        """
        配置日志系统。
        """
        self.logger = logging.getLogger(self.config.PID)
        self.logger.setLevel(logging.DEBUG)

        for handler in self.logger.handlers[:]:
            self.logger.removeHandler(handler)

        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.DEBUG)
        console_formatter = logging.Formatter(
            '[%(asctime)s | %(levelname)s] %(message)s',
            datefmt='%H:%M:%S'
        )
        console_handler.setFormatter(console_formatter)
        self.logger.addHandler(console_handler)

        file_handler = logging.FileHandler("app.log", encoding="utf-8")
        file_handler.setLevel(logging.DEBUG)
        if self.config.LOG_LEVEL == 0:
            file_formatter = logging.Formatter(
                '[%(asctime)s | %(levelname)s]%(message)s',
                datefmt='%H:%M:%S'
            )
        else:
            file_formatter = logging.Formatter(
                '[%(asctime)s][%(levelname)s]%(message)s',
                datefmt='%Y-%m-%d | %H:%M:%S.%f'
            )
        file_handler.setFormatter(file_formatter)
        self.logger.addHandler(file_handler)

    def log(self, msg: str, level: int = logging.INFO):
        """
        添加日志。

        Args:
            msg (str): 日志消息。
            level (int, optional): 日志级别，默认为logging.INFO。
        """
        self.logger.log(level, msg)

    async def connect(self):
        """
        启动WebSocket对象，连接到Secluded，并接收Secluded传回的部分消息。
        """
        while self.running:
            try:
                async with websockets.connect(
                    self.config.WS_URL,
                    ping_interval=self.config.PING_INTERVAL,
                    ping_timeout=30
                ) as ws:
                    self.ws = ws
                    await self.onOpen()
                    while self.running:
                        try:
                            message = await asyncio.wait_for(self.ws.recv(), timeout=None)
                            msg = loads(message)
                            await self.onMsgHandler(msg)
                        except (websockets.ConnectionClosed, ConnectionRefusedError) as e:
                            raise e
                        except Exception as e:
                            traceback.print_exc()
                            self.log(f"消息处理错误: {str(e)}", level=3)
            except (websockets.ConnectionClosed, ConnectionRefusedError) as e:
                self.log(f"连接中断: {str(e)}，3秒后重连...", level=2)
                await asyncio.sleep(3)
            except Exception as e:
                self.log(f"发生错误: {str(e)}，3秒后重连...", level=3)
                await asyncio.sleep(3)

    async def onOpen(self):
        """
        WebSocket与Secluded连接成功后进行同步，才可以继续收到其他消息。
        同步成功后，会收到一个Response消息，其中data.status为true。
        """
        await self.sendWss(
            cmd="SyncOicq",
            data={
                "pid": self.config.PID,
                "name": self.config.NAME,
                "token": self.config.TOKEN
            }
        )

    def _enum_keys_to_str(self, obj):
        """
        将Msg枚举类中的键转换为字符串。

        Args:
            obj (Any): 需要转换的对象。
        
        Returns:
            Any: 转换后的对象。
        """
        if isinstance(obj, dict):
            return { (k.value if isinstance(k, Msg) else k): self._enum_keys_to_str(v) for k, v in obj.items() }
        elif isinstance(obj, list):
            return [self._enum_keys_to_str(i) for i in obj]
        elif isinstance(obj, Msg):
            return obj.value
        else:
            return obj

    async def sendWss(self, cmd: str, data: Any, needRsp: bool = True):
        """
        发送WebSocket到Secluded。

        Args:
            cmd (str): 指令。
            data (Any): 内容。
            needRsp (bool, optional): 是否需要等待响应，默认为True。
        """
        if self.ws is None:
            raise Exception("WebSocket未连接")

        seq = self.seq
        self.seq += 1

        json_msg = {
            "seq": seq,
            "cmd": cmd,
            "rsp": needRsp
        }

        if data is not None:
            if isinstance(data, Messenger):
                json_msg["data"] = self._enum_keys_to_str(data.getList())
            else:
                json_msg["data"] = self._enum_keys_to_str(data)

        await self.ws.send(dumps(json_msg))
        self.log(f"[sendWss] -> {dumps(json_msg, ensure_ascii=False)}")

    async def sendMsg(self, messenger: Messenger, text: str):
        """
        自适应发送文本消息。

        Args:
            messenger (Messenger): 原消息的Messenger对象。
            text (str): 文本内容。
        """
        if not text:
            return
        messenger = Messenger.getSendMessenger(messenger)
        if messenger.getListSize() == 0:
            self.log(f"无法自适应该消息体 | {messenger.toString()}")
            return
        messenger.addMsg(Msg.Text, text)
        await self.sendWss(
            cmd="SendOicqMsg",
            data=messenger
        )

    async def sendPic(self, messenger: Messenger, url: str):
        """
        自适应发送图片消息。

        Args:
            messenger (Messenger): 原消息的Messenger对象。
            url (str): 发送图片的链接/地址。
        """
        if not url:
            return
        messenger = Messenger.getSendMessenger(messenger)
        if messenger.getListSize() == 0:
            self.log(f"无法自适应该消息体 | {messenger.toString()}")
            return
        messenger.addMsg(Msg.Img, url)
        await self.sendWss(
            cmd="SendOicqMsg",
            data=messenger
        )

    async def send(self, messenger: Messenger, msgList: list[list[Union[str, str]]]):
        """
        自适应发送自定义列表消息。

        Args:
            messenger (Messenger): 原消息的Messenger对象。
            msgList (list[list[Union[int, str]]]): 消息列表，格式 [[Msg.Type, Content], ...]。
        """
        if not msgList:
            return
        messenger = Messenger.getSendMessenger(messenger)
        if messenger.getListSize() == 0:
            self.log(f"无法自适应该消息体 | {messenger.toString()}")
            return
        for l in msgList:
            if len(l) == 2:
                messenger.addMsg(l[0], l[1])
        await self.sendWss(
            cmd="SendOicqMsg",
            data=messenger
        )

    async def onMsgHandler(self, msg: dict[str, Any]):
        """
        消息总处理。

        Args:
            msg (dict[str, Any]): 原消息。
        """
        try:
            if msg.get("cmd") == "Response" and "seq" in msg:
                seq = msg["seq"]
                self.log(f"[recvWss] -> {dumps(msg, ensure_ascii=False)}")
                return
            
            if self.config.LOG_LEVEL == 2:
                self.log(f"{msg}", level=1)
                return
            
            if msg["cmd"] == "Heartbeat":
                await self.onHeartbeat(msg)
            elif msg["cmd"] == "Response":
                if msg["data"].get("status"):
                    self.log("服务端认证成功")
                else:
                    self.log(f"认证失败: {msg['data']}", level=2)
            elif "data" in msg:
                messenger = Messenger(msg["data"])
                if msg["cmd"] == "PushOicqMsg":    
                    if messenger.hasMsg(Msg.Group):
                        await self.onGroupMsgHandler(messenger)
                    elif messenger.hasMsg(Msg.Friend):
                        await self.onFriendMsgHandler(messenger)
                    elif messenger.hasMsg(Msg.Temp):
                        await self.onTempMsgHandler(messenger)
                    elif messenger.hasMsg(Msg.Guild):
                        await self.onGuildMsgHandler(messenger)
                    elif messenger.hasMsg(Msg.Goline) or messenger.hasMsg(Msg.Offline):
                        await self.onLine(messenger)
                    elif messenger.hasMsg(Msg.OntimeTask):
                         await self.onTimeTask(messenger)
                    elif messenger.hasMsg(Msg.Heartbeat):
                        await self.onAccountHeartbeat(messenger)
            else:
                self.log(f"{msg['cmd']} - {msg.get('data', '无数据')}")
        except Exception as e:
            traceback.print_exc()
            self.log(f"消息处理异常: {str(e)} | 原始数据: {msg}", level=3)

    """
     * @Name SecPlugin.onTimeTask
     * @Desc 定时任务 5分钟一次 该函数由SecPlugin.onMsgHandler回调执行
     
     Args:
       messenger: 原消息的Messenger对象
    """
    async def onTimeTask(self, messenger):
        """
        定时任务 5分钟一次，由SecPlugin.onMsgHandler回调执行。

        Args:
            messenger (Messenger): 原消息的Messenger对象。
        """
        self.log(f"[系统消息 | 定时任务] {messenger.getString(Msg.OntimeTask)}")

    """
     * @Name SecPlugin.onLine
     * @Desc 账号上下线总处理 该函数由SecPlugin.onMsgHandler回调执行
     
     Args:
       messenger: 原消息的Messenger对象
    """
    async def onLine(self, messenger):
        """
        账号上下线总处理，由SecPlugin.onMsgHandler回调执行。

        Args:
            messenger (Messenger): 原消息的Messenger对象。
        """
        mode = self.GolineModes.get(messenger.getString(Msg.GolineMode), ["未知模式", "Unknown"])
        timestamp, text = (messenger.getString(Msg.Goline), "上线") if messenger.hasMsg(Msg.Goline) else (messenger.getString(Msg.Offline), "下线")
        self.log(f"账号[{messenger.getString(Msg.Account)}]{text} | {text}模式: {mode[1]}({mode[0]}) | {text}时间：{timestamp}")

    """
     * @Name SecPlugin.onHeartbeat
     * @Desc 框架心跳总处理 该函数由SecPlugin.onMsgHandler回调执行
     
     Args:
       messenger: 原消息的Messenger对象
    """
    async def onHeartbeat(self, msg):
        """
        框架心跳总处理，由SecPlugin.onMsgHandler回调执行。

        Args:
            msg (dict): 原消息。
        """
        self.log(f"框架心跳 | {msg.get('cmd-ver', 'unknown')}")
        await self.sendWss(
            cmd="Heartbeat",
            data={
                "pid": self.config.PID,
                "name": self.config.NAME,
                "token": self.config.TOKEN
            }
        )

    """
     * @Name SecPlugin.onHeartbeat
     * @Desc 账号心跳总处理 该函数由SecPlugin.onMsgHandler回调执行
     
     Args:
       messenger: 原消息的Messenger对象
    """
    async def onAccountHeartbeat(self, messenger):
        """
        账号心跳总处理，由SecPlugin.onMsgHandler回调执行。

        Args:
            messenger (Messenger): 原消息的Messenger对象。
        """
        mode = self.GolineModes.get(messenger.getString(Msg.GolineMode), ["未知模式", "Unknown"])
        self.log(f"账号[{messenger.getString(Msg.Account)}]心跳: {messenger.getString(Msg.Heartbeat)} | 上线模式: {mode[1]}({mode[0]})")

    """
     * @Name SecPlugin.onGroupMsgHandler
     * @Desc 群聊消息总处理 该函数由SecPlugin.onMsgHandler回调执行
     
     Args:
       messenger: 原消息的Messenger对象
    """
    async def onGroupMsgHandler(self, messenger):
        """
        群聊消息总处理，由SecPlugin.onMsgHandler回调执行。

        Args:
            messenger (Messenger): 原消息的Messenger对象。
        """
        self.log(f"群[{messenger.getString(Msg.GroupId)} | {messenger.getString(Msg.Uin)}]消息: {messenger.getString(Msg.Text)}")

    """
     * @Name SecPlugin.onFriendMsgHandler
     * @Desc 好友消息总处理 该函数由SecPlugin.onMsgHandler回调执行
     
     Args:
       messenger: 原消息的Messenger对象
    """
    async def onFriendMsgHandler(self, messenger):
        """
        好友消息总处理，由SecPlugin.onMsgHandler回调执行。

        Args:
            messenger (Messenger): 原消息的Messenger对象。
        """
        self.log(f"好友[{messenger.getString(Msg.Uin)}]消息: {messenger.getString(Msg.Text)}")

    """
     * @Name SecPlugin.onTempMsgHandler
     * @Desc 临时消息总处理 该函数由SecPlugin.onMsgHandler回调执行
     
     Args:
       messenger: 原消息的Messenger对象
    """
    async def onTempMsgHandler(self, messenger):
        """
        临时消息总处理，由SecPlugin.onMsgHandler回调执行。

        Args:
            messenger (Messenger): 原消息的Messenger对象。
        """
        self.log(f"临时[{messenger.getString(Msg.GroupId)} | {messenger.getString(Msg.Uin)}]消息: {messenger.getString(Msg.Text)}")

    """
     * @Name SecPlugin.onGuildMsgHandler
     * @Desc 频道消息总处理 该函数由SecPlugin.onMsgHandler回调执行
     
     Args:
       messenger: 原消息的Messenger对象
    """
    async def onGuildMsgHandler(self, messenger):
        """
        频道消息总处理，由SecPlugin.onMsgHandler回调执行。

        Args:
            messenger (Messenger): 原消息的Messenger对象。
        """
        self.log(f"频道[{messenger.getString(Msg.GuildId)} | {messenger.getString(Msg.Uin)}]消息: {messenger.getString(Msg.Text)}")

"""
 * @Author SumaRoder
 * @Name   start_websocket
 * @Desc   新建一个进程用于维持SecPlugin与Secluded连接
 
 Args:
   plugin: SecPlugin
"""
def start_websocket(plugin):
    """
    新建一个进程用于维持SecPlugin与Secluded连接。

    Args:
        plugin (SecPlugin): 插件实例。
    """
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(plugin.connect())

"""
 * @Author SumaRoder
 * @Name   run
 * @Desc   一键启动 SecPlugin/消费日志进程
 
 Args:
  plugin: SecPlugin
"""
def run(plugin):
    """
    一键启动 SecPlugin/消费日志进程。

    Args:
        plugin (SecPlugin): 插件实例。
    """
    ws_thread = threading.Thread(target=start_websocket, args=(plugin,), daemon=True)
    ws_thread.start()
    
    try:
        while True:
            sleep(1)
    except KeyboardInterrupt:
        plugin.running = False
        # 停止日志监听器
        if hasattr(plugin, 'log_listener'):
            plugin.log_listener.stop()
        print("\n正在关闭...等待线程退出")
        ws_thread.join(timeout=1)
        print("程序终止")
