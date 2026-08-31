from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

from .config_loader import (
    MarketResolution,
    build_task_description,
    load_prompt_text,
    load_tasks_registry,
    load_yaml,
    project_paths,
    resolve_market,
)
from .guardrails import build_guardrail, guardrails_enabled, make_output_writer
from .models import ProjectBrief

load_dotenv()

from crewai import Agent, Crew, Process, Task  # noqa: E402

try:
    from crewai_tools import SerperDevTool  # type: ignore
except Exception:  # pragma: no cover
    SerperDevTool = None

try:
    # 网页抓取：基于 requests + bs4，不需要额外 API key。
    # 加它是为了补上一个长期短板——之前 agent 只能"搜"不能"读"，
    # 所以永远无法验证一条商品页 URL 里到底有没有那个产品、标价是多少。
    # 历史证据：Aesop 那条 `/uk/p/body/...facial-cream/` 的 URL（路径写身体护理、
    # 产品是面霜）跨了 v4.1/v7/v8 三个版本没被任何一层发现，因为验证它
    # 必须真的把页面打开。
    from crewai_tools import ScrapeWebsiteTool  # type: ignore
except Exception:  # pragma: no cover
    ScrapeWebsiteTool = None


def _build_toolkit() -> dict[str, Any]:
    tools: dict[str, Any] = {}
    has_serper_key = bool(os.getenv("SERPER_API_KEY"))
    if SerperDevTool is not None and has_serper_key:
        tools["serper_search"] = SerperDevTool()
    if ScrapeWebsiteTool is not None:
        # 不绑定固定网址：agent 每次调用时自己传 website_url，
        # 这样它才能自主决定要读哪一页（agentic 的前提）。
        tools["scrape_page"] = ScrapeWebsiteTool()
    return tools


def _build_agents(
    agent_cfg: dict[str, Any],
    tools: dict[str, Any],
    config_dir: Path,
) -> dict[str, Agent]:
    default_llm_name = os.getenv("OPENAI_MODEL_NAME", "gpt-4o-mini")
    built: dict[str, Agent] = {}
    for key, spec in agent_cfg["agents"].items():
        tool_instances = [tools[t] for t in spec.get("tools", []) if t in tools]
        backstory = str(spec.get("backstory", "")).strip()
        prompt_file = spec.get("prompt_file")
        if prompt_file:
            persona = load_prompt_text(config_dir, str(prompt_file))
            if persona:
                backstory = persona
        if not backstory:
            raise ValueError(f"Agent `{key}` requires backstory or prompt_file")
        # 规则密集的任务（研究/QA）对模型的指令遵循能力要求更高；允许在 agents.yaml
        # 给单个 agent 指定更强的模型，不写则退回全局 OPENAI_MODEL_NAME。
        agent_llm_name = str(spec.get("llm") or "").strip() or default_llm_name

        # agentic 相关参数：只有在 agents.yaml 里显式写了才传，
        # 不写就完全保持原有行为，避免影响已有的 workflow 版本 agent。
        #   max_iter  = 允许的「思考→用工具→再思考」循环轮数上限（CrewAI 默认 25）
        #   reasoning = 执行前先自己做一次规划（这是 agent 与 workflow 的关键差别之一）
        extra: dict[str, Any] = {}
        if spec.get("max_iter") is not None:
            extra["max_iter"] = int(spec["max_iter"])
        if spec.get("reasoning") is not None:
            extra["reasoning"] = bool(spec["reasoning"])
        if spec.get("max_reasoning_attempts") is not None:
            extra["max_reasoning_attempts"] = int(spec["max_reasoning_attempts"])

        built[key] = Agent(
            role=spec["role"],
            goal=spec["goal"],
            backstory=backstory,
            allow_delegation=bool(spec.get("allow_delegation", False)),
            verbose=True,
            tools=tool_instances,
            llm=agent_llm_name,
            **extra,
        )
    return built


# ⚠️ 这里曾经有一份 `_SCOPE_TO_LOCALE` 硬编码表，**已删除**。
#
# 原因：同一件事（market_scope → 地区）当时维护在两个地方——这份表决定引用校验的
# 地区码，`knowledge/registry.yaml` 决定加载哪个知识包。两份手维护的表必然漂移，
# 而且实测已经漂了：日本/新加坡/马来西亚只在这份表里、东南亚只在 registry 里、
# **德国一度只在 registry 里而这份表漏了**——后果是石头科技那一整轮跑下来，
# 「他国站点当本地商品页」检测从头到尾没执行过，且没有任何提示。
#
# 现在唯一的映射表是 `knowledge/registry.yaml`，由 `config_loader.resolve_market()` 读取。
# 加市场只改那一个文件。


