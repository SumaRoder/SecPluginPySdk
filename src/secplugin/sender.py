import json
import logging
import re
from typing import Any, List, Union

from .msg import Msg
from .messenger import Messenger
from .cmd import Cmd

class Sender:
    def __init__(self, plugin):
        self._plugin = plugin

    async def set_group_member_nick(self, messenger_or_qun: Union['Messenger', str], uin: str, nick: str, account: str = None) -> None:
        if not self._plugin.running():
            return
        try:
            if isinstance(messenger_or_qun, Messenger):
                reply = Messenger.get_base_messenger(messenger_or_qun)
            else:
                reply = Messenger()
                reply.add(Msg.Account, account)
                reply.add(Msg.Group)
                reply.add(Msg.GroupId, str(messenger_or_qun))
            reply.add(Msg.GroupMemberNickModify) \
                 .add(Msg.Uin, uin) \
                 .add(Msg.Nick, nick)
            await self._plugin.send_ws_msg(Cmd.SendOicqMsg, reply, rsp=False)
        except Exception as e:
            self._plugin._logger.error(e, tag="set_group_member_nick")

    async def withdraw(self, messenger_or_qun: Union['Messenger', str], msgId: str, account: str = None) -> Any:
        if not self._plugin.running():
            return
        try:
            if isinstance(messenger_or_qun, Messenger):
                reply = Messenger.get_base_messenger(messenger_or_qun)
            else:
                reply = Messenger()
                reply.add(Msg.Account, account)
                reply.add(Msg.Group)
                reply.add(Msg.GroupId, str(messenger_or_qun))
            reply.add(Msg.Withdraw, msgId)
            await self._plugin.send_ws_msg(Cmd.SendOicqMsg, reply, rsp=False)
        except Exception as e:
            self._plugin._logger.error(e, tag="withdraw")
        return None

    async def send_json_card(self, messenger: 'Messenger', type: str, *args) -> Any:
        if not self._plugin.running():
            return
        try:
            reply = Messenger.get_base_messenger(messenger)
            reply.add(Msg.CustomJson)
            reply.add(type)
            arguments = [Msg.Title, Msg.Info, Msg.Img, Msg.Url, Msg.Audio]
            match type:
                case Msg.JSON_QQ:
                    for i in range(min(len(args), 5)):
                        reply.add(arguments[i], args[i])
            return await self._plugin.send_ws_msg(Cmd.SendOicqMsg, reply)
        except Exception as e:
            self._plugin._logger.error(e, tag="send_json_card")
        return None

    async def is_operator(self, messenger_or_qun: Union['Messenger', str], uin: str = None, account: str = None) -> bool:
        if not self._plugin.running():
            return False
        try:
            if isinstance(messenger_or_qun, Messenger):
                reply = Messenger.get_base_messenger(messenger_or_qun)
                if uin is None:
                    uin = messenger_or_qun.get(Msg.Uin)
            else:
                reply = Messenger()
                reply.add(Msg.Account, account)
                reply.add(Msg.Group)
                reply.add(Msg.GroupId, str(messenger_or_qun))
            reply.add(Msg.GroupMemberListGetAdmin)
            operators = await self._plugin.send_ws_msg(Cmd.SendOicqMsg, reply, rsp=True)
            if operators is None:
                return False
            operators = operators.get("data", [])
            for operator in operators:
                if operator.get(Msg.Uin, "") == uin:
                    return True
        except Exception as e:
            self._plugin._logger.error(e, tag="is_operator")
        return False

    async def get_group_list(self, account: str = None) -> bool:
        if not self._plugin.running():
            return False
        try:
            reply = Messenger()
            reply.add(Msg.Account, account)
            reply.add(Msg.GroupListGet)
            groupList = await self._plugin.send_ws_msg(Cmd.SendOicqMsg, reply, rsp=True)
            return groupList
        except Exception as e:
            self._plugin._logger.error(e, tag="get_group_list")

    async def send_msg(self, messenger: 'Messenger', *text: str, replyMsgId: int = 0) -> Any:
        if not self._plugin.running():
            return
        try:
            pattern = "\\[图片=(.+)\\]"
            result = []
            for t in text:
                if not t:
                    continue
                if isinstance(t, (dict, list)):
                    t = json.dumps(t, ensure_ascii=False)
                elif isinstance(t, Messenger):
                    t = json.dumps(t.getList(), ensure_ascii=False)
                elif isinstance(t, Exception):
                    t = self._plugin._format_exception(t)
                elif not isinstance(t, str):
                    t = str(t)
                matches = list(re.finditer(pattern, t))
                if matches:
                    last_end = 0
                    for match in matches:
                        start, end = match.span()
                        result.append(t[last_end:start])
                        result.append(f"[图片={match.group(1)}]")
                        last_end = end
                    result.append(t[last_end:])
                else:
                    result.append(t)
            reply = Messenger.get_base_messenger(messenger)
            for item in result:
                if item.startswith("[图片=") and item.endswith("]"):
                    link = item[4:-1]
                    reply.add(Msg.Img, link)
                else:
                    reply.add(Msg.Text, item)
            if replyMsgId:
                reply.add(Msg.Reply, replyMsgId)
            return await self._plugin.send_ws_msg(Cmd.SendOicqMsg, reply)
        except Exception as e:
            self._plugin._logger.error(e, tag="send_msg")

    async def send_reply_msg(self, messenger: 'Messenger', *text: str, replyMsgId: int = 0) -> Any:
        if not self._plugin.running():
            return
        try:
            if not replyMsgId:
                replyMsgId = messenger.get(Msg.MsgId)
            return self.send_msg(messenger, *text, replyMsgId=replyMsgId)
        except Exception as e:
            self._plugin._logger.error(e, tag="send_reply_msg")

    async def send_card(self, messenger: 'Messenger', *json_text: str) -> List[Any]:
        if not self._plugin.running():
            return
        try:
            reply = Messenger.get_base_messenger(messenger) \
                                .add(Msg.Json, jsont)
            return await self._plugin.send_ws_msg(Cmd.SendOicqMsg, reply)
        except Exception as e:
            self._plugin._logger.error(e, tag="send_card")

    async def send_img(self, messenger: 'Messenger', *url: str) -> Any:
        if not self._plugin.running():
            return
        try:
            for u in url:
                reply = Messenger.get_base_messenger(messenger) \
                                .add(Msg.Img, u)
            return await self._plugin.send_ws_msg(Cmd.SendOicqMsg, reply)
        except Exception as e:
            self._plugin._logger.error(e, tag="send_img", level=logging.ERROR)
