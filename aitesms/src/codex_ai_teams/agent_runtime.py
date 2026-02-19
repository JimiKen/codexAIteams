import json
import subprocess
import time
from queue import Empty, Queue
from threading import Lock, Thread
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Callable, Dict, List, Optional, Tuple

from .models import AgentConfig, AgentLogEvent, AgentResult, AgentStatus


class AgentRuntimeManager:
    def __init__(self, agents: List[AgentConfig], project_root: Path) -> None:
        self.agents = agents
        self.project_root = project_root
        self._sessions: Dict[str, str] = {a.agent_id: (a.session_id or "") for a in agents}
        self._last_pid: Dict[str, int] = {a.agent_id: -1 for a in agents}
        self._active_procs: Dict[str, subprocess.Popen] = {}
        self._proc_lock = Lock()

        self.codex_js = Path(r"C:\Users\jimik\AppData\Roaming\npm\node_modules\@openai\codex\bin\codex.js")
        if not self.codex_js.exists():
            raise FileNotFoundError(f"codex.js not found: {self.codex_js}")

    def start(self) -> None:
        return

    def stop(self) -> None:
        with self._proc_lock:
            running_ids = list(self._active_procs.keys())
        for agent_id in running_ids:
            self.stop_agent(agent_id)

    def stop_agent(self, agent_id: str) -> bool:
        with self._proc_lock:
            proc = self._active_procs.get(agent_id)
        if proc is None or proc.poll() is not None:
            return False
        try:
            proc.terminate()
            proc.wait(timeout=3)
        except Exception:  # noqa: BLE001
            try:
                proc.kill()
            except Exception:  # noqa: BLE001
                pass
        finally:
            with self._proc_lock:
                self._active_procs.pop(agent_id, None)
        return True

    def runtime_info(self) -> Dict[str, int]:
        return dict(self._last_pid)

    def session_for(self, agent_id: str) -> str:
        sid = self._sessions.get(agent_id, "")
        return sid or f"{agent_id}-pending"

    def _build_prompt(self, agent: AgentConfig, text: str, work_path: str) -> str:
        role_prompt = agent.role_prompt.strip() or agent.role
        return (
            f"你是 {agent.agent_id.upper()}，角色：{agent.role}。\\n"
            f"角色要求：{role_prompt}\\n"
            f"当前工作路径固定为：{work_path}\\n"
            "回答规则：\\n"
            "1) 直接回答，不要寒暄。\\n"
            "2) 如果被问到工作路径，必须原样输出上面的完整路径。\\n"
            "3) 输出尽量简洁明确。\\n"
            "4) 若信息不足，先给出可执行的最小方案，再说明缺失条件。\\n"
            "5) 涉及改动时，优先给出可直接落地的步骤或命令。\\n"
            "6) 禁止编造不存在的文件、命令结果或外部事实。\\n"
            f"用户消息：{text}"
        )

    def _is_path_question(self, text: str) -> bool:
        lower = text.lower()
        return "工作路径" in text or "路径" in text or "path" in lower or "cwd" in lower

    def _stream_line(
        self,
        agent: AgentConfig,
        line: str,
        on_stream: Optional[Callable[[AgentLogEvent], None]],
        last_message_holder: Dict[str, str],
        thread_holder: Dict[str, str],
    ) -> None:
        line = line.strip()
        if not line:
            return
        if on_stream:
            on_stream(AgentLogEvent(agent.agent_id, agent.role, AgentStatus.RUNNING, f"CLI> {line}"))

        if not line.startswith("{"):
            return

        try:
            evt = json.loads(line)
        except Exception:
            return

        evt_type = evt.get("type")
        if evt_type == "thread.started":
            thread_holder["id"] = evt.get("thread_id", "")
            return

        if evt_type != "item.completed":
            return

        item = evt.get("item", {})
        item_type = item.get("type")
        if item_type == "agent_message":
            msg = (item.get("text") or "").strip()
            if msg:
                last_message_holder["text"] = msg
                if on_stream:
                    on_stream(AgentLogEvent(agent.agent_id, agent.role, AgentStatus.RUNNING, f"回复片段> {msg.splitlines()[0]}"))
        elif item_type == "error":
            msg = (item.get("message") or "").strip()
            if msg and on_stream:
                on_stream(AgentLogEvent(agent.agent_id, agent.role, AgentStatus.FAILED, f"CLI错误> {msg}"))

    def _run_one(
        self,
        agent: AgentConfig,
        text: str,
        work_path: str,
        timeout_sec: int,
        on_stream: Optional[Callable[[AgentLogEvent], None]],
    ) -> AgentResult:
        session_id = self._sessions.get(agent.agent_id, "").strip()
        prompt = self._build_prompt(agent, text, work_path)

        base = ["node", str(self.codex_js), "exec"]
        if session_id:
            cmd = base + ["resume", "--skip-git-repo-check", "--json", session_id, prompt]
        else:
            cmd = base + ["--skip-git-repo-check", "--json", prompt]

        if on_stream:
            on_stream(AgentLogEvent(agent.agent_id, agent.role, AgentStatus.RUNNING, f"启动CLI: {' '.join(cmd[:4])} ..."))

        try:
            p = subprocess.Popen(
                cmd,
                cwd=work_path,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                encoding="utf-8",
                errors="replace",
                bufsize=1,
            )
            self._last_pid[agent.agent_id] = p.pid
            with self._proc_lock:
                self._active_procs[agent.agent_id] = p
        except Exception as exc:  # noqa: BLE001
            return AgentResult(agent.agent_id, agent.role, AgentStatus.FAILED, f"外部 Codex CLI 启动失败: {exc}")

        last_message_holder = {"text": ""}
        thread_holder = {"id": ""}

        idle_timeout = max(20, timeout_sec)
        total_timeout = max(60, timeout_sec * 4)
        idle_deadline = time.time() + idle_timeout
        total_deadline = time.time() + total_timeout

        line_queue: "Queue[Optional[str]]" = Queue()

        def _stdout_reader() -> None:
            if not p.stdout:
                line_queue.put(None)
                return
            try:
                for raw in p.stdout:
                    line_queue.put(raw)
            finally:
                line_queue.put(None)

        reader = Thread(target=_stdout_reader, daemon=True)
        reader.start()

        while True:
            now = time.time()
            if now > total_deadline:
                p.kill()
                return AgentResult(agent.agent_id, agent.role, AgentStatus.FAILED, "外部 Codex CLI 总耗时超时")
            if now > idle_deadline:
                p.kill()
                return AgentResult(agent.agent_id, agent.role, AgentStatus.FAILED, "外部 Codex CLI 空闲超时")

            try:
                line = line_queue.get(timeout=0.1)
            except Empty:
                if p.poll() is not None:
                    break
                continue

            if line is None:
                if p.poll() is not None:
                    break
                continue

            if line:
                self._stream_line(agent, line, on_stream, last_message_holder, thread_holder)
                idle_deadline = time.time() + idle_timeout
                continue

            if p.poll() is not None:
                break

        return_code = p.returncode
        with self._proc_lock:
            self._active_procs.pop(agent.agent_id, None)
        if thread_holder["id"] and not self._sessions.get(agent.agent_id, "").strip():
            self._sessions[agent.agent_id] = thread_holder["id"]

        if return_code != 0:
            return AgentResult(agent.agent_id, agent.role, AgentStatus.FAILED, f"外部 Codex CLI 返回非零退出码: {return_code}")

        final_msg = last_message_holder["text"].strip()
        if not final_msg:
            return AgentResult(agent.agent_id, agent.role, AgentStatus.FAILED, "未获取到 Codex 回复")

        if self._is_path_question(text) and work_path not in final_msg:
            final_msg = f"当前工作路径是：{work_path}"

        return AgentResult(agent.agent_id, agent.role, AgentStatus.DONE, final_msg)

    def dispatch(
        self,
        targets: List[AgentConfig],
        text: str,
        work_path: str,
        timeout_sec: int = 60,
        on_stream: Optional[Callable[[AgentLogEvent], None]] = None,
    ) -> List[AgentResult]:
        work = Path(work_path)
        if not work.exists():
            work = self.project_root
        work_path_str = str(work)

        results: List[Tuple[int, AgentResult]] = []
        with ThreadPoolExecutor(max_workers=max(1, len(targets))) as pool:
            futs = {
                pool.submit(self._run_one, agent, text, work_path_str, timeout_sec, on_stream): idx
                for idx, agent in enumerate(targets)
            }
            for fut in as_completed(futs):
                idx = futs[fut]
                try:
                    result = fut.result()
                except Exception as exc:  # noqa: BLE001
                    agent = targets[idx]
                    result = AgentResult(agent.agent_id, agent.role, AgentStatus.FAILED, f"调度异常: {exc}")

                if result.status == AgentStatus.FAILED and "超时" in result.content:
                    agent = targets[idx]
                    retry_timeout = max(timeout_sec * 2, 120)
                    if on_stream:
                        on_stream(
                            AgentLogEvent(
                                agent_id=agent.agent_id,
                                role=agent.role,
                                status=AgentStatus.RUNNING,
                                message=f"检测到超时，自动重试一次（timeout={retry_timeout}s）",
                            )
                        )
                    result = self._run_one(agent, text, work_path_str, retry_timeout, on_stream)
                results.append((idx, result))

        results.sort(key=lambda x: x[0])
        return [r for _, r in results]