def _resolve_market(market_scope: str, knowledge_dir: Path) -> MarketResolution:
    """解析市场配置，并把需要人注意的情况**大声打印出来**。

    为什么要打印而不是静默返回：这个项目里反复出问题的模式就是「静默回落」——
    没匹配上就用默认值，不报错，于是「没报错」被读成「检查过了没问题」。
    """
    resolution = resolve_market(knowledge_dir, market_scope)
    warnings = resolution.warnings(market_scope)
    if warnings:
        print()
        print("=" * 78)
        print("⚠️  市场配置提示（不是错误，但会影响本次检查的覆盖范围）")
        print("=" * 78)
        for w in warnings:
            print(f"  • {w}")
        print()
    return resolution


def _expand_task_dependencies(requested: list[str], task_specs: dict[str, dict[str, Any]]) -> list[str]:
    """Ensure upstream context tasks run before dependents (e.g. expansion needs feasibility)."""
    ordered: list[str] = []

    def add_task(name: str) -> None:
        if name not in task_specs:
            raise ValueError(f"Unknown task: {name}")
        if name in ordered:
            return
        for dep in task_specs[name].get("context", []) or []:
            add_task(str(dep))
        ordered.append(name)

    for task_name in requested:
        add_task(task_name)
    return ordered


def resolve_selected_tasks(variant: str = "full", task_filter: list[str] | None = None) -> list[str]:
    """Public helper: which task names would run for a given variant/filter.

    Mirrors the selection logic inside `build_marketing_crew` so callers (main.py,
    citation checks, ablation scripts) can know which output files to expect
    without having to build/run the whole crew.
    """
    base_dir = Path(__file__).resolve().parent
    paths = project_paths(base_dir)
    task_registry = load_tasks_registry(paths["config_dir"])
    task_order: list[str] = task_registry["task_order"]
    task_specs: dict[str, dict[str, Any]] = task_registry["tasks"]

    if task_filter:
        return _expand_task_dependencies(task_filter, task_specs)

    selected = _select_tasks(task_order, variant=variant)
    if variant == "expansion_only":
        selected = _expand_task_dependencies(selected, task_specs)
    return selected


def resolve_output_files(variant: str = "full", task_filter: list[str] | None = None) -> list[Path]:
    """Absolute paths of the output_file(s) that this run is expected to (re)write."""
    base_dir = Path(__file__).resolve().parent
    paths = project_paths(base_dir)
    task_registry = load_tasks_registry(paths["config_dir"])
    task_specs: dict[str, dict[str, Any]] = task_registry["tasks"]
    project_root = base_dir.parent.parent

    selected = resolve_selected_tasks(variant=variant, task_filter=task_filter)
    files: list[Path] = []
    for task_name in selected:
        output_file = task_specs[task_name].get("output_file")
        if output_file:
            files.append(project_root / output_file)
    return files


def _select_tasks(task_order: list[str], variant: str) -> list[str]:
    if variant == "single_agent":
        return ["channel_strategy_task"]
    if variant == "feasibility_only":
        # 可行性 + 缺口二轮补证（测深度时用这个，比全链路便宜）
        return [
            "market_feasibility_task",
            "evidence_gap_fill_task",
        ]
    if variant == "expansion_only":
        return ["market_expansion_task"]
    if variant == "research_only":
        return [
            "market_feasibility_task",
            "evidence_gap_fill_task",
            "market_expansion_task",
            "competitor_analysis_task",
        ]
    if variant == "research_depth":
        # Depth V1：与 research_only 同序，但用平行 task（硬证据清单地板 + 少灌水）。
        # 不改 research_only，便于冻结 demo 对照。
        return [
            "market_feasibility_depth_task",
            "evidence_gap_fill_depth_task",
            "market_expansion_depth_task",
            "competitor_analysis_depth_task",
        ]
    if variant == "feasibility_depth":
        # 便宜试验：只跑可行性 Depth + 缺口补证 Depth
        return [
            "market_feasibility_depth_task",
            "evidence_gap_fill_depth_task",
        ]
    if variant == "competitor_agentic":
        # agentic 试点：可行性 + 缺口补证 + 开拓 + **agentic 版竞品分析**。
        # 跟 research_only 的主要差别是最后一步换成了自主研究版竞品。
        # 输出文件也是分开的（competitor_battlecard_agentic.md），不会覆盖原版结果。
        return [
            "market_feasibility_task",
            "evidence_gap_fill_task",
            "market_expansion_task",
            "competitor_analysis_agentic_task",
        ]
    if variant == "research_qa":
        # 研究链路 + QA 审校，不含渠道/内容生产。
        # qa_review_task 的 context 可能列了未跑的上游；build 时 `if n in tasks_by_name`
        # 会自动只挂上本次真正跑了的任务。
        return [
            "market_feasibility_task",
            "evidence_gap_fill_task",
            "market_expansion_task",
            "competitor_analysis_task",
            "qa_review_task",
        ]
    if variant == "no_research_stage":
        return ["channel_strategy_task", "xhs_content_task", "douyin_plan_task", "qa_review_task"]
    if variant == "no_qa":
        return [name for name in task_order if name != "qa_review_task"]
    return task_order


