import asyncio
from plugin.SecPlugin import SecPlugin

plugin = SecPlugin(
    ws_url="ws://127.0.0.1:24804",
    secret="SecretToken"
)

@plugin.onCmd("Response")
async def handle_response(data):
    print("Response:", data)

@plugin.onCmd("PushOicqMsg")
async def handle_push_oicq_msg(data):
    print("PushOicqMsg:", data)
    text = "\n".join([m.get("Text", "") for m in data.get("data", [])])
    if text.strip() == "插件测试":
        await plugin.sendMsg(data, "成功")

@plugin.onMsg(r"插件测试 (.*)")
async def handle_match(data, match):
    match_text = match.group(1)
    await plugin.sendMsg(data, match_text)

if __name__ == "__main__":
    plugin.start()
