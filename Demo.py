import sys
import io
from plugin.SecPlugin import run as RunPlugin
from plugin.SecPlugin import SecPlugin, PluginConfig
from plugin.Messenger import Messenger
from plugin.Msg import Msg

imgListener = True

"""
 * @Author SumaRoder
 * @Name   DemoBotClient
 * @Desc   示例Bot端
"""
class DemoBotClient(SecPlugin):
    """示例Bot端。

    继承自SecPlugin，实现了群聊、好友、临时、频道消息的处理逻辑。
    """
    def __init__(self, config=PluginConfig()):
        """构造器。

        Args:
            config (PluginConfig, optional): 插件配置，默认为PluginConfig()。
        """
        super().__init__(config)

    async def onTimeTask(self, msg):
        """定时任务处理。

        Args:
            msg: 定时任务消息对象。
        """
        await super().onTimeTask(msg)

    async def onMsgHandler(self, msg):
        """消息总处理。

        Args:
            msg: 消息对象。
        """
        await super().onMsgHandler(msg)

    async def onGroupMsgHandler(self, messenger):
        """群聊消息总处理。

        Args:
            messenger (Messenger): 群聊消息对象。
        """
        await super().onGroupMsgHandler(messenger)
        text = messenger.getString(Msg.Text)
        uin = messenger.getString(Msg.Uin)
        if text == "测试":
            await self.sendMsg(messenger, "成功")
        global imgListener
        if imgListener and uin != messenger.getString(Msg.Account):
            if messenger.hasMsg(Msg.Img):
                await self.sendMsg(messenger, f"收到图片 {messenger.getString(Msg.Url)}")
                await self.sendPic(messenger, messenger.getString(Msg.Url))
                await self.send(messenger, [[Msg.Text, "成功"], [Msg.Img, messenger.getString(Msg.Url)]])
            if messenger.hasMsg(Msg.Gif):
                await self.sendMsg(messenger, f"收到动图 {messenger.getString(Msg.Url)}")
                await self.sendPic(messenger, messenger.getString(Msg.Url))
                await self.send(messenger, [[Msg.Text, "成功"], [Msg.Gif, messenger.getString(Msg.Url)]])
        if text == "开图片监听":
            if uin != "1493813167":
                return
            imgListener = True
        if text == "关图片监听":
            if uin != "1493813167":
                return
            imgListener = False
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
        """好友消息总处理。

        Args:
            messenger (Messenger): 好友消息对象。
        """
        await super().onFriendMsgHandler(messenger)

    async def onTempMsgHandler(self, messenger):
        """临时消息总处理。

        Args:
            messenger (Messenger): 临时消息对象。
        """
        await super().onTempMsgHandler(messenger)

    async def onGuildMsgHandler(self, messenger):
        """频道消息总处理。

        Args:
            messenger (Messenger): 频道消息对象。
        """
        await super().onGuildMsgHandler(messenger)

RunPlugin(DemoBotClient())