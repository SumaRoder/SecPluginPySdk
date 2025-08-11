# SecPlugin/__init__.py
"""
PluginDemo for Python
----------
import SecPlugin
plugin = SecPlugin.Plugin(ws_url="ws://127.0.0.1:24804", token="SecretToken")
@plugin.onMsg("测试")
async def test(msg, match):
    plugin.log("测试成功")
    await plugin.sendMsg("你好")
plugin.start(webui=True)
"""

__version__ = "1.1"
__author__ = "SumaRoder"
__all__ = ["Plugin", "Cmd", "Msg", "Messenger"]

from .plugin import Plugin
from .cmd import Cmd
from .msg import Msg
from .messenger import Messenger