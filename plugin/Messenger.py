from .Msg import Msg
from json import loads, dumps

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

    def hasMsg(self, tag):
        """判断是否存在指定类型的消息。

        Args:
            tag (str): 消息标签。
        Returns:
            bool: 是否存在该类型消息。
        """
        for l in self.msg:
            if tag in l:
                return True
        return False

    def getString(self, tag, devalue = "0", index = None):
        """获取某消息字符串。

        Args:
            tag (str): 消息标签。
            devalue (str, optional): 默认值，默认为"0"。
            index (int, optional): 指定索引。
        Returns:
            str: 获取到的消息字符串。
        """
        res = ""
        if index is not None:
            return self.msg[index][tag] if tag in self.msg[index] else devalue
        for l in self.msg:
            if tag in l:
                res += l[tag]
        return res if res else devalue

    def getList(self, index = None, tag = None):
        """获取消息体原始值。

        Args:
            index (int, optional): 指定索引。
            tag (str, optional): 指定标签。
        Returns:
            list: 消息体原始值。
        """
        if index is not None and index >= 0 and index < self.getListSize():
            return self.msg[index]
        if tag is not None:
            values = []
            for l in self.msg:
                if tag in l:
                    values.append(l[tag])
            return values
        return self.msg

    def getListSize(self):
        """获取消息长度。

        Returns:
            int: 消息体长度。
        """
        return len(self.msg)

    def getMsgSize(self, tag = None):
        """获取消息内容总长度。

        Args:
            tag (str, optional): 指定标签。
        Returns:
            int: 消息内容总长度。
        """
        cnt = 0
        for l in self.msg:
            if tag is not None and tag in l:
                cnt += 1
            else:
                cnt += len(l)
        return cnt

    def addMsg(self, tag, value):
        """添加消息。

        Args:
            tag (str): 消息标签。
            value: 消息值。
        Returns:
            list: 添加后的消息体。
        """
        if not tag:
            return self.msg
        if tag == Msg.AtUin or tag == Msg.AtName or tag == Msg.AtAll:
            if tag != Msg.AtAll:
                for l in self.msg:
                    if len(l) == 1 and (Msg.AtUin in l or Msg.AtName in l):
                        if not tag in l:
                            l[tag] = value
                            return self.msg
            if not (tag == Msg.Text or tag == Msg.Img or tag == Msg.Gif or tag == Msg.Emoid):
                for l in self.msg:
                    if not tag in l:
                        l[tag] = value
                        return self.msg
        self.msg.append({tag: value});
        return self.msg;

    def removeMsg(self, tag):
        """删除消息。

        Args:
            tag (str): 消息标签。
        Returns:
            list: 删除后的消息体。
        """
        for l in self.msg:
            l.remove(tag)
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


    """
     * @Name StaticMethod Messenger.getSendMessenger
     * @Desc 通过原始消息体自适应为基础消息体
    """
    @staticmethod
    def getSendMessenger(msg):
        """通过原始消息体自适应为基础消息体。

        Args:
            msg (list): 原始消息体。
        Returns:
            Messenger: 适配后的Messenger对象。
        """
        # 这里应根据实际逻辑实现
        return Messenger(msg)
