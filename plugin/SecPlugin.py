import websockets
import asyncio
import threading
import traceback
from time import sleep
from datetime import datetime
from json import dumps, loads
import queue
from .Msg import Msg
from .Messenger import Messenger

"""
 * @Author SumaRoder
 * @Name   PluginConfig
 * @Desc   插件配置
"""
class PluginConfig:
    """插件配置。

    包含WebSocket地址、插件ID、名称、Token、心跳间隔、日志等级等配置项。
    """
    WS_URL = "ws://127.0.0.1:24804"
    PID = "com.sumaroder.secplugin"
    NAME = "SumaPlugin"
    TOKEN = "SecretToken"
    PING_INTERVAL = None
    LOG_LEVEL = 0  # 0 简略模式 | 1 详细模式 | 2 原始模式

"""
 * @Author SumaRoder
 * @Name   SecPlugin
 * @Desc   插件
"""
class SecPlugin:
    """插件基类。

    提供WebSocket连接、消息处理、日志、账号上下线、心跳等功能。
    """
    def __init__(self, config=PluginConfig()):
        """构造器。

        Args:
            config (PluginConfig, optional): 插件配置，默认为PluginConfig()。
        """
        self.seq = 1
        self.ws = None
        self.msg_queue = queue.Queue()
        self.running = True
        self.config = config
        self.GolineModes = {
            "SA": ["Scan Android", "安卓手表"],
            "PA": ["Password Android", "安卓手机"],
            "PP": ["Password Pad", "安卓平板"],
            "SL": ["Scan Linux", "企鹅扫码"],
            "PL": ["Password Linux", "企鹅密码"],
            "PO": ["Password Official", "官方人机"]
        }

    """
     * @Name SecPlugin.log
     * @Desc 添加日志
    """
    async def log(self, msg, level=0):
        """添加日志。

        Args:
            msg (str): 日志内容。
            level (int, optional): 日志等级，默认为0。
        """
        levels = ["Info", "Debug", "Warn", "Error"]
        timestamp = datetime.now()
        
        if self.config.LOG_LEVEL == 0:
            log_msg = f"[{timestamp.strftime('%H:%M:%S')} | {levels[level]}]{" " if len(levels[level]) == 5 else "  "}{msg}"
        else:
            log_msg = f"[{timestamp.strftime('%Y-%m-%d | %H:%M:%S.%f')}][{levels[level]}]{" " if len(levels[level]) == 5 else "  "}{msg}"
            
        self.msg_queue.put(log_msg)
        print(log_msg)

    """
     * @Name SecPlugin.connect
     * @Desc 启动WebSocket对象 | 连接到Secluded | 接收Secluded传回的部分消息
    """
    async def connect(self):
        """启动WebSocket对象，连接到Secluded并接收消息。"""
        while self.running:
            try:
                async with websockets.connect(
                    self.config.WS_URL,
                    ping_interval=self.config.PING_INTERVAL,
                    ping_timeout=30
                ) as self.ws:
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
                            await self.log(f"消息处理错误: {str(e)}", level=3)
            except (websockets.ConnectionClosed, ConnectionRefusedError) as e:
                await self.log(f"连接中断: {str(e)}，3秒后重连...", level=2)
                await asyncio.sleep(3)
            except Exception as e:
                await self.log(f"发生错误: {str(e)}，3秒后重连...", level=3)
                await asyncio.sleep(3)

    """
     * @Name SecPlugin.onOpen
     * @Desc WebSocket与Secluded连接成功后 需要进行同步 才可以继续收到其他消息
    """
    async def onOpen(self):
        """WebSocket与Secluded连接成功后进行同步。"""
        await self.sendWss(
            cmd="SyncOicq",
            data={
                "pid": self.config.PID,
                "name": self.config.NAME,
                "token": self.config.TOKEN
            }
        )

    """
     * @Name SecPlugin.sendWss
     * @Desc 发送WebSocket到Secluded
    """
    async def sendWss(self, cmd, data=None):
        """发送WebSocket消息到Secluded。

        Args:
            cmd (str): 命令。
            data (dict, optional): 数据内容。
        """
        json_msg = {
            "seq": self.seq,
            "cmd": cmd,
            "data": data or {}
        }
        self.seq += 1
        if isinstance(data, Messenger):
            json_msg["data"] = data.getList()
        if not self.ws:
            await self.log("WebSocket 未连接，无法发送消息", level=3)
            return
        await self.ws.send(dumps(json_msg))
        await self.log(f"[sendWss] {dumps(json_msg, ensure_ascii=False)}")

    """
     * @Name SecPlugin.sendMsg
     * @Desc 自适应发送文本消息
    """
    async def sendMsg(self, messenger, text):
        if not text:
            return
        messenger = Messenger.getSendMessenger(messenger)
        if messenger.getListSize() == 0:
            await self.log(f"无法自适应该消息体 | {messenger.toString()}")
            return
        messenger.addMsg(Msg.Text, text)
        await self.sendWss(
            cmd="SendOicqMsg",
            data=messenger
        )

    """
     * @Name SecPlugin.sendMsg
     * @Desc 自适应发送图片消息
    """
    async def sendPic(self, messenger, url):
        if not url:
            return
        messenger = Messenger.getSendMessenger(messenger)
        if messenger.getListSize() == 0:
            await self.log(f"无法自适应该消息体 | {messenger.toString()}")
            return
        messenger.addMsg(Msg.Img, url)
        await self.sendWss(
            cmd="SendOicqMsg",
            data=messenger
        )

    """
     * @Name SecPlugin.sendMsg
     * @Desc 自适应发送自定义列表消息
     * @ListFormat [[Msg.Type, Content], ...]
    """
    async def send(self, messenger, msgList):
        if not msgList:
            return
        messenger = Messenger.getSendMessenger(messenger)
        if messenger.getListSize() == 0:
            await self.log(f"无法自适应该消息体 | {messenger.toString()}")
            return
        for l in msgList:
            if len(l) == 2:
                messenger.addMsg(l[0], l[1])
        await self.sendWss(
            cmd="SendOicqMsg",
            data=messenger
        )

    """
     * @Name SecPlugin.onMsgHandler
     * @Desc 消息总处理
    """
    async def onMsgHandler(self, msg):
        """消息总处理。

        Args:
            msg (dict): 消息内容。
        """
        try:
            if self.config.LOG_LEVEL == 2:
                await self.log(f"{msg}", level=1)
                return
            
            if msg["cmd"] == "Heartbeat":
                await self.onHeartbeat(msg)
            elif msg["cmd"] == "Response":
                if msg["data"].get("status"):
                    await self.log("服务端认证成功")
                else:
                    await self.log(f"认证失败: {msg['data']}", level=2)
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
                await self.log(f"{msg['cmd']} - {msg.get('data', '无数据')}")
        except Exception as e:
            traceback.print_exc()
            await self.log(f"消息处理异常: {str(e)} | 原始数据: {msg}", level=3)

    """
     * @Name SecPlugin.onTimeTask
     * @Desc 定时任务 5分钟一次 该函数由SecPlugin.onMsgHandler回调执行
    """
    async def onTimeTask(self, messenger):
        """定时任务处理，每5分钟回调一次。

        Args:
            messenger (Messenger): 定时任务消息对象。
        """
        await self.log(f"[系统消息 | 定时任务] {messenger.getString(Msg.OntimeTask)}")

    """
     * @Name SecPlugin.onLine
     * @Desc 账号上下线总处理 该函数由SecPlugin.onMsgHandler回调执行
    """
    async def onLine(self, messenger):
        """账号上下线总处理。

        Args:
            messenger (Messenger): 上下线消息对象。
        """
        mode = self.GolineModes.get(messenger.getString(Msg.GolineMode), ["未知模式", "Unknown"])
        timestamp, text = (messenger.getString(Msg.Goline), "上线") if messenger.hasMsg(Msg.Goline) else (messenger.getString(Msg.Offline), "下线")
        await self.log(f"账号[{messenger.getString(Msg.Account)}]{text} | {text}模式: {mode[1]}({mode[0]}) | {text}时间：{timestamp}")

    """
     * @Name SecPlugin.onHeartbeat
     * @Desc 框架心跳总处理 该函数由SecPlugin.onMsgHandler回调执行
    """
    async def onHeartbeat(self, msg):
        """框架心跳总处理。

        Args:
            msg (dict): 心跳消息。
        """
        await self.log(f"框架心跳 | {msg.get('cmd-ver', 'unknown')}")
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
    """
    async def onAccountHeartbeat(self, messenger):
        """账号心跳总处理。

        Args:
            messenger (Messenger): 账号心跳消息对象。
        """
        mode = self.GolineModes.get(messenger.getString(Msg.GolineMode), ["未知模式", "Unknown"])
        await self.log(f"账号[{messenger.getString(Msg.Account)}]心跳: {messenger.getString(Msg.Heartbeat)} | 上线模式: {mode[1]}({mode[0]})")

    """
     * @Name SecPlugin.onGroupMsgHandler
     * @Desc 群聊消息总处理 该函数由SecPlugin.onMsgHandler回调执行
    """
    async def onGroupMsgHandler(self, messenger):
        """群聊消息总处理。

        Args:
            messenger (Messenger): 群聊消息对象。
        """
        await self.log(f"群[{messenger.getString(Msg.GroupId)} | {messenger.getString(Msg.Uin)}]消息: {messenger.getString(Msg.Text)}")

    """
     * @Name SecPlugin.onFriendMsgHandler
     * @Desc 好友消息总处理 该函数由SecPlugin.onMsgHandler回调执行
    """
    async def onFriendMsgHandler(self, messenger):
        """好友消息总处理。

        Args:
            messenger (Messenger): 好友消息对象。
        """
        await self.log(f"好友[{messenger.getString(Msg.Uin)}]消息: {messenger.getString(Msg.Text)}")

    """
     * @Name SecPlugin.onTempMsgHandler
     * @Desc 临时消息总处理 该函数由SecPlugin.onMsgHandler回调执行
    """
    async def onTempMsgHandler(self, messenger):
        """临时消息总处理。

        Args:
            messenger (Messenger): 临时消息对象。
        """
        await self.log(f"临时[{messenger.getString(Msg.GroupId)} | {messenger.getString(Msg.Uin)}]消息: {messenger.getString(Msg.Text)}")

    """
     * @Name SecPlugin.onGuildMsgHandler
     * @Desc 频道消息总处理 该函数由SecPlugin.onMsgHandler回调执行
    """
    async def onGuildMsgHandler(self, messenger):
        """频道消息总处理。

        Args:
            messenger (Messenger): 频道消息对象。
        """
        await self.log(f"频道[{messenger.getString(Msg.GuildId) | messenger.getString(Msg.Uin)}]消息: {messenger.getString(Msg.Text)}")

"""
 * @Author SumaRoder
 * @Name   start_websocket
 * @Desc   新建一个进程用于维持SecPlugin与Secluded连接
