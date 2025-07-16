import sys
import io
import asyncio
from plugin.SecPlugin import run as RunPlugin
from plugin.SecPlugin import SecPlugin, PluginConfig
from plugin.Messenger import Messenger
from plugin.Msg import Msg
from typing import Any
from json import dumps

class DemoBotClient(SecPlugin):
    """
    示例Bot端。
    """
    def __init__(self, config=PluginConfig):
        """
        构造器。

        Args:
            config (PluginConfig, optional): 插件配置，默认为PluginConfig。
        """
        super().__init__(config)

    async def onTimeTask(self, msg):
        """
        定时任务处理。

        Args:
            msg: 定时任务消息。
        """
        await super().onTimeTask(msg)

    async def onMsgHandler(self, msg: dict[str, Any]):
        """
        消息总处理。

        Args:
            msg: 消息内容。
        """
        await super().onMsgHandler(msg)

    async def onGroupMsgHandler(self, messenger):
        """
        群聊消息总处理。

        Args:
            messenger (Messenger): 群聊消息体。
        """
        await super().onGroupMsgHandler(messenger)
        group_id = messenger.getString(Msg.GroupId)
        uin = messenger.getString(Msg.Uin)
        uin_name = messenger.getString(Msg.UinName)
        title = messenger.getString(Msg.Title)
        text = messenger.getString(Msg.Text)

        if text == "测试":
            await self.sendMsg(messenger, "成功")

        if text.startswith("执行"):
            if uin != "1493813167":
                return
            output = io.StringIO()
            res = "None"
            error = ""
            try:
                sys.stdout = output
                exec(text[2:], {"messenger": messenger})
            except Exception as e:
                error = str(e)
            finally:
                sys.stdout = sys.__stdout__
            res = output.getvalue()
            await self.sendMsg(messenger, res)
            await self.sendMsg(messenger, error)

    async def onFriendMsgHandler(self, messenger):
        """
        好友消息总处理。

        Args:
            messenger (Messenger): 好友消息体。
        """
        await super().onFriendMsgHandler(messenger)

    async def onTempMsgHandler(self, messenger):
        """
        临时消息总处理。

        Args:
            messenger (Messenger): 临时消息体。
        """
        await super().onTempMsgHandler(messenger)

    async def onGuildMsgHandler(self, messenger):
        """
        频道消息总处理。

        Args:
            messenger (Messenger): 频道消息体。
        """
        await super().onGuildMsgHandler(messenger)

RunPlugin(DemoBotClient())