# 编写指南：https://spdocs.tbit.xin/

from SecPlugin import *

plugin = Plugin(ws_url="ws://127.0.0.1:24804", token="SecretToken")

@plugin.onMsg("测试")
def test(messenger: 'Messenger') -> None:
    plugin.sendMsg(messenger, "成功")

@plugin.onMsg("测试(.*)")
def test(messenger: 'Messenger', matches) -> None:
    plugin.sendMsg(str(matches.groups()))

plugin.start()