"""
def start_websocket(plugin):
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(plugin.connect())

"""
 * @Author SumaRoder
 * @Name   consume_messages
 * @Desc   登记日志总处理  该方法定位主要为 进行消费消息统计
"""
def consume_messages(plugin):
    """登记日志总处理，进行消费消息统计。

    Args:
        plugin (SecPlugin): 插件对象。
    """
    while plugin.running:
        try:
            msg = plugin.msg_queue.get(timeout=1)
            with open("app.log", "a", encoding="utf-8") as f:
                f.write(msg + "\n")
        except queue.Empty:
            continue

"""
 * @Author SumaRoder
 * @Name   run
 * @Desc   一键启动 SecPlugin/消费日志进程
"""
def run(plugin):
    """一键启动 SecPlugin/消费日志进程。

    Args:
        plugin (SecPlugin): 插件对象。
    """
    ws_thread = threading.Thread(target=start_websocket, args=(plugin,), daemon=True)
    ws_thread.start()
    
    consumer_thread = threading.Thread(target=consume_messages, args=(plugin,), daemon=True)
    consumer_thread.start()

    try:
        while True:
            sleep(1)
    except KeyboardInterrupt:
        plugin.running = False
        print("\n正在关闭...等待线程退出")
        ws_thread.join(timeout=1)
        consumer_thread.join(timeout=1)
        print("程序终止")
