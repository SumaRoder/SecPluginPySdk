from enum import Enum

class Cmd(str, Enum):
    Sync        = "Sync"
    Response    = "Response"
    Heartbeat   = "Heartbeat"
    PushOicqMsg = "PushOicqMsg"
    SendOicqMsg = "SendOicqMsg"
