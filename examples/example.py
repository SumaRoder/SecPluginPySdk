import asyncio
from secplugin import *

plugin = Plugin()
sender = plugin.get_sender()

@plugin.on_msg("测试")
async def test(messenger):
    await sender.send_msg(messenger, "成功")
    return "ok"

if __name__ == "__main__":
    plugin.run(
        url="ws://127.0.0.1:24804",
        pid="com.plugin.sumaroder",
        name="SecPlugin",
        token="SecretToken"
    )
