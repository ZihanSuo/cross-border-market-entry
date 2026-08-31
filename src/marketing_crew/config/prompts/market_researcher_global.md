# 跨境市场研究员（两阶段分工说明）

市场研究拆为两个 **独立 Agent + Task**，避免同一 persona 混用：

| 阶段 | Agent | Persona MD | Task | 输出 |
|------|-------|------------|------|------|
| 1 可行性 | `market_researcher_feasibility` | `market_researcher_feasibility.md` | `market_feasibility_task` | `market_feasibility.md` |
| 2 开拓 | `market_researcher_expansion` | `market_researcher_expansion.md` | `market_expansion_task` | `market_expansion.md` |

- Persona MD → `agents.yaml` 的 `prompt_file` → 加载为 Agent **backstory**
- 执行框架 → 各 task 的 `description`（含 `{brief}`）
