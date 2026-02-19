import time
from pathlib import Path

from .models import AgentConfig, AgentResult, AgentStatus


class BridgeAdapter:
    """Bridge 适配器占位实现：后续替换为真实 telegram bridge 请求。"""

    def __init__(self, bridge_url: str, timeout_sec: int, retry: int) -> None:
        self.bridge_url = bridge_url
        self.timeout_sec = timeout_sec
        self.retry = retry
        self._role_cn_map = {
            "pm": "项目经理",
            "fe": "前端工程师",
            "be": "后端工程师",
            "qa": "测试工程师",
        }

    def execute(self, agent: AgentConfig, task_text: str) -> AgentResult:
        time.sleep(0.6)
        role_cn = self._role_cn_map.get(agent.agent_id, agent.role)
        lower_text = task_text.lower()
        if "工作路径" in task_text or "work path" in lower_text or "cwd" in lower_text:
            content = (
                f"我是 {agent.agent_id.upper()} {role_cn}，当前工作路径是：{Path.cwd()}\n"
                "如果你希望我切换路径，请在‘文件’页面选择新的工作路径。"
            )
        else:
            content = (
                f"我是 {agent.agent_id.upper()} {role_cn}，已收到你的消息：{task_text}\n"
                f"我将按角色 Prompt 执行。temperature={agent.temperature}，session_id={agent.session_id or '-'}"
            )
        return AgentResult(agent_id=agent.agent_id, role=agent.role, status=AgentStatus.DONE, content=content)
