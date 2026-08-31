from __future__ import annotations

import argparse
import json
import os
import time
from pathlib import Path

from dotenv import load_dotenv

from .citation_check import check_files
from .crew import build_marketing_crew, resolve_output_files
from .models import ProjectBrief

load_dotenv()

ALLOWED_MATERIAL_PREFIXES = ("inputs/", "knowledge/user/")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run localized CrewAI marketing workflow.")
    parser.add_argument("--brief-file", type=str, default="", help="Path to a JSON brief file.")
    parser.add_argument(
        "--variant",
        type=str,
        default="research_only",
        choices=[
            "full",
            "research_only",
            "research_depth",
            "feasibility_depth",
            "research_qa",
            "competitor_agentic",
            "feasibility_only",
            "expansion_only",
            "single_agent",
            "no_research_stage",
            "no_qa",
        ],
        help=(
            "Workflow variant. 默认 research_only = 可行性 → 缺口二轮补证 → 开拓 → 竞品；"
            "research_depth = Depth V1（平行任务 + 硬证据清单地板，不改 research_only）；"
            "feasibility_depth = 只跑可行性/补证 Depth（便宜试验）；"
            "feasibility_only = 可行性 + 缺口补证（测深度用）；"
            "research_qa = 上述研究链路 + QA；"
            "competitor_agentic = 研究链路但竞品换成自主研究版（对照实验，已证明通常更差）。"
        ),
    )
    parser.add_argument(
        "--no-guardrails",
        action="store_true",
        help=(
            "关闭 task 级 guardrail 自我修正循环（默认开启）。"
            "开启时，挂了 guardrail 的 task 若产出有严重引用问题，会把违规清单喂回模型自动重跑。"
        ),
    )
    parser.add_argument(
        "--no-tool-audit",
        action="store_true",
        help="关闭工具调用审计（默认开启，会把每次真实的工具调用写进 outputs/tool_audit.jsonl）",
    )
    parser.add_argument(
        "--tasks",
        type=str,
        default="",
        help="Comma-separated task names; auto-includes upstream context deps (e.g. market_expansion_task).",
    )
    parser.add_argument("--product-name", type=str, default="")
    parser.add_argument("--product-description", type=str, default="")
    parser.add_argument("--target-audience", type=str, default="")
    parser.add_argument("--market-scope", type=str, default="")
    parser.add_argument("--goals", type=str, default="")
    parser.add_argument("--budget-range", type=str, default="")
    parser.add_argument("--focus-areas", type=str, default="", help="Comma-separated focus areas.")
    parser.add_argument("--known-competitors", type=str, default="", help="Optional; leave empty to let AI discover.")
    parser.add_argument("--competitors", type=str, default="", help="Alias of --known-competitors.")
    parser.add_argument(
        "--materials-file",
        action="append",
        default=[],
        help="Path to product materials (md/txt). Can be passed multiple times.",
    )
    parser.add_argument("--notes", type=str, default="", help="Free-form user notes.")
    parser.add_argument("--constraints", type=str, default="避免夸大宣传,关键结论附来源")
    parser.add_argument(
        "--strict-citations",
        action="store_true",
        help="若引用校验发现假域名/未填模板等严重问题，以非零退出码结束（默认只打印报告，不中断）。",
    )
    parser.add_argument(
        "--strict-depth",
        action="store_true",
        help="若深度门禁发现「零搜索下乐观结论 / 补证不换角度」等严重问题，以非零退出码结束。",
    )
    return parser.parse_args()


def _split_csv(value: str) -> list[str]:
    return [x.strip() for x in value.split(",") if x.strip()]


def _project_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _normalize_material_path(project_root: Path, raw_path: str) -> Path:
    candidate = Path(raw_path)
    resolved = candidate if candidate.is_absolute() else (project_root / candidate)
    resolved = resolved.resolve()
    if not resolved.is_relative_to(project_root):
        raise SystemExit(f"materials file must be inside project root: {raw_path}")

    relative = resolved.relative_to(project_root).as_posix()
    if not any(relative.startswith(prefix) for prefix in ALLOWED_MATERIAL_PREFIXES):
        raise SystemExit(
            f"materials file must be under inputs/ or knowledge/user/: {raw_path}"
        )
    return resolved


