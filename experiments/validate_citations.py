"""独立 CLI：对 outputs/ 下的研究报告做一次机械引用校验。

跟 `main.py` 跑完自动打印的报告是同一套逻辑（复用 src/marketing_crew/citation_check.py），
单独拎出来方便：
  1) 不重新跑一次昂贵的 crew，只想复查已有 outputs/*.md；
  2) 面试时单独演示"我加了什么校验"。

用法：
    PYTHONPATH=. python experiments/validate_citations.py
    PYTHONPATH=. python experiments/validate_citations.py outputs/backup_v3/*.md
"""

from __future__ import annotations

import glob
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.marketing_crew.citation_check import check_files  # noqa: E402

DEFAULT_TARGETS = [
    "outputs/market_feasibility.md",
    "outputs/market_expansion.md",
    "outputs/competitor_battlecard.md",
    "outputs/channel_strategy.md",
    "outputs/xhs_content_pack.md",
    "outputs/douyin_plan.md",
    "outputs/final_review.md",
]


def _resolve_targets(argv: list[str]) -> list[Path]:
    root = Path(__file__).resolve().parent.parent
    if not argv:
        return [root / p for p in DEFAULT_TARGETS]

    paths: list[Path] = []
    for pattern in argv:
        matches = glob.glob(pattern)
        if matches:
            paths.extend(Path(m) for m in matches)
        else:
            paths.append(Path(pattern))
    return paths


def main() -> None:
    targets = _resolve_targets(sys.argv[1:])
    existing = [p for p in targets if p.exists()]
    missing = [p for p in targets if not p.exists()]

    if missing:
        print("（以下文件不存在，跳过）")
        for p in missing:
            print(f"  - {p}")
        print()

    if not existing:
        print("没有可校验的文件。")
        raise SystemExit(0)

    report = check_files(existing)
    print(report.render())
    if report.total_errors:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
