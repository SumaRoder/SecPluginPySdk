import json
import logging
import re
from typing import Any, List, Optional, Union, TYPE_CHECKING
from typing_extensions import Protocol

from .msg import Msg
from .cmd import Cmd
from .logger import Logger
from .messenger import Messenger

class AbstractSender(Protocol):
    def running(self) -> bool:
        ...
    
    def get_logger(self) -> Logger:
        ...
    
    def get_local_send_wait_timeout(self) -> float:
        ...
    
    async def send_ws_msg(self, cmd: Cmd | str, data: dict | Messenger, rsp: bool = True, timeout: float = 0) -> Optional[dict]:
        ...

class Sender:
    def __init__(self, abstract_sender: AbstractSender) -> None:
        self._sender: AbstractSender = abstract_sender
        self._logger: Logger = abstract_sender.get_logger()

    def running(self) -> bool:
        return self._sender.running()
    
    async def send_ws_msg(self, cmd: Cmd | str, messenger: Messenger, rsp: bool = True) -> Any:
        return await self._sender.send_ws_msg(cmd, messenger, rsp)

    async def set_group_member_nick(self,
                                    messenger_or_qun: Messenger | str,
                                    uin: str,
                                    nick: str,
                                    account: Optional[str] = None
    ) -> None:
        if not self.running():
            return
        try:
            if isinstance(messenger_or_qun, Messenger):
                reply = Messenger.get_base_messenger(messenger_or_qun)
            else:
                reply = Messenger()
                reply.add_msg(Msg.Account, account)
                reply.add_msg(Msg.Group)
                reply.add_msg(Msg.GroupId, str(messenger_or_qun))
            reply.add_msg(Msg.GroupMemberNickModify) \
                 .add_msg(Msg.Uin, uin) \
                 .add_msg(Msg.Nick, nick)
            await self._sender.send_ws_msg(Cmd.SendOicqMsg, reply, rsp=False)
        except Exception as e:
            self._logger.error(e, tag="set_group_member_nick")

    async def withdraw(self, messenger_or_qun: Union['Messenger', str], msgId: str, account: str | None = None) -> Any:
        if not self.running():
            return
        try:
            if isinstance(messenger_or_qun, Messenger):
                reply = Messenger.get_base_messenger(messenger_or_qun)
            else:
                reply = Messenger()
                reply.add_msg(Msg.Account, account)
                reply.add_msg(Msg.Group)
                reply.add_msg(Msg.GroupId, str(messenger_or_qun))
            reply.add_msg(Msg.Withdraw, msgId)
            await self._sender.send_ws_msg(Cmd.SendOicqMsg, reply, rsp=False)
        except Exception as e:
            self._logger.error(e, tag="withdraw")

    async def send_json_card(self, messenger: 'Messenger', type: str, *args) -> Any:
        if not self.running():
            return
        try:
            reply = Messenger.get_base_messenger(messenger)
            reply.add_msg(Msg.CustomJson)
            reply.add_msg(type)
            arguments = [Msg.Title, Msg.Info, Msg.Img, Msg.Url, Msg.Audio]
            match type:
                case Msg.JSON_QQ:
                    for i in range(min(len(args), 5)):
                        reply.add_msg(arguments[i], args[i])
            return await self._sender.send_ws_msg(Cmd.SendOicqMsg, reply)
        except Exception as e:
            self._logger.error(e, tag="send_json_card")

    async def is_operator(self, messenger_or_qun: Messenger | str, uin: Optional[str] = None, account: Optional[str] = None) -> bool:
        if not self.running():
            raise RuntimeError("Plugin has not running")
        try:
            if isinstance(messenger_or_qun, Messenger):
                reply = Messenger.get_base_messenger(messenger_or_qun)
                if uin is None:
                    uin = messenger_or_qun.get_msg(Msg.Uin)
            else:
                reply = Messenger()
                reply.add_msg(Msg.Account, account)
                reply.add_msg(Msg.Group)
                reply.add_msg(Msg.GroupId, str(messenger_or_qun))
            reply.add_msg(Msg.GroupMemberListGetAdmin)
            operators = await self._sender.send_ws_msg(Cmd.SendOicqMsg, reply, rsp = True)
            if operators is None:
                return False
            operators = operators.get("data", [])
            if uin and uin in operators:
                return True
            return False
        except Exception as e:
            self._logger.error(e, tag="is_operator")
            return False

    async def get_group_list(self, messenger_or_account: Messenger | str) -> list[str]:
        if not self.running():
            raise RuntimeError("Plugin has not running")
        try:
            if isinstance(messenger_or_account, Messenger):
                reply = Messenger.get_base_messenger(messenger_or_account)
            else:
                reply = Messenger()
                reply.add_msg(Msg.Account, messenger_or_account)
                reply.add_msg(Msg.GroupListGet)
            group_list = await self._sender.send_ws_msg(Cmd.SendOicqMsg, reply, rsp = True)
            if group_list is None:
                return []
            return group_list.get("data", [])
        except Exception as e:
            self._logger.error(e, tag="get_group_list")
            return []

    async def send_msg(self, messenger: Messenger, *text: str, reply_msg_id: int = 0, in_one: bool = False) -> dict | list[dict]:
        if not self.running():
            raise RuntimeError("Plugin has not running")
        try:
            reply = Messenger.get_base_messenger(messenger)
            if reply_msg_id:
                reply.add_msg(Msg.Reply, reply_msg_id)
            if len(text) > 1:
                if in_one:
                    for u in text:
                        reply.add_msg(Msg.Text, u)
                    res = await self._sender.send_ws_msg(Cmd.SendOicqMsg, reply)
                    if res is None:
                        return {}
                    return res
                else:
                    res = []
                    for u in text:
                        if reply.has_msg(Msg.Text):
                            reply.del_msg(Msg.Text)
                        reply.add_msg(Msg.Text, u)
                        result = await self._sender.send_ws_msg(Cmd.SendOicqMsg, reply)
                        if result is None:
                            result = {}
                        res.append(result)
                    return res
            elif text:
                reply.add_msg(Msg.Text, text[0])
                res = await self._sender.send_ws_msg(Cmd.SendOicqMsg, reply)
                if res is None:
                    return {}
                return res
            else:
                raise TypeError("send_msg need attribute 'text' less than 1")
        except Exception as e:
            self._logger.error(e, tag = "send_text")
            return {}

    async def send_reply_msg(self, messenger: 'Messenger', *text: str, reply_msg_id: int = 0) -> dict | list[dict]:
        if not self.running():
            raise RuntimeError("Plugin has not running")
        try:
            if not reply_msg_id:
                reply_msg_id = messenger.get_msg(Msg.MsgId)
            return await self.send_msg(messenger, *text, reply_msg_id = reply_msg_id)
        except Exception as e:
            self._logger.error(e, tag="send_reply_msg")
            return {}

    async def send_card(self, messenger: Messenger, *json: tuple[str], in_one: bool = True) -> dict | list[dict]:
        if not self.running():
            raise RuntimeError("Plugin has not running")
        try:
            reply = Messenger.get_base_messenger(messenger)
            if len(json) > 1:
                if in_one:
                    for u in json:
                        reply.add_msg(Msg.Json, u)
                    res = await self._sender.send_ws_msg(Cmd.SendOicqMsg, reply)
                    if res is None:
                        return {}
                    return res
                else:
                    res = []
                    for u in json:
                        if reply.has_msg(Msg.Json):
                            reply.del_msg(Msg.Json)
                        reply.add_msg(Msg.Json, u)
                        result = await self._sender.send_ws_msg(Cmd.SendOicqMsg, reply)
                        if result is None:
                            result = {}
                        res.append(result)
                    return res
            elif json:
                reply.add_msg(Msg.Json, json[0])
                res = await self._sender.send_ws_msg(Cmd.SendOicqMsg, reply)
                if res is None:
                    return {}
                return res
            else:
                raise TypeError("send_json need less than 1")
        except Exception as e:
            self._logger.error(e, tag = "send_card")
            return {}

    async def send_img(self, messenger: Messenger, *url: tuple[str], in_one: bool = True) -> dict | list[dict]:
        if not self.running():
            raise RuntimeError("Plugin has not running")
        try:
            reply = Messenger.get_base_messenger(messenger)
            if len(url) > 1:
                if in_one:
                    for u in url:
                        reply.add_msg(Msg.Img, u)
                    res = await self._sender.send_ws_msg(Cmd.SendOicqMsg, reply)
                    if res is None:
                        return {}
                    return res
                else:
                    res = []
                    for u in url:
                        if reply.has_msg(Msg.Img):
                            reply.del_msg(Msg.Img)
                        reply.add_msg(Msg.Img, u)
                        result = await self._sender.send_ws_msg(Cmd.SendOicqMsg, reply)
                        if result is None:
                            result = {}
                        res.append(result)
                    return res
            elif url:
                reply.add_msg(Msg.Img, url[0])
                res = await self._sender.send_ws_msg(Cmd.SendOicqMsg, reply)
                if res is None:
                    return {}
                return res
            else:
                raise TypeError("send_img need less than 1")
        except Exception as e:
            self._logger.error(e, tag = "send_img")
            return {}