def _merge_material_text(project_root: Path, files: list[str]) -> str:
    sections: list[str] = []
    for raw_path in files:
        normalized_path = _normalize_material_path(project_root, raw_path)
        content = normalized_path.read_text(encoding="utf-8").strip()
        if not content:
            continue
        relative = normalized_path.relative_to(project_root).as_posix()
        sections.append(f"### 文件: {relative}\n\n{content}")
    return "\n\n".join(sections).strip()


def build_brief(args: argparse.Namespace) -> ProjectBrief:
    project_root = _project_root()
    if args.brief_file:
        payload = json.loads(Path(args.brief_file).read_text(encoding="utf-8"))
        brief = ProjectBrief.from_dict(payload)
        merged_files = list(brief.material_files) + list(args.materials_file)
        merged_materials = _merge_material_text(project_root, merged_files)
        if merged_materials:
            brief.product_materials = (
                f"{brief.product_materials.strip()}\n\n{merged_materials}".strip()
                if brief.product_materials.strip()
                else merged_materials
            )
        if merged_files:
            brief.material_files = merged_files
        return brief

    materials = _merge_material_text(project_root, list(args.materials_file))

    known = _split_csv(args.known_competitors) or _split_csv(args.competitors)
    if not args.product_name.strip():
        raise SystemExit("请提供 --brief-file 或至少 --product-name")

    return ProjectBrief(
        product_name=args.product_name,
        product_description=args.product_description,
        target_audience=args.target_audience,
        market_scope=args.market_scope,
        goals=args.goals,
        budget_range=args.budget_range,
        focus_areas=_split_csv(args.focus_areas),
        known_competitors=known,
        product_materials=materials,
        material_files=list(args.materials_file),
        user_notes=args.notes,
        constraints=_split_csv(args.constraints),
    )


def _warn_stale_outputs(output_files: list[Path], run_started_at: float) -> None:
    """检查本轮该产出的文件是否真的被写过；没写的大声报出来。

    「文件存在」不等于「本轮产出」——它可能是上一次运行留下的。
    这个检查很便宜，但能挡住一整类静默失败。
    """
    stale: list[Path] = []
    missing: list[Path] = []
    for path in output_files:
        if not path.exists():
            missing.append(path)
        elif path.stat().st_mtime < run_started_at:
            stale.append(path)

    if not stale and not missing:
        return

    print("\n" + "=" * 78)
    print("⚠️  产出完整性检查未通过")
    print("=" * 78)
    for path in missing:
        print(f"  ❌ 未生成：{path}")
    for path in stale:
        print(f"  ❌ **本轮未更新（是上一次运行的旧文件）**：{path}")
    print()
    print("  说明：对应的 task 很可能失败了（工具报错 / guardrail 重试耗尽 / 依赖缺失）。")
    print("  ⚠️ **不要直接 cp 归档**——那会把上一轮的内容当成本轮产出存下来。")
    print("  先看上面的运行日志找出失败原因，修好后重跑。")


