from enum import Enum

class Cmd(str, Enum):
    SyncOicq = "SyncOicq"
    Response = "Response"
    Heartbeat = "Heartbeat"
    PushOicqMsg = "PushOicqMsg"
    SendOicqMsg = "SendOicqMsg"