def build_marketing_crew(
    brief: ProjectBrief,
    variant: str = "full",
    process: Process = Process.sequential,
    task_filter: list[str] | None = None,
) -> Crew:
    base_dir = Path(__file__).resolve().parent
    paths = project_paths(base_dir)
    agents_yaml = load_yaml(paths["agents_yaml"])
    task_registry = load_tasks_registry(paths["config_dir"])
    tools = _build_toolkit()
    agents = _build_agents(agents_yaml, tools, paths["config_dir"])

    brief_block = brief.to_prompt_block()
    task_specs: dict[str, dict[str, Any]] = task_registry["tasks"]

    selected = resolve_selected_tasks(variant=variant, task_filter=task_filter)

    # 市场配置只解析一次：知识包与引用校验地区码来自**同一次匹配**，
    # 不可能再出现「知识包按德国加载、地区检测按空串跳过」这种错配。
    market = _resolve_market(brief.market_scope, paths["knowledge_dir"])

    tasks_by_name: dict[str, Task] = {}
    rendered_tasks: list[Task] = []

    for task_name in selected:
        spec = task_specs[task_name]
        context_tasks = [tasks_by_name[n] for n in spec.get("context", []) if n in tasks_by_name]
        description = build_task_description(
            spec=spec,
            config_dir=paths["config_dir"],
            knowledge_dir=paths["knowledge_dir"],
            brief_block=brief_block,
            market_scope=brief.market_scope,
        )
        # guardrail：让 workflow 具备 agent 式的自我修正循环。
        # task yaml 里写 `guardrail: citation` 即可挂上——机械校验发现严重问题时，
        # CrewAI 会把具体违规清单喂回给同一个 agent 重跑（最多 guardrail_max_retries 次）。
        # 与之前的 agentic 实验的关键区别：裁判是代码不是模型。
        task_kwargs: dict[str, Any] = {}
        output_file = spec.get("output_file")
        guardrail_name = str(spec.get("guardrail") or "").strip()

        if guardrail_name and guardrails_enabled():
            soft_retries = int(spec.get("guardrail_max_retries", 2))
            guardrail_fn = build_guardrail(
                guardrail_name,
                locale=market.locale,
                soft_max_retries=soft_retries,
                # search_effort guardrail 要按 agent 角色去审计日志里查真实调用记录，
                # 所以必须把角色名传进去（日志里记的是 role，不是 agent key）
                agent_role=agents[spec["agent"]].role,
            )
            if guardrail_fn is not None:
                task_kwargs["guardrail"] = guardrail_fn
                # 给 CrewAI 的上限设得比软上限大：组合 guardrail 用共享软上限兜住后应放行。
                # depth_v2 曾因「子 guardrail 各自 soft + CrewAI 总预算过紧」在可行性耗尽重试、
                # 整条 research_depth 中断（竞品 guardrail 从未执行）。共享软上限后这里 +3 作余量。
                task_kwargs["guardrail_max_retries"] = soft_retries + 3

                # ⚠️ 挂了 guardrail 就**不能**再用 CrewAI 的 output_file，必须改用 callback 写文件。
                # 原因：CrewAI 的 `Task._execute_core` 写文件时用的是第一次执行的 `result` 变量，
                # 而 guardrail 重试后的新内容只在返回的 `task_output` 里——用 output_file 会把
                # 「没改过的原始版本」写进磁盘，让 guardrail 白跑。
                # callback 在 output_file 写入**之前**执行，且收到的是校验后的 task_output。
                # 详见 guardrails.make_output_writer 的文档字符串。
                if output_file:
                    task_kwargs["callback"] = make_output_writer(output_file)
                    output_file = None

        task = Task(
            description=description,
            expected_output=spec["expected_output"],
            output_file=output_file,
            agent=agents[spec["agent"]],
            context=context_tasks,
            **task_kwargs,
        )
        tasks_by_name[task_name] = task
        rendered_tasks.append(task)

    return Crew(agents=list(agents.values()), tasks=rendered_tasks, process=process, verbose=True)


def build_research_crew(brief: ProjectBrief) -> Crew:
    """Research-only sub-pipeline for template reuse."""
    return build_marketing_crew(brief=brief, variant="research_only", process=Process.sequential)


def build_content_crew(brief: ProjectBrief) -> Crew:
    """Content-only sub-pipeline for template reuse."""
    return build_marketing_crew(brief=brief, variant="no_research_stage", process=Process.sequential)