def run() -> None:
    args = parse_args()
    brief = build_brief(args)
    task_filter = _split_csv(args.tasks) if args.tasks else None

    # guardrail 开关：CLI 优先于环境变量。必须在 build_marketing_crew 之前设置，
    # 因为 guardrail 是在构建 Task 时装配的。
    if args.no_guardrails:
        os.environ["DISABLE_GUARDRAILS"] = "1"

    # 工具调用审计：必须在 kickoff **之前**创建（构造函数里完成事件订阅）。
    # 为什么需要：agentic 版报告里写过「已用 scrape_page 核实，页面显示标价 £12.95」，
    # 但独立请求那条 URL 返回 HTTP 404——页面根本不存在。「已核实」是模型自己填的一栏，
    # 不可信。这里由代码记录每一次真实的工具调用，跑完与报告对照即可发现伪造。
    audit = None
    if not args.no_tool_audit:
        from .tool_audit import ToolAuditListener

        audit_log = Path("outputs") / "tool_audit.jsonl"
        audit = ToolAuditListener(log_path=audit_log)

    # 记录开跑时间：跑完用它检查每个 output_file 是不是真的被本轮写过。
    # 为什么需要：某个 task 失败时（例如 guardrail 重试耗尽、工具报错），
    # 它的输出文件不会被更新，而**上一次运行的旧文件仍留在原地**——
    # 如果直接 cp 归档，看起来就像跑成功了。实测踩过：石头科技那轮的竞品报告，
    # 归档出来的其实是上一轮花知晓的泰国彩妆内容，逐字节相同。
    run_started_at = time.time()

    crew = build_marketing_crew(brief=brief, variant=args.variant, task_filter=task_filter)
    result = crew.kickoff()
    print("\n=== Crew run complete ===")
    print(result)

    _warn_stale_outputs(
        resolve_output_files(variant=args.variant, task_filter=task_filter),
        run_started_at,
    )

    if audit is not None:
        print()
        print(audit.render_summary())

    # 事后把关：模型经常不遵守 prompt 里"禁止 example.com / 禁止拿首页当证据"的规则，
    # 这里跑一遍机械校验，把假引用明确列出来，而不是假装输出已经可信。
    output_files = resolve_output_files(variant=args.variant, task_filter=task_filter)
    print()
    report = check_files(output_files)
    print(report.render())
    if args.strict_citations and report.total_errors:
        raise SystemExit(
            f"\n引用校验未通过（{report.total_errors} 处严重问题），已按 --strict-citations 中断。"
        )

    # 评分表自洽性：重算加权总分，并核对结论档位与分数是否一致。
    # 为什么必须由代码做：这是纯确定性运算，让模型自查等于让它重做一遍同样会做错的事。
    # 实测四份归档报告里**三份把自己的加权总分算错了**，其中东边野兽 v8 写的 3.35
    # 按阈值该判「暂缓」，报告却写「建议进入」——说明分数和结论是各写各的。
    from .scoring_check import check_scoring_files, render_scoring_reports

    scoring_reports = check_scoring_files(output_files)
    print()
    print(render_scoring_reports(scoring_reports))
    scoring_errors = sum(len(r.errors) for r in scoring_reports)
    if args.strict_citations and scoring_errors:
        raise SystemExit(
            f"\n评分表自洽性校验未通过（{scoring_errors} 处），已按 --strict-citations 中断。"
        )

    # 深度门禁：对照 tool_audit（可行性是否零搜索下结论、补证是否换过零售/品牌角度）
    from .research_depth_check import check_research_depth

    depth = check_research_depth(
        audit,
        feasibility_path=Path("outputs/market_feasibility.md"),
        gap_fill_path=Path("outputs/evidence_gap_fill.md"),
    )
    print()
    print(depth.render())
    if args.strict_depth and depth.errors:
        raise SystemExit(
            f"\n深度门禁未通过（{len(depth.errors)} 处严重问题），已按 --strict-depth 中断。"
        )

    # Depth V1 硬证据地板：仅 research_depth / feasibility_depth 启用，避免抬高旧基线。
    if args.variant in {"research_depth", "feasibility_depth"}:
        from .artifact_check import check_research_depth_artifacts, render_artifact_reports

        competitor_path = Path("outputs/competitor_battlecard.md")
        artifact_reports = check_research_depth_artifacts(
            feasibility_path=Path("outputs/market_feasibility.md"),
            competitor_path=competitor_path if args.variant == "research_depth" else None,
            audit=audit,
        )
        print()
        print(render_artifact_reports(artifact_reports))
        artifact_errors = sum(len(r.errors) for r in artifact_reports)
        if args.strict_depth and artifact_errors:
            raise SystemExit(
                f"\n硬证据地板未通过（{artifact_errors} 处严重问题），已按 --strict-depth 中断。"
            )


if __name__ == "__main__":
    run()
