from __future__ import annotations
import json
from typing import Any, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from .sender import Sender

from .msg import Msg

class Messenger:
    def __init__(self, data: Optional[str | Messenger | list[dict[str, str]]] = None, sender: Optional[Sender] = None) -> None:
        self.list: list[dict[str, str]] = []
        if data is not None:
            if isinstance(data, str):
                self.add_msg(data)
            elif isinstance(data, Messenger):
                self.list.extend(data.list)
            elif isinstance(data, list):
                if data is not None:
                    self.list.extend(data)
        self._sender: Optional[Sender] = sender
        self._in_with: bool = False

    def get_msg(self, tag: str | int, default: Any = "0") -> Any:
        if isinstance(tag, int):
            return self._get_by_index(tag, str(default), default)
        else:
            return self._get_by_tag(tag, default)

    def _get_by_tag(self, tag: str, default: Any = "0") -> Any:
        data = ""
        msg_list = self.get_list(tag)
        for msg in msg_list:
            if isinstance(msg, dict):
                msg = json.dumps(msg)
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

    def get_list(self, tag: Optional[str] = None) -> list[dict[str, str]] | list[str]:
        if tag is None:
            return self.list
        else:
            result_list = []
            for map_dict in self.list:
                if tag in map_dict:
                    result_list.append(map_dict[tag])
            return result_list

    def size(self, tag: Optional[str] = None, all = False) -> int:
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

    def has_msg(self, tag: str) -> bool:
        for map_dict in self.list:
            if tag in map_dict:
                return True
        return False

    def insert(self, index: int, tag: str, value: str) -> Messenger:
        if 0 <= index < len(self.list):
            self.list[index][tag] = value
        return self

    def add_msg(self,
            tag: str | Messenger | list[dict[str, str]] | dict[str, str],
            value: Any = None
    ) -> Messenger:
        if tag is None:
            raise ValueError("tag 不能为空")

        if isinstance(tag, Messenger):
            if tag is not None:
                self.add_msg(tag.list)
            return self
        elif isinstance(tag, list):
            self.list.extend(tag)
            return self
        elif isinstance(tag, dict):
            if tag is not None:
                for key, val in tag.items():
                    self.add_msg(key, val)
            return self
        elif value is None:
            return self.add_msg(tag, tag)

        tag = str(tag)
        value = str(value) if value is not None else ""

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

    def add_args(self, tag: str, *values) -> Messenger:
        append = ""
        for s in values:
            append += str(s)
        return self.add_msg(tag, append)

    def del_msg(self, tag: Optional[str] = None) -> Messenger:
        if tag is None:
            self.list.clear()
        else:
            for map_dict in self.list:
                if tag in map_dict:
                    del map_dict[tag]
        return self

    @staticmethod
    def get_base_messenger(messenger: Messenger) -> Messenger:
        reply = Messenger()
        reply.add_msg(Msg.Account, messenger.get_msg(Msg.Account))
        if messenger.has_msg(Msg.Group):
            reply.add_msg(Msg.Group) \
                 .add_msg(Msg.GroupId, messenger.get_msg(Msg.GroupId))
        elif messenger.has_msg(Msg.Friend):
            reply.add_msg(Msg.Friend) \
                 .add_msg(Msg.Uin, messenger.get_msg(Msg.Uin))
        elif messenger.has_msg(Msg.Temp):
            reply.add_msg(Msg.Temp) \
                 .add_msg(Msg.GroupId, messenger.get_msg(Msg.GroupId)) \
                 .add_msg(Msg.Uin, messenger.get_msg(Msg.Uin))
        elif messenger.has_msg(Msg.Guild):
            reply.add_msg(Msg.Guild) \
                 .add_msg(Msg.GuildId, messenger.get_msg(Msg.GuildId)) \
                 .add_msg(Msg.ChannelId, messenger.get_msg(Msg.ChannelId))
        else:
            raise TypeError("该消息类型暂不支持处理")
        return reply

    @staticmethod
    def get_msg_type(messenger: Messenger) -> Optional[str]:
        type = None
        if messenger and isinstance(messenger, Messenger) and messenger.get_list():
            if messenger.has_msg(Msg.Group):
                type = Msg.Group
            elif messenger.has_msg(Msg.Friend):
                type = Msg.Friend
            elif messenger.has_msg(Msg.Temp):
                type = Msg.Temp
            elif messenger.has_msg(Msg.Guild):
                type = Msg.Guild
        return type

    def __len__(self) -> int:
        return self.size()

    def __str__(self) -> str:
        return json.dumps(self.list, ensure_ascii = False)

    def __repr__(self) -> str:
        return str(self.list)
    
    def __enter__(self) -> Messenger:
        self._in_with = True
        return self
    
    async def send_ws_msg(self, cmd: str, rsp: bool = False, sender: Optional[Sender] = None) -> Any:
        if not sender:
            if self._sender is None:
                raise RuntimeError("未绑定 Sender，无法发送消息")
            sender = self._sender
        if not sender.running():
            raise RuntimeError("Plugin has not running")
        return await sender.send_ws_msg(cmd, self, rsp)
    
    def __exit__(self, exc_type, exc_value, traceback) -> bool:
        return False
