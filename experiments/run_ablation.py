from __future__ import annotations

import json
import shutil
import time
from pathlib import Path

from dotenv import load_dotenv

from evaluate_outputs import evaluate_output_files

load_dotenv()

from src.marketing_crew.crew import build_marketing_crew  # noqa: E402
from src.marketing_crew.models import ProjectBrief  # noqa: E402

VARIANTS = ["single_agent", "no_research_stage", "no_qa", "full"]


def _project_root() -> Path:
    return Path(__file__).resolve().parent.parent


def _output_files(root: Path) -> list[Path]:
    outputs = root / "outputs"
    return [
        outputs / "market_feasibility.md",
        outputs / "market_expansion.md",
        outputs / "competitor_battlecard.md",
        outputs / "channel_strategy.md",
        outputs / "xhs_content_pack.md",
        outputs / "douyin_plan.md",
        outputs / "final_review.md",
    ]


def _snapshot_variant(root: Path, variant: str, files: list[Path]) -> list[str]:
    target = root / "outputs" / "ablation" / variant
    target.mkdir(parents=True, exist_ok=True)
    copied: list[str] = []
    for file_path in files:
        if file_path.exists():
            dst = target / file_path.name
            shutil.copy(file_path, dst)
            copied.append(str(dst.relative_to(root)))
    return copied


def _default_brief() -> ProjectBrief:
    root = _project_root()
    return ProjectBrief.from_dict(
        json.loads((root / "briefs" / "sample_brief.json").read_text(encoding="utf-8"))
    )


def main() -> None:
    root = _project_root()
    files = _output_files(root)
    brief = _default_brief()
    rows = []

    for variant in VARIANTS:
        start = time.time()
        crew = build_marketing_crew(brief=brief, variant=variant)
        _ = crew.kickoff()
        elapsed = time.time() - start
        metrics = evaluate_output_files(files).to_dict()
        snapshot = _snapshot_variant(root, variant, files)
        rows.append(
            {
                "variant": variant,
                "elapsed_sec": round(elapsed, 2),
                "metrics": metrics,
                "outputs": snapshot,
            }
        )

    report_path = root / "outputs" / "ablation_report.json"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Ablation report saved: {report_path}")


if __name__ == "__main__":
    main()

