"""QA 审校环节的 benchmark：拿已归档的报告当固定输入，测 QA 能抓到几条已知问题。

## 为什么需要这个

在此之前，验证 QA 改动的唯一办法是跑一整轮 `--variant research_qa`，有三个毛病：
1. 花钱（要重跑研究三步）
2. 研究三份每次都重新生成，输入不一样，不是干净对照
3. 慢

这个脚本让 QA 直接读**已归档的固定报告**，跳过研究三步。于是可以：
- 几毛钱、几十秒跑完一次
- 每次输入完全一样，改 prompt 前后的结果可比
- 用 `qa_bench_cases.yaml` 里人工标注的已知问题算召回率

## 用法

    # 跑单个 case
    PYTHONPATH=. python experiments/qa_bench.py --case flowerknows_v2

    # 跑全部 case
    PYTHONPATH=. python experiments/qa_bench.py --all

    # 只看会喂给模型的 prompt，不实际调 API（免费，用于检查 prompt 拼装是否正确）
    PYTHONPATH=. python experiments/qa_bench.py --case herbeast_v8 --dry-run

    # 指定模型（默认读 agents.yaml 里 brand_qa_checker 的 llm，没有则用 .env）
    PYTHONPATH=. python experiments/qa_bench.py --all --model gpt-4o-mini

结果写到 `experiments/qa_bench_runs/<时间戳>/`，包含每个 case 的 QA 原始输出与评分。

## 评分口径（重要，别把这个数字当成绝对能力）

召回率 = QA 命中的已知问题数 / 该 case 标注的已知问题总数。

命中判定是**关键词匹配**（用标注里的关键实体，如域名、数字、字段名去 QA 输出里搜），
这是个粗糙的近似：QA 可能用不同措辞描述同一个问题而被判成未命中（低估），
也可能碰巧提到了关键词但判断是错的（高估）。所以：

- 这个数字适合做**同一套标注下的纵向对比**（改 prompt 前后、换模型前后）
- 不适合当作 QA 的绝对能力值
- 每次跑完建议人工扫一眼 miss 列表，确认是真漏了还是措辞不同
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

import yaml

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "src"))

# 必须显式加载 .env：正常跑流水线时是 crew.py 在导入时调的 load_dotenv()，
# 但本脚本不导入 crew.py（刻意的，避免拉起 CrewAI 依赖），所以要自己加载，
# 否则 OPENAI_API_KEY 读不到，会报 "Missing credentials"。
from dotenv import load_dotenv  # noqa: E402

load_dotenv(PROJECT_ROOT / ".env")

from marketing_crew.config_loader import (  # noqa: E402
    build_task_description,
    load_tasks_registry,
    load_yaml,
    project_paths,
)
from marketing_crew.models import ProjectBrief  # noqa: E402

CASES_FILE = Path(__file__).resolve().parent / "qa_bench_cases.yaml"
RUNS_DIR = Path(__file__).resolve().parent / "qa_bench_runs"

# 用于 _strip_urls：把 markdown 链接与裸链接整体挖掉
import re as _re  # noqa: E402

_MD_LINK_RE_LOCAL = _re.compile(r"\[([^\]]*)\]\((https?://[^\s)]+)\)")
_BARE_URL_RE_LOCAL = _re.compile(r"https?://[^\s)\]|]+")

UPSTREAM_FILES = (
    ("market_feasibility.md", "市场可行性研究"),
    ("market_expansion.md", "市场开拓路径"),
    ("competitor_battlecard.md", "竞品分析"),
)

# case id → 对应的 brief 文件。QA 要做「与 brief 原文比对」，必须喂对 brief。
CASE_BRIEFS = {
    "herbeast": "briefs/herbeast_uk_v2.json",
    "flowerknows": "briefs/flowerknows_thailand.json",
}


@dataclass
class IssueResult:
    issue_id: str
    issue_type: str
    detectable_by: str
    hit: bool
    matched_on: str = ""


@dataclass
class CaseResult:
    case_id: str
    model: str
    qa_output: str = ""
    issues: list[IssueResult] = field(default_factory=list)
    error: str = ""
    repeat_index: int = 1

    @property
    def total(self) -> int:
        return len(self.issues)

    @property
    def hits(self) -> int:
        return sum(1 for i in self.issues if i.hit)

    @property
    def recall(self) -> float:
        return round(self.hits / self.total, 2) if self.total else 0.0

    def recall_for(self, detectable_by: str) -> tuple[int, int]:
        subset = [i for i in self.issues if detectable_by in i.detectable_by]
        return sum(1 for i in subset if i.hit), len(subset)


@dataclass
class RepeatedCaseResult:
    """同一个 case 跑多次的汇总。

    存在的理由：实测发现同配置、同输入、同模型跑两次，结果会不一样——
    `herbeast_v8` 的「消费者评价极高」这条，第一轮 QA 抓到了，第二轮没抓到。
    单次数字有噪声，判断某个改动是否有效时可能被波动淹没，所以需要多跑几次
    看均值和稳定性，而不是拿单次结果下结论。
    """

    case_id: str
    model: str
    runs: list[CaseResult] = field(default_factory=list)

    @property
    def ok_runs(self) -> list[CaseResult]:
        return [r for r in self.runs if not r.error]

    @property
    def recalls(self) -> list[float]:
        return [r.recall for r in self.ok_runs]

    @property
    def mean_recall(self) -> float:
        vals = self.recalls
        return round(sum(vals) / len(vals), 3) if vals else 0.0

    @property
    def min_recall(self) -> float:
        return min(self.recalls) if self.recalls else 0.0

    @property
    def max_recall(self) -> float:
        return max(self.recalls) if self.recalls else 0.0

    def issue_stability(self) -> list[tuple[str, str, int, int]]:
        """每条已知问题在 N 次运行里命中了几次。

        返回 (issue_id, issue_type, 命中次数, 总次数)，按命中次数升序——
        最不稳定/最难抓的排在最前面。
        """
        if not self.ok_runs:
            return []
        stats: dict[str, list] = {}
        for run in self.ok_runs:
            for issue in run.issues:
                entry = stats.setdefault(issue.issue_id, [issue.issue_type, 0, 0])
                entry[1] += 1 if issue.hit else 0
                entry[2] += 1
        rows = [(iid, v[0], v[1], v[2]) for iid, v in stats.items()]
        rows.sort(key=lambda r: (r[2], r[0]))
        return rows


def _resolve_brief_path(case_id: str) -> Path:
    for prefix, rel in CASE_BRIEFS.items():
        if case_id.startswith(prefix):
            return PROJECT_ROOT / rel
    raise ValueError(f"case `{case_id}` 没有对应的 brief 映射，请在 CASE_BRIEFS 里补上")


def _load_brief(path: Path) -> ProjectBrief:
    with path.open("r", encoding="utf-8") as f:
        data = json.load(f)
    return ProjectBrief(**data)


def _read_upstream(case_dir: Path) -> str:
    """把已归档的三份研究报告拼成 QA 的上游上下文。

    这是本脚本的核心：正常跑流水线时，CrewAI 通过 Task 对象传递 context；
    这里改成直接从磁盘读，从而跳过重新生成研究三步。
    """
    blocks: list[str] = []
    for filename, label in UPSTREAM_FILES:
        path = case_dir / filename
        if not path.exists():
            continue
        text = path.read_text(encoding="utf-8").strip()
        blocks.append(f"---\n### 上游产出：{label}（文件名 {filename}）\n\n{text}")
    if not blocks:
        raise FileNotFoundError(f"{case_dir} 下没有找到任何上游产出文件")
    return "\n\n".join(blocks)


def build_qa_prompt(case: dict[str, Any]) -> str:
    """拼出与正式运行时等价的 QA prompt（description + knowledge + 上游产出）。"""
    base_dir = PROJECT_ROOT / "src" / "marketing_crew"
    paths = project_paths(base_dir)
    registry = load_tasks_registry(paths["config_dir"])
    spec = registry["tasks"]["qa_review_task"]

    brief = _load_brief(_resolve_brief_path(case["id"]))
    description = build_task_description(
        spec=spec,
        config_dir=paths["config_dir"],
        knowledge_dir=paths["knowledge_dir"],
        brief_block=brief.to_prompt_block(),
        market_scope=brief.market_scope,
    )

    upstream = _read_upstream(PROJECT_ROOT / case["dir"])
    expected = spec.get("expected_output", "")

    return (
        f"{description}\n\n"
        f"## 待审校的上游产出（这就是你要检查的全部内容）\n\n{upstream}\n\n"
        f"---\n\n## 输出格式要求\n\n{expected}\n"
    )


def _resolve_model(explicit: str = "") -> str:
    if explicit:
        return explicit
    agents_yaml = load_yaml(PROJECT_ROOT / "src" / "marketing_crew" / "config" / "agents.yaml")
    override = str(agents_yaml["agents"]["brand_qa_checker"].get("llm") or "").strip()
    return override or os.getenv("OPENAI_MODEL_NAME", "gpt-4o-mini")


def call_model(prompt: str, model: str) -> str:
    from openai import OpenAI

    client = OpenAI()
    resp = client.chat.completions.create(
        model=model,
        messages=[{"role": "user", "content": prompt}],
    )
    return resp.choices[0].message.content or ""


# 从标注的 evidence 里提取用于匹配的关键词。
#
# 只用**能唯一定位到这一条问题**的特征：域名、百分比、反引号内容、特征短语。
# 刻意**不用品牌名**（Mistine / Srichand / Aesop 等）——自测发现同一个品牌
# 往往对应多条不同问题（市场份额无来源、社媒主页当舆论、首页当商品页），
# 只要 QA 提到品牌名，三条都会被判命中，召回率被严重高估。
def _match_keys(issue: dict[str, Any]) -> list[str]:
    import re

    # 标注里可以用 `match_keys` 显式指定匹配键，覆盖自动抽取。
    # 用于自动抽取会产生假阳性的情况——例如 v8-aesop-body-path 这条，
    # evidence 里必须写出完整 URL 供人复核，但域名本身区分度不够
    # （QA 在逐 URL 核查表里必然会提到该域名，即使它把这条判成了"正常"）。
    explicit = issue.get("match_keys")
    if isinstance(explicit, list) and explicit:
        return [str(k) for k in explicit if str(k).strip()]

    evidence = str(issue.get("evidence", ""))
    keys: list[str] = []
    # 域名：不同问题引用的域名不同，区分度够
    keys += re.findall(r"[a-z0-9-]+\.(?:com|co\.uk|org|net|co\.th|eu|gov\.uk)", evidence)
    # 百分比 / 具体数字：定位「无来源数字」这类问题
    keys += re.findall(r"\d+(?:\.\d+)?%", evidence)
    # 反引号里的原文片段
    keys += re.findall(r"`([^`]+)`", evidence)
    # 唯一性足够强的特征短语（每条只对应一个问题，不要放品牌名）
    for token in (
        "True Botanicals",
        "Raven Botanicals",
        "已按计划扩展",
        "评价极高",
        "N/A | N/A",
        "example.com",
    ):
        if token in evidence:
            keys.append(token)
    seen: set[str] = set()
    out: list[str] = []
    for k in keys:
        if k and k not in seen:
            seen.add(k)
            out.append(k)
    return out


def _strip_urls(text: str) -> str:
    """把 URL 整体挖掉，只留正文。

    用于 `match_in_prose_only` 的标注：有些问题的特征词本身就藏在 URL 里
    （如 `/body/` 路径段），QA 只要在核查表里**引用**了这条 URL 就会匹配上，
    但引用 URL 不等于指出问题——它完全可能把这条判成"正常"。
    挖掉 URL 之后再匹配，才能确认 QA 是真的在正文里讨论了这个问题。
    """
    stripped = _MD_LINK_RE_LOCAL.sub(" ", text)
    return _BARE_URL_RE_LOCAL.sub(" ", stripped)


def score_case(case: dict[str, Any], qa_output: str) -> list[IssueResult]:
    results: list[IssueResult] = []
    lowered = qa_output.lower()
    prose_only = _strip_urls(qa_output).lower()
    for issue in case.get("known_issues", []):
        keys = _match_keys(issue)
        haystack = prose_only if issue.get("match_in_prose_only") else lowered
        matched = next((k for k in keys if k.lower() in haystack), "")
        results.append(
            IssueResult(
                issue_id=issue["id"],
                issue_type=issue["type"],
                detectable_by=str(issue.get("detectable_by", "")),
                hit=bool(matched),
                matched_on=matched,
            )
        )
    return results


def render_report(results: list[CaseResult]) -> str:
    lines: list[str] = ["=" * 78, "QA Benchmark 结果", "=" * 78]
    for r in results:
        lines.append(f"\n## {r.case_id}  (model={r.model})")
        if r.error:
            lines.append(f"  ❌ 运行失败：{r.error}")
            continue
        lines.append(f"  总召回：{r.hits}/{r.total}  ({r.recall:.0%})")
        for label in ("tool", "qa", "neither"):
            h, t = r.recall_for(label)
            if t:
                lines.append(f"    - 标注为「{label}」的问题：{h}/{t}")
        misses = [i for i in r.issues if not i.hit]
        if misses:
            lines.append("  未命中：")
            for m in misses:
                lines.append(f"    ✗ [{m.issue_type}] {m.issue_id}")
        hitsl = [i for i in r.issues if i.hit]
        if hitsl:
            lines.append("  命中：")
            for h in hitsl:
                lines.append(f"    ✓ [{h.issue_type}] {h.issue_id}  (匹配到「{h.matched_on}」)")

    lines.append("")
    lines.append("注意：命中判定是关键词匹配，是粗糙近似——QA 换个措辞描述同一问题会被判未命中。")
    lines.append("      这个数字适合同一套标注下的纵向对比，不宜当作绝对能力值。")
    lines.append("      建议人工扫一眼未命中列表，确认是真漏还是措辞不同。")
    return "\n".join(lines)


def render_repeated_report(groups: list[RepeatedCaseResult]) -> str:
    lines: list[str] = [
        "=" * 78,
        "QA Benchmark 结果（多次运行）",
        "=" * 78,
        "",
        "为什么要跑多次：同配置、同输入、同模型，两次运行的结果会不一样。",
        "实测例子：herbeast_v8 的「消费者评价极高」这条，一轮抓到、一轮没抓到。",
        "单次数字有噪声，判断改动是否有效时可能被波动淹没。",
    ]
    for g in groups:
        n = len(g.ok_runs)
        lines.append(f"\n## {g.case_id}  (model={g.model}, 跑了 {n} 次)")
        failed = [r for r in g.runs if r.error]
        if failed:
            lines.append(f"  ⚠️ {len(failed)} 次运行失败：{failed[0].error}")
        if not n:
            continue
        spread = "稳定" if g.min_recall == g.max_recall else f"波动 {g.min_recall:.0%}~{g.max_recall:.0%}"
        lines.append(
            f"  平均召回：{g.mean_recall:.0%}   "
            f"各次：{'、'.join(f'{v:.0%}' for v in g.recalls)}   [{spread}]"
        )
        lines.append("  逐条稳定性（命中次数/总次数，最难抓的排前面）：")
        for iid, itype, hits, total in g.issue_stability():
            if hits == 0:
                mark, note = "✗", "稳定漏掉"
            elif hits == total:
                mark, note = "✓", "稳定命中"
            else:
                mark, note = "~", "**不稳定**"
            lines.append(f"    {mark} [{itype}] {iid}  {hits}/{total}  {note}")

    lines.append("")
    lines.append("读法：")
    lines.append("  ✓ 稳定命中 = 这类问题 QA 可靠地能抓")
    lines.append("  ✗ 稳定漏掉 = 真实覆盖缺口，值得改规则或交给别的层")
    lines.append("  ~ 不稳定   = 运行波动，单次结果不足以下结论，别拿它证明改动有效")
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description="QA 审校 benchmark")
    parser.add_argument("--case", type=str, default="", help="只跑指定 case id")
    parser.add_argument("--all", action="store_true", help="跑全部 case")
    parser.add_argument("--model", type=str, default="", help="覆盖模型")
    parser.add_argument("--dry-run", action="store_true", help="只打印 prompt，不调 API")
    parser.add_argument(
        "--repeat",
        type=int,
        default=1,
        help="同一 case 重复跑几次，用于区分「真的变好」和「这次运气好」（建议 3）",
    )
    args = parser.parse_args()

    cases_cfg = yaml.safe_load(CASES_FILE.read_text(encoding="utf-8"))
    cases = cases_cfg["cases"]
    if args.case:
        cases = [c for c in cases if c["id"] == args.case]
        if not cases:
            print(f"找不到 case `{args.case}`，可选：{[c['id'] for c in cases_cfg['cases']]}")
            raise SystemExit(2)
    elif not args.all:
        print("请指定 --case <id> 或 --all")
        print(f"可选 case：{[c['id'] for c in cases]}")
        raise SystemExit(2)

    model = _resolve_model(args.model)

    if args.dry_run:
        for case in cases:
            prompt = build_qa_prompt(case)
            print(f"===== {case['id']} 的 prompt（{len(prompt)} 字符）=====")
            print(prompt[:2000])
            print(f"...（省略 {max(0, len(prompt) - 2000)} 字符）")
        return

    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_dir = RUNS_DIR / stamp
    out_dir.mkdir(parents=True, exist_ok=True)

    repeat = max(1, args.repeat)
    groups: list[RepeatedCaseResult] = []
    for case in cases:
        group = RepeatedCaseResult(case_id=case["id"], model=model)
        for n in range(1, repeat + 1):
            suffix = f" (第 {n}/{repeat} 次)" if repeat > 1 else ""
            print(f"[跑] {case['id']}{suffix} ...", flush=True)
            cr = CaseResult(case_id=case["id"], model=model, repeat_index=n)
            try:
                prompt = build_qa_prompt(case)
                cr.qa_output = call_model(prompt, model)
                cr.issues = score_case(case, cr.qa_output)
                name = f"{case['id']}_qa_output" + (f"_run{n}" if repeat > 1 else "") + ".md"
                (out_dir / name).write_text(cr.qa_output, encoding="utf-8")
            except Exception as exc:  # noqa: BLE001
                cr.error = f"{type(exc).__name__}: {exc}"
            group.runs.append(cr)
        groups.append(group)

    results = [r for g in groups for r in g.runs]
    report = render_repeated_report(groups) if repeat > 1 else render_report(results)
    print("\n" + report)
    (out_dir / "report.txt").write_text(report, encoding="utf-8")
    summary = {
        "timestamp": stamp,
        "model": model,
        "repeat": repeat,
        "cases": [
            {
                "case_id": g.case_id,
                "mean_recall": g.mean_recall,
                "recalls": g.recalls,
                "stability": [
                    {"id": iid, "type": itype, "hits": h, "runs": t}
                    for iid, itype, h, t in g.issue_stability()
                ],
                "runs": [
                    {
                        "run": r.repeat_index,
                        "recall": r.recall,
                        "hits": r.hits,
                        "total": r.total,
                        "error": r.error,
                        "issues": [
                            {"id": i.issue_id, "type": i.issue_type,
                             "detectable_by": i.detectable_by, "hit": i.hit}
                            for i in r.issues
                        ],
                    }
                    for r in g.runs
                ],
            }
            for g in groups
        ],
    }
    (out_dir / "summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(f"\n结果已存到 {out_dir}")


if __name__ == "__main__":
    main()
