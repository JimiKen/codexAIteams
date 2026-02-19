from dataclasses import dataclass
from pathlib import Path
from typing import List

import yaml

from .models import AgentConfig


@dataclass
class BridgeSettings:
    bridge_type: str
    bridge_url: str
    timeout_sec: int
    retry: int
    telegram_token: str = ""
    telegram_chat_id: str = ""


@dataclass
class AppSettings:
    name: str
    max_agents: int


@dataclass
class Settings:
    app: AppSettings
    bridge: BridgeSettings
    agents: List[AgentConfig]


DEFAULT_AGENT_ORDER = ["pm", "fe", "be", "qa"]
DEFAULT_AGENT_SPECS = {
    "pm": {
        "role": "PM Agent",
        "role_prompt": "你是项目经理，先给结论再给计划，重点输出任务拆解、优先级、里程碑、风险与回滚方案。",
    },
    "fe": {
        "role": "Frontend Agent",
        "role_prompt": "你是前端工程师，负责界面交互、状态管理与可用性；优先保证易读、可操作、响应式和错误提示清晰。",
    },
    "be": {
        "role": "Backend Agent",
        "role_prompt": "你是后端工程师，负责接口、数据模型与稳定性；优先保证幂等性、错误边界、可观测性和兼容性。",
    },
    "qa": {
        "role": "QA Agent",
        "role_prompt": "你是测试工程师，负责测试设计与回归验证；重点覆盖主流程、边界场景、失败路径和验收标准。",
    },
}


def load_settings(config_path: Path) -> Settings:
    data = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    app = AppSettings(name=data["app"]["name"], max_agents=int(data["app"]["max_agents"]))
    bridge_data = data.get("bridge", {})
    bridge = BridgeSettings(
        bridge_type=bridge_data.get("type", "telegram_bridge"),
        bridge_url=bridge_data.get("bridge_url", "http://127.0.0.1:8080"),
        timeout_sec=int(bridge_data.get("timeout_sec", 90)),
        retry=int(bridge_data.get("retry", 2)),
        telegram_token=str(bridge_data.get("telegram_token", "")),
        telegram_chat_id=str(bridge_data.get("telegram_chat_id", "")),
    )
    loaded_agents = {
        str(item.get("id", "")).strip(): AgentConfig(
            agent_id=str(item.get("id", "")).strip(),
            role=str(item.get("role", "")),
            temperature=float(item.get("temperature", 0.7)),
            role_prompt=str(item.get("role_prompt", "")),
            codex_params=str(item.get("codex_params", "")),
            session_id=str(item.get("session_id", "")),
            extra_params=str(item.get("extra_params", "")),
            enabled=bool(item.get("enabled", True)),
        )
        for item in data.get("agents", [])
        if str(item.get("id", "")).strip()
    }
    agents: List[AgentConfig] = []
    for agent_id in DEFAULT_AGENT_ORDER:
        existing = loaded_agents.get(agent_id)
        if existing:
            if not existing.role:
                existing.role = DEFAULT_AGENT_SPECS[agent_id]["role"]
            if not existing.role_prompt:
                existing.role_prompt = DEFAULT_AGENT_SPECS[agent_id]["role_prompt"]
            agents.append(existing)
            continue
        spec = DEFAULT_AGENT_SPECS[agent_id]
        agents.append(AgentConfig(agent_id=agent_id, role=spec["role"], role_prompt=spec["role_prompt"]))

    if app.max_agents > 0:
        agents = agents[: max(app.max_agents, len(DEFAULT_AGENT_ORDER))]
    return Settings(app=app, bridge=bridge, agents=agents)


def save_settings(config_path: Path, settings: Settings) -> None:
    payload = {
        "app": {
            "name": settings.app.name,
            "max_agents": settings.app.max_agents,
        },
        "bridge": {
            "type": settings.bridge.bridge_type,
            "bridge_url": settings.bridge.bridge_url,
            "timeout_sec": settings.bridge.timeout_sec,
            "retry": settings.bridge.retry,
            "telegram_token": settings.bridge.telegram_token,
            "telegram_chat_id": settings.bridge.telegram_chat_id,
        },
        "agents": [
            {
                "id": agent.agent_id,
                "role": agent.role,
                "temperature": agent.temperature,
                "role_prompt": agent.role_prompt,
                "codex_params": agent.codex_params,
                "session_id": agent.session_id,
                "extra_params": agent.extra_params,
                "enabled": agent.enabled,
            }
            for agent in settings.agents
        ],
    }
    config_path.write_text(yaml.safe_dump(payload, sort_keys=False, allow_unicode=True), encoding="utf-8")
