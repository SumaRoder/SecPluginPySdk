from SecPlugin import *

plugin = Plugin(ws_url="ws://127.0.0.1:24804", token="SecretToken")

@plugin.onMsg("测试(.*)?")
def test(messenger: 'Messenger', matches):
    if matches:
        plugin.sendMsg(messenger, f"获取到：{matches.group(1)}")
    plugin.log("消息接收", tag="onTest")
    plugin.sendMsg(messenger, "成功")

@plugin.onMsg("异步测试(.*)?")
async def test_async(messenger: 'Messenger', matches):
    if matches:
        plugin.sendMsg(messenger, f"获取到：{matches.group(1)}")
    plugin.log("消息接收", tag="onTestAsync")
    plugin.sendMsg(messenger, "成功")

plugin.start(use_webui=True)