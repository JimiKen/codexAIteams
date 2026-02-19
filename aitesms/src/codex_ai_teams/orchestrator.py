from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from typing import Callable, List, Optional

from .bridge_adapter import BridgeAdapter
from .models import AgentConfig, AgentLogEvent, AgentResult, AgentStatus


class Orchestrator:
    def __init__(self, agents: List[AgentConfig], bridge: BridgeAdapter) -> None:
        self.agents = agents
        self.bridge = bridge

    def run_parallel(
        self,
        task_text: str,
        on_agent_update: Callable[[AgentResult], None],
        on_finished: Callable[[List[AgentResult]], None],
        on_agent_log: Optional[Callable[[AgentLogEvent], None]] = None,
    ) -> None:
        results: List[AgentResult] = []

        def emit_log(agent: AgentConfig, status: AgentStatus, msg: str) -> None:
            if on_agent_log:
                on_agent_log(AgentLogEvent(agent_id=agent.agent_id, role=agent.role, status=status, message=msg))

        def worker(agent: AgentConfig) -> AgentResult:
            emit_log(agent, AgentStatus.RUNNING, f"{datetime.now().strftime('%H:%M:%S')} 接收主任务")
            emit_log(agent, AgentStatus.RUNNING, f"{datetime.now().strftime('%H:%M:%S')} 开始执行，temperature={agent.temperature}")
            try:
                result = self.bridge.execute(agent, task_text)
            except Exception as exc:  # noqa: BLE001
                result = AgentResult(
                    agent_id=agent.agent_id,
                    role=agent.role,
                    status=AgentStatus.FAILED,
                    content=f"执行失败: {exc}",
                )
            emit_log(agent, result.status, f"{datetime.now().strftime('%H:%M:%S')} 执行结束: {result.status.value}")
            return result

        with ThreadPoolExecutor(max_workers=max(1, len(self.agents))) as pool:
            futures = {pool.submit(worker, agent): agent for agent in self.agents}
            for future in as_completed(futures):
                result = future.result()
                results.append(result)
                on_agent_update(result)

        on_finished(results)
