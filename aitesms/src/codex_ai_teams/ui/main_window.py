import csv
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Set

from PySide6.QtCore import QEvent, QObject, Qt, Signal, QTimer
from PySide6.QtGui import QColor, QFont
from PySide6.QtWidgets import (
    QApplication,
    QComboBox,
    QFileDialog,
    QFileSystemModel,
    QFormLayout,
    QGridLayout,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QListWidget,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QSpinBox,
    QSplitter,
    QStackedWidget,
    QTableWidget,
    QTableWidgetItem,
    QTextEdit,
    QTreeView,
    QVBoxLayout,
    QWidget,
)

from ..agent_runtime import AgentRuntimeManager
from ..config import BridgeSettings, Settings, load_settings, save_settings
from ..models import AgentConfig, AgentLogEvent, AgentResult, AgentStatus, LogEntry
from .app_icon import load_app_icon


class EventBus(QObject):
    agent_updated = Signal(object)
    agent_log = Signal(object)
    terminal_output = Signal(str)
    command_finished = Signal()
    dialog_finished = Signal()


class MainWindow(QMainWindow):
    ROLE_CN_MAP = {
        "pm": "项目经理",
        "fe": "前端工程师",
        "be": "后端工程师",
        "qa": "测试工程师",
    }

    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("Codex AI Teams")
        self.resize(1440, 860)

        self.project_root = Path(__file__).resolve().parents[3]
        self.setWindowIcon(load_app_icon(self.project_root))
        self.config_path = self.project_root / "config" / "teams.yaml"
        self.settings = load_settings(self.config_path)
        self.runtime = AgentRuntimeManager(self.settings.agents, self.project_root)
        self.runtime.start()

        self.logs: List[LogEntry] = []
        self._agent_row_map: Dict[str, int] = {}
        self._row_agent_map: Dict[int, str] = {}
        self._agent_log_buffers: Dict[str, List[str]] = {}
        self._terminal_panels: Dict[str, QTextEdit] = {}
        self._status_combo_map: Dict[str, QComboBox] = {}
        self._stopped_agents: Set[str] = {a.agent_id for a in self.settings.agents if not a.enabled}
        self._exec_log_font = QFont("Consolas", 9)

        self._texts = {
            "zh": {
                "main_title": "Codex AI Teams",
                "lang": "语言",
                "menu_team": "团队列表",
                "menu_config": "配置",
                "menu_log": "日志",
                "menu_files": "文件",
                "menu_terminal": "终端",
                "team_members": "团队成员",
                "agent_table": "Agent 执行面板",
                "team_chat": "团队对话",
                "chat_target": "对话目标",
                "chat_all": "全部成员",
                "chat_ph": "输入消息，可群发或单发给指定成员",
                "send_chat": "发送消息",
                "warn_title": "提示",
                "warn_chat_empty": "请输入对话内容",
                "warn_no_active_agent": "目标成员处于 STOPPED，无法派发任务",
                "join_on": "参与",
                "join_off": "休息",
                "config_title": "配置中心",
                "save_config": "保存全部配置",
                "save_ok": "配置保存成功",
                "save_fail": "配置保存失败：{err}",
                "prompt_cfg": "角色 Prompt 配置",
                "prompt_target": "目标成员",
                "save_prompt": "保存 Prompt",
                "save_prompt_ok": "Prompt 已保存",
                "bridge_type": "Bridge 类型",
                "bridge_url": "Bridge 地址",
                "timeout": "超时(秒)",
                "retry": "重试次数",
                "telegram_token": "Telegram Token",
                "telegram_chat_id": "Telegram Chat ID",
                "agents_cfg": "Agent 参数",
                "col_agent": "Agent",
                "col_role": "角色",
                "col_status": "状态",
                "col_exec_log": "执行日志",
                "col_control": "参与设置",
                "control_join": "参与",
                "control_rest": "休息",
                "col_temp": "温度",
                "col_prompt": "角色 Prompt",
                "col_codex": "Codex 参数",
                "col_session": "Session ID",
                "col_extra": "其他参数",
                "col_enabled": "启用",
                "logs_title": "日志列表",
                "filter": "状态筛选",
                "all": "全部",
                "normal": "normal",
                "error": "error",
                "export_csv": "导出 CSV",
                "csv_ok": "日志已导出：{path}",
                "files_title": "文件浏览",
                "choose_path": "选择工作路径",
                "terminal_title": "终端",
                "cmd_ph": "输入命令并运行，例如：dir",
                "run_cmd": "运行命令",
                "running_cmd": "正在执行命令：{cmd}",
                "cmd_done": "命令执行完成",
            },
            "en": {
                "main_title": "Codex AI Teams",
                "lang": "Language",
                "menu_team": "Team",
                "menu_config": "Config",
                "menu_log": "Logs",
                "menu_files": "Files",
                "menu_terminal": "Terminal",
                "team_members": "Team Members",
                "agent_table": "Agent Execution Panel",
                "team_chat": "Team Chat",
                "chat_target": "Target",
                "chat_all": "All Members",
                "chat_ph": "Enter message for all or one member",
                "send_chat": "Send",
                "warn_title": "Notice",
                "warn_chat_empty": "Please enter a message",
                "warn_no_active_agent": "Target is STOPPED; cannot dispatch",
                "join_on": "Participate",
                "join_off": "Rest",
                "config_title": "Config Center",
                "save_config": "Save Config",
                "save_ok": "Config saved",
                "save_fail": "Save failed: {err}",
                "prompt_cfg": "Role Prompt",
                "prompt_target": "Target Agent",
                "save_prompt": "Save Prompt",
                "save_prompt_ok": "Prompt saved",
                "bridge_type": "Bridge Type",
                "bridge_url": "Bridge URL",
                "timeout": "Timeout(sec)",
                "retry": "Retry",
                "telegram_token": "Telegram Token",
                "telegram_chat_id": "Telegram Chat ID",
                "agents_cfg": "Agent Params",
                "col_agent": "Agent",
                "col_role": "Role",
                "col_status": "Status",
                "col_exec_log": "Execution Log",
                "col_control": "Participation",
                "control_join": "Join",
                "control_rest": "Rest",
                "col_temp": "Temperature",
                "col_prompt": "Role Prompt",
                "col_codex": "Codex Params",
                "col_session": "Session ID",
                "col_extra": "Extra Params",
                "col_enabled": "Enabled",
                "logs_title": "Logs",
                "filter": "Filter",
                "all": "all",
                "normal": "normal",
                "error": "error",
                "export_csv": "Export CSV",
                "csv_ok": "CSV exported: {path}",
                "files_title": "File Explorer",
                "choose_path": "Choose Work Path",
                "terminal_title": "Terminal",
                "cmd_ph": "Enter command, e.g. dir",
                "run_cmd": "Run Command",
                "running_cmd": "Running command: {cmd}",
                "cmd_done": "Command done",
            },
        }
        self._lang = "zh"

        self.bus = EventBus()
        self.bus.agent_updated.connect(self.handle_agent_update)
        self.bus.agent_log.connect(self.handle_agent_log)
        self.bus.terminal_output.connect(self._append_terminal_output)
        self.bus.command_finished.connect(self._on_command_finished)
        self.bus.dialog_finished.connect(self._on_dialog_finished)

        self._normal_color = QColor("#2ecc71")
        self._error_color = QColor("#ff4d4f")
        self._stopped_color = QColor("#faad14")
        self.logs_dir = self.project_root / "logs"
        self.logs_dir.mkdir(parents=True, exist_ok=True)
        self.runtime_log_path = self.logs_dir / "runtime.log"

        root = QWidget()
        self.setCentralWidget(root)
        self._apply_dark_style()

        base_layout = QHBoxLayout(root)
        splitter = QSplitter(Qt.Horizontal)
        base_layout.addWidget(splitter)

        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)

        lang_row = QHBoxLayout()
        self.lbl_lang = QLabel()
        self.lang_combo = QComboBox()
        self.lang_combo.addItem("中文", "zh")
        self.lang_combo.addItem("English", "en")
        self.lang_combo.currentIndexChanged.connect(self._on_lang_changed)
        lang_row.addWidget(self.lbl_lang)
        lang_row.addWidget(self.lang_combo)
        left_layout.addLayout(lang_row)

        self.menu_list = QListWidget()
        self.menu_list.currentRowChanged.connect(self._switch_page)
        left_layout.addWidget(self.menu_list, 1)

        self.pages = QStackedWidget()
        self.team_page = self._build_team_page()
        self.config_page = self._build_config_page()
        self.log_page = self._build_log_page()
        self.files_page = self._build_files_page()
        self.terminal_page = self._build_terminal_page()

        self.pages.addWidget(self.team_page)
        self.pages.addWidget(self.config_page)
        self.pages.addWidget(self.log_page)
        self.pages.addWidget(self.files_page)
        self.pages.addWidget(self.terminal_page)

        splitter.addWidget(left_panel)
        splitter.addWidget(self.pages)
        splitter.setSizes([250, 1190])

        self._refresh_i18n()
        self._reload_agent_rows()
        QTimer.singleShot(0, self._fit_agent_rows)

    def closeEvent(self, event):  # noqa: N802
        self._persist_settings()
        self.runtime.stop()
        super().closeEvent(event)

    def resizeEvent(self, event):  # noqa: N802
        super().resizeEvent(event)
        self._fit_agent_rows()

    def _apply_dark_style(self) -> None:
        self.setStyleSheet(
            """
            QMainWindow, QWidget { background-color: #000000; color: #FFFFFF; }
            QLabel { color: #FFFFFF; }
            QListWidget, QLineEdit, QTextEdit, QTableWidget, QComboBox, QSpinBox, QTreeView {
                background-color: #111111;
                color: #FFFFFF;
                border: 1px solid #333333;
                selection-background-color: #1f5f3b;
            }
            QPushButton {
                background-color: #1f1f1f;
                color: #FFFFFF;
                border: 1px solid #3a3a3a;
                padding: 6px 10px;
            }
            QPushButton:disabled {
                background-color: #151515;
                color: #999999;
            }
            QHeaderView::section {
                background-color: #111111;
                color: #FFFFFF;
                border: 1px solid #333333;
            }
            """
        )

    def _build_team_page(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)

        self.lbl_team_members = QLabel()
        self.lbl_team_members.hide()

        self.member_row = QHBoxLayout()
        holder = QWidget()
        holder.setLayout(self.member_row)
        layout.addWidget(holder)

        self.team_splitter = QSplitter(Qt.Vertical)

        table_block = QWidget()
        table_layout = QVBoxLayout(table_block)
        self.lbl_agent_table = QLabel()
        self.agent_table = QTableWidget(0, 5)
        self.agent_table.verticalHeader().setVisible(True)
        self.agent_table.verticalHeader().setSectionResizeMode(QHeaderView.Fixed)
        self.agent_table.verticalHeader().setDefaultSectionSize(105)
        self.agent_table.setWordWrap(True)
        # Keep four agents visible by default; allow scroll as fallback on small windows.
        self.agent_table.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        header = self.agent_table.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.Interactive)
        header.setSectionResizeMode(3, QHeaderView.Stretch)
        self.agent_table.setMinimumHeight(0)
        table_layout.addWidget(self.lbl_agent_table)
        table_layout.addWidget(self.agent_table)

        chat_block = QWidget()
        chat_layout = QVBoxLayout(chat_block)
        self.lbl_team_chat = QLabel()
        chat_layout.addWidget(self.lbl_team_chat)

        chat_top = QHBoxLayout()
        self.lbl_chat_target = QLabel()
        self.chat_target_combo = QComboBox()
        chat_top.addWidget(self.lbl_chat_target)
        chat_top.addWidget(self.chat_target_combo)
        chat_top.addStretch(1)
        chat_layout.addLayout(chat_top)

        self.chat_history = QTextEdit()
        self.chat_history.setReadOnly(True)
        self.chat_history.setMinimumHeight(180)
        chat_layout.addWidget(self.chat_history)

        chat_send_row = QHBoxLayout()
        self.chat_input = QTextEdit()
        self.chat_input.setMinimumHeight(88)
        self.chat_input.installEventFilter(self)
        self.send_chat_btn = QPushButton()
        self.send_chat_btn.clicked.connect(self.send_team_message)
        chat_send_row.addWidget(self.chat_input, 1)
        chat_send_row.addWidget(self.send_chat_btn)
        chat_layout.addLayout(chat_send_row)

        self.team_splitter.addWidget(table_block)
        self.team_splitter.addWidget(chat_block)
        self.team_splitter.setChildrenCollapsible(False)
        self.team_splitter.setStretchFactor(0, 4)
        self.team_splitter.setStretchFactor(1, 1)
        self.team_splitter.setSizes([700, 160])
        self.team_splitter.splitterMoved.connect(lambda *_: self._fit_agent_rows())
        layout.addWidget(self.team_splitter)
        return page

    def _build_config_page(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)

        self.lbl_config_title = QLabel()
        layout.addWidget(self.lbl_config_title)

        form = QFormLayout()
        self.cfg_bridge_type = QLineEdit()
        self.cfg_bridge_url = QLineEdit()
        self.cfg_timeout = QSpinBox()
        self.cfg_timeout.setRange(1, 9999)
        self.cfg_retry = QSpinBox()
        self.cfg_retry.setRange(0, 20)
        self.cfg_telegram_token = QLineEdit()
        self.cfg_telegram_chat_id = QLineEdit()
        self._cfg_bridge_type_label = QLabel()
        self._cfg_bridge_url_label = QLabel()
        self._cfg_timeout_label = QLabel()
        self._cfg_retry_label = QLabel()
        self._cfg_tg_token_label = QLabel()
        self._cfg_tg_chat_label = QLabel()
        form.addRow(self._cfg_bridge_type_label, self.cfg_bridge_type)
        form.addRow(self._cfg_bridge_url_label, self.cfg_bridge_url)
        form.addRow(self._cfg_timeout_label, self.cfg_timeout)
        form.addRow(self._cfg_retry_label, self.cfg_retry)
        form.addRow(self._cfg_tg_token_label, self.cfg_telegram_token)
        form.addRow(self._cfg_tg_chat_label, self.cfg_telegram_chat_id)
        layout.addLayout(form)

        self.lbl_agents_cfg = QLabel()
        self.cfg_agent_table = QTableWidget(0, 8)
        self.cfg_agent_table.verticalHeader().setVisible(False)
        self.cfg_agent_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        layout.addWidget(self.lbl_agents_cfg)
        layout.addWidget(self.cfg_agent_table)

        self.save_cfg_btn = QPushButton()
        self.save_cfg_btn.clicked.connect(self.save_config)
        layout.addWidget(self.save_cfg_btn)

        return page

    def _build_log_page(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)

        self.lbl_logs_title = QLabel()
        layout.addWidget(self.lbl_logs_title)

        top = QHBoxLayout()
        self.lbl_filter = QLabel()
        self.log_filter = QComboBox()
        self.log_filter.currentIndexChanged.connect(self._refresh_log_table)
        self.export_csv_btn = QPushButton()
        self.export_csv_btn.clicked.connect(self.export_logs_csv)
        top.addWidget(self.lbl_filter)
        top.addWidget(self.log_filter)
        top.addWidget(self.export_csv_btn)
        top.addStretch(1)
        layout.addLayout(top)

        self.logs_table = QTableWidget(0, 5)
        self.logs_table.setHorizontalHeaderLabels(["Time", "Agent", "Status", "Level", "Message"])
        self.logs_table.verticalHeader().setVisible(False)
        self.logs_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        layout.addWidget(self.logs_table)
        return page

    def _build_files_page(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)

        self.lbl_files_title = QLabel()
        layout.addWidget(self.lbl_files_title)

        top = QHBoxLayout()
        self.path_edit = QLineEdit(str(self.project_root))
        self.choose_path_btn = QPushButton()
        self.choose_path_btn.clicked.connect(self.choose_work_path)
        top.addWidget(self.path_edit)
        top.addWidget(self.choose_path_btn)
        layout.addLayout(top)

        self.fs_model = QFileSystemModel(self)
        self.fs_model.setRootPath(str(self.project_root))
        self.file_tree = QTreeView()
        self.file_tree.setModel(self.fs_model)
        self.file_tree.setRootIndex(self.fs_model.index(str(self.project_root)))
        layout.addWidget(self.file_tree)
        return page

    def _build_terminal_page(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)

        self.lbl_terminal_title = QLabel()
        layout.addWidget(self.lbl_terminal_title)

        top = QHBoxLayout()
        self.cmd_input = QLineEdit()
        self.run_cmd_btn = QPushButton()
        self.run_cmd_btn.clicked.connect(self.run_command)
        top.addWidget(self.cmd_input)
        top.addWidget(self.run_cmd_btn)
        layout.addLayout(top)

        self.terminal_grid_holder = QWidget()
        self.terminal_grid = QGridLayout(self.terminal_grid_holder)
        self.terminal_grid.setContentsMargins(0, 0, 0, 0)
        self.terminal_grid.setHorizontalSpacing(10)
        self.terminal_grid.setVerticalSpacing(10)
        layout.addWidget(self.terminal_grid_holder, 1)

        self.terminal_output = QTextEdit()
        self.terminal_output.setReadOnly(True)
        self.terminal_output.setPlaceholderText("系统命令输出")
        self.terminal_output.setMaximumHeight(150)
        layout.addWidget(self.terminal_output)
        return page

    def _on_lang_changed(self) -> None:
        self._lang = self.lang_combo.currentData()
        self._refresh_i18n()
        self._reload_agent_rows()

    def _refresh_i18n(self) -> None:
        t = self._texts[self._lang]
        self.setWindowTitle(t["main_title"])
        self.lbl_lang.setText(t["lang"])

        self.menu_list.clear()
        self.menu_list.addItems([t["menu_team"], t["menu_config"], t["menu_log"], t["menu_files"], t["menu_terminal"]])
        self.menu_list.setCurrentRow(0)

        self.lbl_agent_table.setText(t["agent_table"])
        self.agent_table.setHorizontalHeaderLabels(
            [t["col_agent"], t["col_role"], t["col_status"], t["col_exec_log"], t["col_control"]]
        )
        self.lbl_team_chat.setText(t["team_chat"])
        self.lbl_chat_target.setText(t["chat_target"])
        self.chat_input.setPlaceholderText(t["chat_ph"])
        self.send_chat_btn.setText(t["send_chat"])

        self.lbl_config_title.setText(t["config_title"])
        self._cfg_bridge_type_label.setText(t["bridge_type"])
        self._cfg_bridge_url_label.setText(t["bridge_url"])
        self._cfg_timeout_label.setText(t["timeout"])
        self._cfg_retry_label.setText(t["retry"])
        self._cfg_tg_token_label.setText(t["telegram_token"])
        self._cfg_tg_chat_label.setText(t["telegram_chat_id"])
        self.lbl_agents_cfg.setText(t["agents_cfg"])
        self.cfg_agent_table.setHorizontalHeaderLabels(
            [
                t["col_agent"],
                t["col_role"],
                t["col_temp"],
                t["col_prompt"],
                t["col_codex"],
                t["col_session"],
                t["col_extra"],
                t["col_enabled"],
            ]
        )
        self.save_cfg_btn.setText(t["save_config"])

        self.lbl_logs_title.setText(t["logs_title"])
        self.lbl_filter.setText(t["filter"])
        self.log_filter.blockSignals(True)
        self.log_filter.clear()
        self.log_filter.addItem(t["all"], "all")
        self.log_filter.addItem(t["normal"], "normal")
        self.log_filter.addItem(t["error"], "error")
        self.log_filter.blockSignals(False)
        self.export_csv_btn.setText(t["export_csv"])

        self.lbl_files_title.setText(t["files_title"])
        self.choose_path_btn.setText(t["choose_path"])

        self.lbl_terminal_title.setText(t["terminal_title"])
        self.cmd_input.setPlaceholderText(t["cmd_ph"])
        self.run_cmd_btn.setText(t["run_cmd"])

    def _switch_page(self, idx: int) -> None:
        if idx >= 0:
            self.pages.setCurrentIndex(idx)
            if idx == 0:
                QTimer.singleShot(0, self._fit_agent_rows)
                QTimer.singleShot(80, self._fit_agent_rows)

    def eventFilter(self, watched, event):  # noqa: N802
        if watched is self.chat_input and event.type() == QEvent.KeyPress:
            if event.key() in (Qt.Key_Return, Qt.Key_Enter):
                if event.modifiers() & Qt.ShiftModifier:
                    return False
                self.send_team_message()
                return True
        if watched is self.agent_table.viewport() and event.type() == QEvent.Resize:
            QTimer.singleShot(0, self._fit_agent_rows)
        return super().eventFilter(watched, event)

    def _role_cn(self, agent: AgentConfig) -> str:
        return self.ROLE_CN_MAP.get(agent.agent_id, agent.role)

    def _reload_agent_rows(self) -> None:
        while self.member_row.count():
            item = self.member_row.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()

        self.agent_table.setRowCount(len(self.settings.agents))
        self.cfg_agent_table.setRowCount(len(self.settings.agents))
        self._agent_row_map.clear()
        self._row_agent_map.clear()
        self._agent_log_buffers.clear()
        self._terminal_panels.clear()
        self._status_combo_map.clear()
        self._stopped_agents = {a.agent_id for a in self.settings.agents if not a.enabled}

        self.chat_target_combo.clear()
        self.chat_target_combo.addItem(self._texts[self._lang]["chat_all"], "__all__")

        for i, agent in enumerate(self.settings.agents):
            self._agent_row_map[agent.agent_id] = i
            self._row_agent_map[i] = agent.agent_id
            self._agent_log_buffers[agent.agent_id] = []

            self.chat_target_combo.addItem(f"{agent.agent_id} ({self._role_cn(agent)})", agent.agent_id)

            badge = QLabel(f"{agent.agent_id}（{self._role_cn(agent)}）")
            badge.setStyleSheet("padding:4px 8px;border:1px solid #2ecc71;color:#2ecc71;")
            self.member_row.addWidget(badge)

            self.agent_table.setItem(i, 0, QTableWidgetItem(agent.agent_id))
            self.agent_table.setItem(i, 1, QTableWidgetItem(f"{agent.role} / {self._role_cn(agent)}"))
            self._init_status_combo(i, agent.agent_id)
            self._set_agent_status(i, AgentStatus.STOPPED.value if agent.agent_id in self._stopped_agents else AgentStatus.IDLE.value)
            self.agent_table.setItem(i, 3, self._make_exec_log_item(""))

            self.cfg_agent_table.setItem(i, 0, QTableWidgetItem(agent.agent_id))
            self.cfg_agent_table.setItem(i, 1, QTableWidgetItem(agent.role))
            self.cfg_agent_table.setItem(i, 2, QTableWidgetItem(str(agent.temperature)))
            self.cfg_agent_table.setItem(i, 3, QTableWidgetItem(agent.role_prompt))
            self.cfg_agent_table.setItem(i, 4, QTableWidgetItem(agent.codex_params))
            self.cfg_agent_table.setItem(i, 5, QTableWidgetItem(agent.session_id))
            self.cfg_agent_table.setItem(i, 6, QTableWidgetItem(agent.extra_params))
            self.cfg_agent_table.setItem(i, 7, QTableWidgetItem("true" if agent.enabled else "false"))

        self.member_row.addStretch(1)
        self._rebuild_terminal_panels()
        self.agent_table.viewport().installEventFilter(self)

        self.cfg_bridge_type.setText(self.settings.bridge.bridge_type)
        self.cfg_bridge_url.setText(self.settings.bridge.bridge_url)
        self.cfg_timeout.setValue(self.settings.bridge.timeout_sec)
        self.cfg_retry.setValue(self.settings.bridge.retry)
        self.cfg_telegram_token.setText(self.settings.bridge.telegram_token)
        self.cfg_telegram_chat_id.setText(self.settings.bridge.telegram_chat_id)

        pid_map = self.runtime.runtime_info()
        for agent in self.settings.agents:
            pid = pid_map.get(agent.agent_id, -1)
            self._append_agent_log_line(agent.agent_id, f"独立CLI进程 PID={pid}, session_id={self.runtime.session_for(agent.agent_id)}")
        self._fit_agent_rows()

    def _rebuild_terminal_panels(self) -> None:
        while self.terminal_grid.count():
            item = self.terminal_grid.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()

        self._terminal_panels.clear()
        for idx, agent in enumerate(self.settings.agents[:4]):
            block = QWidget()
            block_layout = QVBoxLayout(block)
            block_layout.setContentsMargins(0, 0, 0, 0)
            title = QLabel(f"{agent.agent_id.upper()} / {self._role_cn(agent)}")
            panel = QTextEdit()
            panel.setReadOnly(True)
            panel.setPlaceholderText(f"{agent.agent_id} 终端输出")
            panel.setFont(self._exec_log_font)
            block_layout.addWidget(title)
            block_layout.addWidget(panel)
            self.terminal_grid.addWidget(block, idx // 2, idx % 2)
            self._terminal_panels[agent.agent_id] = panel

        self.terminal_grid.setRowStretch(0, 1)
        self.terminal_grid.setRowStretch(1, 1)
        self.terminal_grid.setColumnStretch(0, 1)
        self.terminal_grid.setColumnStretch(1, 1)

    def _append_agent_terminal_line(self, agent_id: str, line: str) -> None:
        panel = self._terminal_panels.get(agent_id)
        if panel is not None:
            panel.append(line)

    def _fit_agent_rows(self) -> None:
        row_count = self.agent_table.rowCount()
        if row_count <= 0:
            return
        viewport_height = max(1, self.agent_table.viewport().height())
        visible_rows = min(4, row_count)
        row_height = max(52, min(112, int((viewport_height - 8) / visible_rows)))
        for row in range(row_count):
            self.agent_table.setRowHeight(row, row_height)

    def _init_status_combo(self, row: int, agent_id: str) -> None:
        combo = QComboBox()
        t = self._texts[self._lang]
        combo.addItem(t["control_join"], AgentStatus.RUNNING.value)
        combo.addItem(t["control_rest"], AgentStatus.STOPPED.value)
        combo.setCurrentIndex(1 if agent_id in self._stopped_agents else 0)
        combo.currentIndexChanged.connect(lambda _idx, aid=agent_id, c=combo: self._on_status_changed(aid, str(c.currentData())))
        self.agent_table.setCellWidget(row, 4, combo)
        self._status_combo_map[agent_id] = combo
        self._set_status_combo_color(combo, str(combo.currentData()))

    def _set_status_combo_color(self, combo: QComboBox, status: str) -> None:
        if status == AgentStatus.FAILED.value:
            color = self._error_color.name()
        elif status == AgentStatus.STOPPED.value:
            color = self._stopped_color.name()
        else:
            color = self._normal_color.name()
        combo.setStyleSheet(f"color: {color};")

    def _on_status_changed(self, agent_id: str, status: str) -> None:
        combo = self._status_combo_map.get(agent_id)
        if combo:
            self._set_status_combo_color(combo, status)
        row = self._agent_row_map.get(agent_id)
        agent = next((a for a in self.settings.agents if a.agent_id == agent_id), None)

        if status == AgentStatus.STOPPED.value:
            self._stopped_agents.add(agent_id)
            if agent:
                agent.enabled = False
            if row is not None:
                self.cfg_agent_table.setItem(row, 7, QTableWidgetItem("false"))
                self._set_agent_status(row, AgentStatus.STOPPED.value)
            stopped = self.runtime.stop_agent(agent_id)
            msg = "已切换为 STOPPED，后续不会派发任务"
            if stopped:
                msg = "已切换为 STOPPED，并停止当前执行中的任务"
            self._append_agent_log_line(agent_id, msg)
            self._add_log(agent_id, AgentStatus.STOPPED.value, msg)
            return

        if agent_id in self._stopped_agents:
            self._stopped_agents.discard(agent_id)
            if agent:
                agent.enabled = True
            if row is not None:
                self.cfg_agent_table.setItem(row, 7, QTableWidgetItem("true"))
                self._set_agent_status(row, AgentStatus.IDLE.value)
            msg = f"已从 STOPPED 恢复为 {status}"
            self._append_agent_log_line(agent_id, msg)
            self._add_log(agent_id, status, msg)

    def _set_agent_status(self, row: int, status: str) -> None:
        agent_id = self._row_agent_map.get(row)
        if not agent_id:
            return

        if agent_id in self._stopped_agents and status != AgentStatus.STOPPED.value:
            return

        item = QTableWidgetItem(status)
        if status == AgentStatus.FAILED.value:
            item.setForeground(self._error_color)
        elif status == AgentStatus.STOPPED.value:
            item.setForeground(self._stopped_color)
        else:
            item.setForeground(self._normal_color)
        self.agent_table.setItem(row, 2, item)

    def _append_agent_log_line(self, agent_id: str, line: str) -> None:
        buf = self._agent_log_buffers.get(agent_id)
        if buf is None:
            return
        buf.append(line)
        if len(buf) > 40:
            del buf[0]
        row = self._agent_row_map.get(agent_id)
        if row is not None:
            self.agent_table.setItem(row, 3, self._make_exec_log_item("\n".join(buf)))
        self._append_agent_terminal_line(agent_id, line)

    def _make_exec_log_item(self, text: str) -> QTableWidgetItem:
        item = QTableWidgetItem(text)
        item.setFont(self._exec_log_font)
        return item

    def _add_log(self, agent_id: str, status: str, message: str) -> None:
        level = "error" if status == AgentStatus.FAILED.value else "normal"
        ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.logs.append(
            LogEntry(
                ts=ts,
                agent_id=agent_id,
                status=status,
                level=level,
                message=message,
            )
        )
        try:
            with self.runtime_log_path.open("a", encoding="utf-8") as f:
                f.write(f"{ts}\t{agent_id}\t{status}\t{level}\t{message}\n")
        except Exception:
            pass
        self._refresh_log_table()

    def _refresh_log_table(self) -> None:
        selected = str(self.log_filter.currentData()) if self.log_filter.count() else "all"
        rows = [x for x in self.logs if selected == "all" or x.level == selected]
        self.logs_table.setRowCount(len(rows))
        for i, x in enumerate(rows):
            self.logs_table.setItem(i, 0, QTableWidgetItem(x.ts))
            self.logs_table.setItem(i, 1, QTableWidgetItem(x.agent_id))
            self.logs_table.setItem(i, 2, QTableWidgetItem(x.status))
            level_item = QTableWidgetItem(x.level)
            level_item.setForeground(self._error_color if x.level == "error" else self._normal_color)
            self.logs_table.setItem(i, 3, level_item)
            self.logs_table.setItem(i, 4, QTableWidgetItem(x.message))

    def send_team_message(self) -> None:
        text = self.chat_input.toPlainText().strip()
        t = self._texts[self._lang]
        if not text:
            QMessageBox.warning(self, t["warn_title"], t["warn_chat_empty"])
            return

        target_id = self.chat_target_combo.currentData()
        self.send_chat_btn.setEnabled(False)
        self.chat_input.clear()

        if target_id == "__all__":
            targets = [a for a in self.settings.agents if a.agent_id not in self._stopped_agents]
        else:
            targets = [a for a in self.settings.agents if a.agent_id == target_id and a.agent_id not in self._stopped_agents]

        if not targets:
            self.send_chat_btn.setEnabled(True)
            QMessageBox.warning(self, t["warn_title"], t["warn_no_active_agent"])
            return

        for agent in targets:
            row = self._agent_row_map.get(agent.agent_id)
            if row is not None:
                self._set_agent_status(row, AgentStatus.RUNNING.value)
            self.bus.agent_log.emit(AgentLogEvent(agent.agent_id, agent.role, AgentStatus.RUNNING, f"收到对话：{text}"))

        import threading

        def worker() -> None:
            try:
                results = self.runtime.dispatch(
                    targets=targets,
                    text=text,
                    work_path=self.path_edit.text().strip() or str(self.project_root),
                    timeout_sec=max(30, self.settings.bridge.timeout_sec),
                    on_stream=self.bus.agent_log.emit,
                )
                for result in results:
                    self.bus.agent_updated.emit(result)
            finally:
                self.bus.dialog_finished.emit()

        threading.Thread(target=worker, daemon=True).start()

    def handle_agent_log(self, event: AgentLogEvent) -> None:
        self._append_agent_log_line(event.agent_id, event.message)
        self._add_log(event.agent_id, event.status.value, event.message)

    def handle_agent_update(self, result: AgentResult) -> None:
        row = self._agent_row_map.get(result.agent_id)
        if row is not None:
            self._set_agent_status(row, result.status.value)
        short = result.content.splitlines()[0] if result.content else ""
        self._append_agent_log_line(result.agent_id, f"结果：{short}")
        self._add_log(result.agent_id, result.status.value, result.content)
        role_cn = next((self._role_cn(a) for a in self.settings.agents if a.agent_id == result.agent_id), result.role)
        self.chat_history.append(f"[{result.agent_id.upper()} {role_cn}] {result.content.strip()}")
        if result.content.strip():
            self._append_agent_terminal_line(result.agent_id, f"最终回复:\n{result.content.strip()}")
        sid = self.runtime.session_for(result.agent_id)
        sid_updated = False
        for agent in self.settings.agents:
            if agent.agent_id == result.agent_id and "pending" not in sid:
                if agent.session_id != sid:
                    agent.session_id = sid
                    sid_updated = True
                break
        if row is not None and "pending" not in sid:
            self.cfg_agent_table.setItem(row, 5, QTableWidgetItem(sid))
        if sid_updated:
            self._persist_settings()

    def _on_dialog_finished(self) -> None:
        self.send_chat_btn.setEnabled(True)

    def save_config(self) -> None:
        t = self._texts[self._lang]
        try:
            agents: List[AgentConfig] = []
            for row in range(self.cfg_agent_table.rowCount()):
                agent_id = self.cfg_agent_table.item(row, 0).text().strip()
                role = self.cfg_agent_table.item(row, 1).text().strip()
                temperature = float(self.cfg_agent_table.item(row, 2).text().strip())
                role_prompt = self.cfg_agent_table.item(row, 3).text().strip()
                codex_params = self.cfg_agent_table.item(row, 4).text().strip()
                session_id = self.cfg_agent_table.item(row, 5).text().strip()
                extra_params = self.cfg_agent_table.item(row, 6).text().strip()
                enabled_raw = self.cfg_agent_table.item(row, 7).text().strip().lower()
                enabled = enabled_raw in {"1", "true", "yes", "y", "on"}
                agents.append(
                    AgentConfig(
                        agent_id=agent_id,
                        role=role,
                        temperature=temperature,
                        role_prompt=role_prompt,
                        codex_params=codex_params,
                        session_id=session_id,
                        extra_params=extra_params,
                        enabled=enabled,
                    )
                )

            self.settings = Settings(
                app=self.settings.app,
                bridge=BridgeSettings(
                    bridge_type=self.cfg_bridge_type.text().strip(),
                    bridge_url=self.cfg_bridge_url.text().strip(),
                    timeout_sec=self.cfg_timeout.value(),
                    retry=self.cfg_retry.value(),
                    telegram_token=self.cfg_telegram_token.text().strip(),
                    telegram_chat_id=self.cfg_telegram_chat_id.text().strip(),
                ),
                agents=agents,
            )
            save_settings(self.config_path, self.settings)
            self.runtime.stop()
            self.runtime = AgentRuntimeManager(self.settings.agents, self.project_root)
            self.runtime.start()
            self._reload_agent_rows()
            QMessageBox.information(self, t["warn_title"], t["save_ok"])
        except Exception as exc:  # noqa: BLE001
            QMessageBox.critical(self, t["warn_title"], t["save_fail"].format(err=str(exc)))

    def _persist_settings(self) -> None:
        try:
            save_settings(self.config_path, self.settings)
        except Exception:
            pass

    def export_logs_csv(self) -> None:
        logs_dir = self.project_root / "logs"
        logs_dir.mkdir(parents=True, exist_ok=True)
        path = logs_dir / f"logs_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        with path.open("w", newline="", encoding="utf-8-sig") as f:
            writer = csv.writer(f)
            writer.writerow(["time", "agent", "status", "level", "message"])
            for row in self.logs:
                writer.writerow([row.ts, row.agent_id, row.status, row.level, row.message])
        QMessageBox.information(self, self._texts[self._lang]["warn_title"], self._texts[self._lang]["csv_ok"].format(path=path))

    def choose_work_path(self) -> None:
        chosen = QFileDialog.getExistingDirectory(self, self._texts[self._lang]["choose_path"], self.path_edit.text().strip())
        if chosen:
            self.path_edit.setText(chosen)
            self.file_tree.setRootIndex(self.fs_model.index(chosen))

    def run_command(self) -> None:
        cmd = self.cmd_input.text().strip()
        if not cmd:
            return
        self.run_cmd_btn.setEnabled(False)
        self.terminal_output.clear()
        self.bus.terminal_output.emit(self._texts[self._lang]["running_cmd"].format(cmd=cmd))

        import threading

        def worker() -> None:
            try:
                try:
                    proc = subprocess.Popen(
                        ["powershell", "-NoProfile", "-Command", cmd],
                        shell=False,
                        cwd=self.path_edit.text().strip() or str(self.project_root),
                        stdout=subprocess.PIPE,
                        stderr=subprocess.STDOUT,
                        text=True,
                        encoding="utf-8",
                        errors="replace",
                        bufsize=1,
                    )
                except Exception:
                    proc = subprocess.Popen(
                        cmd,
                        shell=True,
                        cwd=self.path_edit.text().strip() or str(self.project_root),
                        stdout=subprocess.PIPE,
                        stderr=subprocess.STDOUT,
                        text=True,
                        encoding="utf-8",
                        errors="replace",
                        bufsize=1,
                    )
                if proc.stdout:
                    for line in proc.stdout:
                        if line:
                            self.bus.terminal_output.emit(line.rstrip())
                return_code = proc.wait()
                if return_code != 0:
                    self.bus.terminal_output.emit(f"命令退出码: {return_code}")
                self.bus.terminal_output.emit(self._texts[self._lang]["cmd_done"])
            except Exception as exc:  # noqa: BLE001
                self.bus.terminal_output.emit(f"命令执行失败: {exc}")
            finally:
                self.bus.command_finished.emit()

        threading.Thread(target=worker, daemon=True).start()

    def _append_terminal_output(self, text: str) -> None:
        self.terminal_output.append(text)

    def _on_command_finished(self) -> None:
        self.run_cmd_btn.setEnabled(True)


def run_app() -> None:
    if sys.platform.startswith("win"):
        try:
            import ctypes

            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("codex.ai.teams.desktop")
        except Exception:
            pass
    app = QApplication(sys.argv)
    project_root = Path(__file__).resolve().parents[3]
    app.setWindowIcon(load_app_icon(project_root))
    window = MainWindow()
    window.show()
    sys.exit(app.exec())



