# 配置说明

## 任务配置拆分

- `tasks.yaml`：流水线清单（`task_order`）+ 可选 inline 覆盖
- `tasks/*.yaml`：每个子任务一份配置
- `prompts/*.md`：角色手册（身份、边界、原则、风格）；**执行框架与检查清单放 `tasks/*.yaml` 的 `description`**

## 市场研究两阶段（独立 Agent Persona）

| Task | Agent | Persona（`agents.yaml` → `prompt_file` → backstory） | 输出 |
|------|-------|------------------------------------------------------|------|
| `market_feasibility_task` | `market_researcher_feasibility` | `market_researcher_feasibility.md` | `outputs/market_feasibility.md` |
| `market_expansion_task` | `market_researcher_expansion` | `market_researcher_expansion.md` | `outputs/market_expansion.md` |

角色手册通过 **Agent 的 backstory** 注入（`crew.py` 读取 `agents.yaml` 的 `prompt_file`）。  
Task `description` 只放本步框架、检查清单与 `{brief}`，避免与 persona 重复。

## 单任务 YAML 字段

| 字段 | 必填 | 说明 |
|------|------|------|
| `agent` | 是 | 对应 `agents.yaml` 里的 agent key |
| `description` | 建议 | 本步骤任务说明，可用 `{brief}` |
| `expected_output` | 是 | 输出结构约束 |
| `output_file` | 建议 | 结果写入 `outputs/` |
| `context` | 否 | 依赖的上游 task 名称列表 |
| `prompt_file` | 否 | 相对 `config/` 的路径 |
| `include_global_knowledge` | 否 | 默认 `true`；research task 建议 `false` |
| `knowledge_mode` | 否 | `registry` 时从 `knowledge/registry.yaml` 按 `market_scope` 加载 |

## 示例：只改可行性任务

编辑 `tasks/market_feasibility.yaml` 或 `prompts/market_researcher_feasibility.md`。

## 临时覆盖（做实验）

在 `tasks.yaml` 里：

```yaml
tasks:
  market_feasibility_task:
    description: |
      实验附加规则...
```

会覆盖 `tasks/market_feasibility.yaml` 的同名字段。

## CLI 单步运行

```bash
# 只跑可行性
PYTHONPATH=. python -m src.marketing_crew.main --variant feasibility_only --product-name "Demo"

# 只跑开拓（自动先跑 feasibility 以提供 context）
PYTHONPATH=. python -m src.marketing_crew.main --variant expansion_only --product-name "Demo"

# 指定 task（自动展开上游依赖）
PYTHONPATH=. python -m src.marketing_crew.main --tasks market_expansion_task --product-name "Demo"
```
