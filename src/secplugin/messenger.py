from typing import Any, List, Dict, Optional, Union
import copy
from .msg import Msg

class Messenger:
    def __init__(self, data: Optional[Union[str, 'Messenger', List[Dict[str, str]]]] = None):
        self.list: List[Dict[str, str]] = []

        if data is None:
            pass
        elif isinstance(data, str):
            self.add(data)
        elif isinstance(data, Messenger):
            if data.list is not None:
                self.list.extend(copy.deepcopy(data.list))
        elif isinstance(data, list):
            if data is not None:
                self.list.extend(data)

    def get(self, tag: Union[str, int], default: Any = "0") -> Any:
        if isinstance(tag, int):
            return self._get_by_index(tag, str(default), default)
        else:
            return self._get_by_tag(tag, default)

    def _get_by_tag(self, tag: str, default: Any = "0") -> Any:
        data = ""

        msg_list = self.get_list(tag)
        for msg in msg_list:
            data += msg

        return data if len(data) > 0 else default

    def _get_by_index(self, index: int, tag: str, default: Any = "0") -> Any:
        if len(self.list) > index:
            if tag in self.list[index]:
                return self.list[index][tag]
            else:
                return default
        else:
            return default

    def get_list(self, tag: Optional[str] = None) -> Union[List[Dict[str, str]], List[str]]:
        if tag is None:
            return self.list
        else:
            result_list = []

            for map_dict in self.list:
                if tag in map_dict:
                    result_list.append(map_dict[tag])

            return result_list

    def size(self, tag: Optional[str] = None, all=False) -> int:
        if tag is None:
            if all:
                size = 0
                for map_dict in self.list:
                    size += len(map_dict)
                return size
            else:
                return len(self.list)
        else:
            count = 0
            for map_dict in self.list:
                if tag in map_dict:
                    count += 1
            return count

    def has(self, tag: str) -> bool:
        for map_dict in self.list:
            if tag in map_dict:
                return True
        return False

    def insert(self, index: int, tag: str, value: str) -> 'Messenger':
        if 0 <= index < len(self.list):
            self.list[index][tag] = value
        return self

    def add(self,
            tag: Union[str, 'Messenger', List[Dict[str, str]], Dict[str, str]],
            value: Optional[Union[str, Any]] = None) -> 'Messenger':
        if tag is None:
            return self

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
            return self.add(tag, tag)

        tag = str(tag)
        value = str(value) if value is not None else ""

        if not tag or not value:
            return self

        if tag == Msg.AtUin or tag == Msg.AtName or tag == Msg.AtAll:
            if tag == Msg.AtAll:
                pass
            else:
                for map_dict in self.list:
                    if len(map_dict) == 1 and (Msg.AtUin in map_dict or Msg.AtName in map_dict):
                        if tag not in map_dict:
                            map_dict[tag] = value
                            return self
        else:
            if tag == Msg.Text or tag == Msg.Img or tag == Msg.Gif or tag == Msg.Emoid:
                pass
            else:
                for map_dict in self.list:
                    if tag not in map_dict:
                        map_dict[tag] = value
                        return self

        map_dict = {tag: value}
        self.list.append(map_dict)
        return self

    def add_args(self, tag: str, *values) -> 'Messenger':
        append = ""
        for s in values:
            append += str(s)
        return self.addMsg(tag, append)

    def del_msg(self, tag: Optional[str] = None) -> 'Messenger':
        if tag is None:
            self.list.clear()
        else:
            for map_dict in self.list:
                if tag in map_dict:
                    del map_dict[tag]
        return self

    @staticmethod
    def get_base_messenger(messenger: 'Messenger') -> 'Messenger':
        reply = Messenger()
        reply.add(Msg.Account, messenger.get(Msg.Account))
        if messenger.has(Msg.Group):
            reply.add(Msg.Group) \
                 .add(Msg.GroupId, messenger.get(Msg.GroupId))
        elif messenger.has(Msg.Friend):
            reply.add(Msg.Friend) \
                 .add(Msg.Uin, messenger.get(Msg.Uin))
        elif messenger.has(Msg.Temp):
            reply.add(Msg.Temp) \
                 .add(Msg.GroupId, messenger.get(Msg.GroupId)) \
                 .add(Msg.Uin, messenger.get(Msg.Uin))
        elif messenger.has(Msg.Guild):
            reply.add(Msg.Guild) \
                 .add(Msg.GuildId, messenger.get(Msg.GuildId)) \
                 .add(Msg.ChannelId, messenger.get(Msg.ChannelId))
        else:
            raise TypeError("该消息类型暂不支持处理")
        return reply

    @staticmethod
    def get_msg_type(messenger: 'Messenger') -> str:
        type = None
        if messenger and isinstance(messenger, Messenger) and messenger.getList():
            if messenger.has(Msg.Group):
                type = Msg.Group
            elif messenger.has(Msg.Friend):
                type = Msg.Friend
            elif messenger.has(Msg.Temp):
                type = Msg.Temp
            elif messenger.has(Msg.Guild):
                type = Msg.Guild
        return type

    def __str__(self) -> str:
        return json.dumps(self.list, )

    def __repr__(self) -> str:
        return str(self.list)
