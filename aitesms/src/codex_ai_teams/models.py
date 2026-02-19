from dataclasses import dataclass
from enum import Enum


class AgentStatus(str, Enum):
    IDLE = "IDLE"
    STOPPED = "STOPPED"
    RUNNING = "RUNNING"
    DONE = "DONE"
    FAILED = "FAILED"


@dataclass
class AgentConfig:
    agent_id: str
    role: str
    temperature: float = 0.7
    role_prompt: str = ""
    codex_params: str = ""
    session_id: str = ""
    extra_params: str = ""
    enabled: bool = True


@dataclass
class AgentResult:
    agent_id: str
    role: str
    status: AgentStatus
    content: str


@dataclass
class AgentLogEvent:
    agent_id: str
    role: str
    status: AgentStatus
    message: str


@dataclass
class LogEntry:
    ts: str
    agent_id: str
    status: str
    level: str
    message: str
