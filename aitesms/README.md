# Codex AI Teams

## 启动

```powershell
cd D:\codexAIteams\aitesms
python -m pip install -r requirements.txt
python .\scripts\generate_app_icon.py
python .\main.py
```

## 说明

- 入口文件已内置 `src` 路径注入，可在任意工作目录执行：
  `python D:\codexAIteams\aitesms\main.py`
- 当前 Bridge 为占位适配器，后续接入真实 telegram bridge。
- 已支持 4 Agent 并发、状态展示、日志输出、结果聚合。

