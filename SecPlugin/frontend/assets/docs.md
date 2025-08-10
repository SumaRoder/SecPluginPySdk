# Plugin 类文档

## 一个基于 `websockets` 的异步插件框架，用于与 Secluded 服务端建立长连接，接收并处理 QQ（OneBot 协议）消息。支持文本、图片、链接等多种消息类型，提供注册消息处理器、心跳保活、日志记录、线程池并发执行等功能。

---

### 1. 快速开始

```python
from plugin import Plugin

bot = Plugin(
    ws_url="ws://127.0.0.1:6700",
    token="your-token",
    max_workers=4,
    log_send_wss=False
)

@bot.onMsg(r"^你好$")
async def hello(messenger):
    bot.sendMsg(messenger, "你好呀！")

bot.start(use_webui=False)   # 启动
```

---

### 2. 构造函数

```python
Plugin(ws_url: str,
       token: str,
       max_workers: int = 4,
       log_send_wss: bool = False)
```

参数	类型	说明	
`ws_url`	str	WebSocket 服务端地址	
`token`	str	鉴权 Token	
`max_workers`	int	线程池最大并发数，用于同步回调	
`log_send_wss`	bool	是否把 每帧发送 的 WSS 消息打印到 DEBUG 日志	

---

### 3. 主要属性

名称	类型	说明	
`running`	bool	插件是否处于运行状态	
`logger`	Logger	彩色日志器（同时输出到控制台与 `app.log`）	
`handlers`	dict	存储消息/命令回调的字典结构	

---

### 4. 公共方法

#### 4.1 生命周期

方法	说明	
`start(use_webui=False)`	启动插件。若 `use_webui=True`，额外启动一个基于 Flask 的 WebUI 线程	
`onClose()`	钩子：插件停止时调用，可被子类重写	
`onOpen()`	钩子：WebSocket 连接建立后向服务端发送 `SyncOicq` 上线包	

#### 4.2 消息发送

方法	说明	
`sendWss(cmd, data=None, rsp=True)`	向服务端发送一条原始 WSS 消息	
`sendMsg(messenger, text)`	快捷方法：对 `messenger` 发送纯文本回复	

#### 4.3 注册处理器

装饰器	说明	
`@bot.onMsg(regex)`	用正则匹配文本消息；匹配成功时执行回调。回调可接受 12 个参数：`messenger` 和 `re.Match`	
`@bot.onCmd(cmd)`	(预留) 用于注册命令回调	

---

### 5. 事件处理流程

```text
WebSocket 连接
       │
       ├─ onOpen() ─→ 发送 SyncOicq
       │
       ├─ 心跳：Heartbeat ⇄ Heartbeat
       │
       ├─ PushOicqMsg ─┬─ 系统消息 → onSystemMsgHandler
       │               └─ 用户消息 → onMsgHandler → doMsgHandler → 用户注册的 onMsg 回调
       │
       └─ Response → onRespMsgHandler
```

---

### 6. 日志系统

- 控制台：彩色分级输出
- 文件：`app.log`，UTF-8 编码，保留毫秒时间戳

日志方法：

```python
bot.log("hello", level=logging.INFO, tag="CustomTag")
```

---

### 7. 异常处理

所有顶层协程与回调都被 `try/except` 包裹，异常将自动写入日志文件并附带堆栈。

---

### 8. 线程与并发

组件	描述	
事件循环	单线程 `asyncio`	
同步回调	通过 `ThreadPoolExecutor(max_workers)` 在线程池中执行，防止阻塞事件循环	
线程安全	`seq_lock`、`handlers_lock` 保证序号与回调列表的并发安全	

---

### 9. WebUI（可选）

```python
bot.start(use_webui=True)
```

- 依赖：同级目录下的 `webui.py`
- 作用：提供基于浏览器的实时监控界面（日志、心跳、消息）

---

### 10. 示例：群聊复读机

```python
@bot.onMsg(r"^复读 (.+)$")
async def repeat(messenger, match):
    text = match.group(1)
    bot.sendMsg(messenger, text)
```

---

### 11. 目录结构建议

```
your_project/
├── plugin.py          # 本文件
├── messenger.py       # Messenger、Msg、Cmd 定义
├── webui.py           # WebUI（可选）
└── app.log            # 日志文件（自动生成）
```

---

### 12. 注意事项

1. 不要在回调里直接执行阻塞 IO；如需阻塞操作，使用线程池或异步库。
2. 正则匹配使用 `re.fullmatch`，请确保表达式覆盖整行。
3. Token 安全：勿将 Token 提交到版本控制。
4. Python 版本：≥ 3.10（使用 `match-case` 语法）。

---