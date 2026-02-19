# Codex AI Teams

桌面端多 Agent 协作工具（PySide6）。

## 项目路径

`D:\codexAIteams\aitesms`

## 环境要求

- Python 3.11+
- Windows PowerShell

## 安装依赖

```powershell
cd D:\codexAIteams\aitesms
python -m pip install -r requirements.txt
```

## 启动

```powershell
python .\main.py
```

如需重新生成图标：

```powershell
python .\scripts\generate_app_icon.py
```

## 功能概览

- 团队页：4 个 Agent 状态与执行日志
- 配置页：Agent 参数与桥接配置
- 日志页：日志筛选与 CSV 导出
- 文件页：工作目录浏览
- 终端页：本地命令执行与输出

## Git 仓库

- 远程地址：`https://github.com/JimiKen/codexAIteams.git`

## 一键推送

仓库根目录提供 `git_push.bat`，双击或命令行执行即可推送。
