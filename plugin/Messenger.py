from .Msg import Msg
from json import loads, dumps
from typing import Union

"""
 * @Author SumaRoder
 * @Name   Messenger
 * @Desc   消息体
"""
class Messenger:
    """消息体。

    用于封装和操作消息内容。
    """
    def __init__(self, msg = []):
        """构造器。

        Args:
            msg (list, optional): 消息内容，默认为空列表。
        """
        self.msg = msg

    def hasMsg(self, tag: Union[Msg, str]):
        """判断是否存在指定类型的消息。

        Args:
            tag (Msg|str): 消息标签。
        Returns:
            bool: 是否存在该类型消息。
        """
        tag_val = tag.value if isinstance(tag, Msg) else tag
        for l in self.msg:
            if tag_val in l:
                return True
        return False

    def getString(self, tag: Union[Msg, str], devalue = "0", index = None):
        """获取某消息字符串。

        Args:
            tag (Msg|str): 消息标签。
            devalue (str, optional): 默认值，默认为"0"。
            index (int, optional): 指定索引。
        Returns:
            str: 获取到的消息字符串。
        """
        tag_val = tag.value if isinstance(tag, Msg) else tag
        res = ""
        if index is not None:
            return self.msg[index][tag_val] if tag_val in self.msg[index] else devalue
        for l in self.msg:
            if tag_val in l:
                res += l[tag_val]
        return res if res else devalue

    def getList(self, index = None, tag: Union[Msg, str] | None = None):
        """获取消息体原始值。

        Args:
            index (int, optional): 指定索引。
            tag (Msg|str, optional): 指定标签。
        Returns:
            list: 消息体原始值。
        """
        if index is not None and index >= 0 and index < self.getListSize():
            return self.msg[index]
        if tag is not None:
            tag_val = tag.value if isinstance(tag, Msg) else tag
            values = []
            for l in self.msg:
                if tag_val in l:
                    values.append(l[tag_val])
            return values
        return self.msg

    def getListSize(self):
        """获取消息长度。

        Returns:
            int: 消息体长度。
        """
        return len(self.msg)

    def getMsgSize(self, tag: Union[Msg, str] | None = None):
        """获取消息内容总长度。

        Args:
            tag (Msg|str, optional): 指定标签。
        Returns:
            int: 消息内容总长度。
        """
        cnt = 0
        tag_val = tag.value if isinstance(tag, Msg) else tag
        for l in self.msg:
            if tag is not None and tag_val in l:
                cnt += 1
            else:
                cnt += len(l)
        return cnt

    def addMsg(self, tag: Union[Msg, str], value):
        """添加消息。

        Args:
            tag (Msg|str): 消息标签。
            value: 消息值。
        Returns:
            list: 添加后的消息体。
        """
        if not tag:
            return self.msg
        tag_val = tag.value if isinstance(tag, Msg) else tag
        if tag_val == Msg.AtUin.value or tag_val == Msg.AtName.value or tag_val == Msg.AtAll.value:
            if tag_val != Msg.AtAll.value:
                for l in self.msg:
                    if len(l) == 1 and (Msg.AtUin.value in l or Msg.AtName.value in l):
                        if not tag_val in l:
                            l[tag_val] = value
                            return self.msg
            if not (tag_val == Msg.Text.value or tag_val == Msg.Img.value or tag_val == Msg.Gif.value or tag_val == Msg.Emoid.value):
                for l in self.msg:
                    if not tag_val in l:
                        l[tag_val] = value
                        return self.msg
        self.msg.append({tag_val: value})
        return self.msg

    def removeMsg(self, tag: Union[Msg, str]):
        """删除消息。

        Args:
            tag (Msg|str): 消息标签。
        Returns:
            list: 删除后的消息体。
        """
        tag_val = tag.value if isinstance(tag, Msg) else tag
        for l in self.msg:
            if tag_val in l:
                l.pop(tag_val)
        return self.msg

    def clearMsg(self):
        """清空消息体。

        Returns:
            list: 空消息体。
        """
        self.msg = []
        return []

    def toString(self):
        """消息体转字符串。

        Returns:
            str: 消息体的JSON字符串。
        """
        return dumps(self.msg, ensure_ascii=False)

    @staticmethod
    def getSendMessenger(messenger: 'Messenger'):
        """通过原始消息体自适应为基础消息体。

        Args:
            msg (list): 原始消息体。
        Returns:
            Messenger: 适配后的Messenger对象。
        """
        if messenger.hasMsg(Msg.Group):
            return Messenger([{
                Msg.Account: messenger.getString(Msg.Account),
                Msg.Group: Msg.Group,
                Msg.GroupId: messenger.getString(Msg.GroupId)
            }])
        elif messenger.hasMsg(Msg.Friend):
            return Messenger([{
                Msg.Account: messenger.getString(Msg.Account),
                Msg.Friend: Msg.Friend,
                Msg.Uin: messenger.getString(Msg.Uin)
            }])
        elif messenger.hasMsg(Msg.Temp):
            return Messenger([{
                Msg.Account: messenger.getString(Msg.Account),
                Msg.Temp: Msg.Temp,
                Msg.GroupId: messenger.getString(Msg.GroupId),
                Msg.Uin: messenger.getString(Msg.Uin)
            }])
        elif messenger.hasMsg(Msg.Guild):
            return Messenger([{
                Msg.Account: messenger.getString(Msg.Account),
                Msg.Guild: Msg.Guild,
                Msg.GuildId: messenger.getString(Msg.GuildId),
                Msg.ChannelId: messenger.getString(Msg.ChannelId)
            }])
        else:
            return Messenger()
