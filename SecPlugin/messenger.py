from typing import Any, List, Dict, Optional, Union
import copy
from .msg import Msg

class Messenger:
    """
    @Author SumaRoder
    @CreateTime 2022-02-19 11:28:38
    @Description 消息
    """
    
    def __init__(self, data: Optional[Union[str, 'Messenger', List[Dict[str, str]]]] = None):
        """
        @CreateTime 2022-02-27 13:11:44
        @Description 构造函数
        """
        self.list: List[Dict[str, str]] = []
        
        if data is None:
            pass
        elif isinstance(data, str):
            self.addMsg(data)
        elif isinstance(data, Messenger):
            if data.list is not None:
                self.list.extend(copy.deepcopy(data.list))
        elif isinstance(data, list):
            if data is not None:
                self.list.extend(data)
    
    @staticmethod
    def newObject(data: Optional[List[Dict[str, str]]] = None) -> 'Messenger':
        """
        @CreateTime 2022-04-16 09:42:48
        @Description 新建一个对象
        """
        return Messenger(data)
    
    def cloneObject(self) -> 'Messenger':
        """
        @CreateTime 2022-04-16 20:06:38
        @Description 克隆
        """
        return Messenger.newObject(self.getList())
    
    def get(self, tag: Union[str, int], default: Any = "0") -> Any:
        """
        @CreateTime 2022-02-19 11:36:34
        @Description 获取Msg
        """
        if isinstance(tag, int):
            return self._get_by_index(tag, str(default), default)
        else:
            return self._get_by_tag(tag, default)
    
    def _get_by_tag(self, tag: str, default: Any = "0") -> Any:
        """
        @CreateTime 2022-02-19 11:38:54
        @Description 获取Msg
        """
        data = ""
        
        msg_list = self.getList(tag)
        for msg in msg_list:
            data += msg
        
        return data if len(data) > 0 else default
    
    def _get_by_index(self, index: int, tag: str, default: Any = "0") -> Any:
        """
        @CreateTime 2022-04-04 15:55:25
        @Description 获取Msg
        """
        if len(self.list) > index:
            if tag in self.list[index]:
                return self.list[index][tag]
            else:
                return default
        else:
            return default
    
    def getList(self, tag: Optional[str] = None) -> Union[List[Dict[str, str]], List[str]]:
        """
        @CreateTime 2022-03-05 11:01:17
        @Description 获取全部Msg
        """
        if tag is None:
            return self.list
        else:
            # @CreateTime 2022-02-19 11:56:07
            # @Description 获取全部消息
            result_list = []
            
            for map_dict in self.list:
                if tag in map_dict:
                    result_list.append(map_dict[tag])
            
            return result_list
    
    def getListSize(self) -> int:
        """
        @CreateTime 2022-04-17 00:44:04
        @Description 获取列表数量
        """
        return len(self.list)
    
    def getMsgSize(self, tag: Optional[str] = None) -> int:
        """
        @CreateTime 2022-02-19 14:45:06
        @Description 获取Msg数量
        """
        if tag is None:
            size = 0
            for map_dict in self.list:
                size += len(map_dict)
            return len(self.list) * size
        else:
            # @CreateTime 2022-05-01 14:35:55
            # @Description 获取Msg数量
            count = 0
            for map_dict in self.list:
                if tag in map_dict:
                    count += 1
            return count
    
    def has(self, tag: str) -> bool:
        """
        @CreateTime 2022-02-20 00:26:14
        @Description 存在消息Tag
        """
        for map_dict in self.list:
            if tag in map_dict:
                return True
        return False
    
    def insert(self, index: int, tag: str, value: str) -> 'Messenger':
        """
        @CreateTime 2022-04-30 22:27:24
        @Description 插入消息
        """
        if 0 <= index < len(self.list):
            self.list[index][tag] = value
        return self
    
    def add(self, 
               tag: Union[str, 'Messenger', List[Dict[str, str]], Dict[str, str]], 
               value: Optional[Union[str, Any]] = None) -> 'Messenger':
        """
        @CreateTime 2022-04-30 22:30:31
        @Description 增加消息
        """
        if tag is None:
            return self
        
        # 处理不同参数类型的情况
        if isinstance(tag, Messenger):
            if tag is not None:
                self.add(tag.list)
            return self
        elif isinstance(tag, list):
            self.list.extend(tag)
            return self
        elif isinstance(tag, dict):
            if tag is not None:
                for key, val in tag.items():
                    self.add(key, val)
            return self
        elif value is None:
            # @CreateTime 2022-03-05 07:07:44
            # @Description 增加消息类型
            return self.add(tag, tag)
        
        tag = str(tag)
        value = str(value) if value is not None else ""
        
        if not tag or not value:
            return self
        
        if tag == Msg.AtUin or tag == Msg.AtName or tag == Msg.AtAll:
            if tag == Msg.AtAll:
                pass  # 空语句块
            else:
                for map_dict in self.list:
                    if len(map_dict) == 1 and (Msg.AtUin in map_dict or Msg.AtName in map_dict):
                        if tag not in map_dict:
                            map_dict[tag] = value
                            return self
        else:
            if tag == Msg.Text or tag == Msg.Img or tag == Msg.Gif or tag == Msg.Emoid:
                pass  # 空语句块
            else:
                # 参与引索列表消息追加
                for map_dict in self.list:
                    if tag not in map_dict:
                        map_dict[tag] = value
                        return self
        
        map_dict = {tag: value}
        self.list.append(map_dict)
        return self
    
    def addArgs(self, tag: str, *values) -> 'Messenger':
        """
        @CreateTime 2022-05-02 21:54:33
        @Description 增加消息
        """
        append = ""
        for s in values:
            append += str(s)
        return self.addMsg(tag, append)
    
    def delMsg(self, tag: Optional[str] = None) -> 'Messenger':
        """
        @CreateTime 2022-02-19 12:01:19
        @Description 清除消息
        """
        if tag is None:
            # @CreateTime 2022-02-19 12:03:40
            # @Description 清除全部消息
            self.list.clear()
        else:
            for map_dict in self.list:
                if tag in map_dict:
                    del map_dict[tag]
        return self

    @staticmethod
    def getBaseMessenger(messenger: 'Messenger') -> 'Messenger':
        reply = Messenger()
        if messenger.has(Msg.Group):
            reply.add(Msg.Account, messenger.get(Msg.Account))
            reply.add(Msg.Group)
            reply.add(Msg.GroupId, messenger.get(Msg.GroupId))
        elif messenger.has(Msg.Friend):
            reply.add(Msg.Account, messenger.get(Msg.Account))
            reply.add(Msg.Friend)
            reply.add(Msg.Uin, messenger.get(Msg.Uin))
        elif messenger.has(Msg.Temp):
            reply.add(Msg.Account, messenger.get(Msg.Account))
            reply.add(Msg.Temp)
            reply.add(Msg.GroupId, messenger.get(Msg.GroupId))
            reply.add(Msg.Uin, messenger.get(Msg.Uin))
        elif messenger.has(Msg.Guild):
            reply.add(Msg.Account, messenger.get(Msg.Account))
            reply.add(Msg.Guild)
            reply.add(Msg.GuildId, messenger.get(Msg.GuildId))
            reply.add(Msg.ChannelId, messenger.get(Msg.ChannelId))
        else:
            raise TypeError("该消息类型暂不被支持处理")
        return reply

    def __str__(self) -> str:
        return str(self.list)

    def __repr__(self) -> str:
        return str(self.list)
