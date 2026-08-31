from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class ProjectBrief:
    """V1 聚焦市场 + 竞品分析；多数字段可选，允许 AI 检索与自行发现竞品。"""

    product_name: str
    product_description: str = ""
    target_audience: str = ""
    market_scope: str = ""
    goals: str = ""
    budget_range: str = ""
    focus_areas: list[str] = field(default_factory=list)
    known_competitors: list[str] = field(default_factory=list)
    product_materials: str = ""
    material_files: list[str] = field(default_factory=list)
    user_notes: str = ""
    constraints: list[str] = field(default_factory=list)
    # V2 内容策略再用；V1 可留空
    channel_priority: list[str] = field(default_factory=list)
    competitors: list[str] = field(default_factory=list)  # backward compat

    def __post_init__(self) -> None:
        if not self.known_competitors and self.competitors:
            self.known_competitors = list(self.competitors)

    def to_prompt_block(self) -> str:
        lines: list[str] = []

        def add(label: str, value: str) -> None:
            text = value.strip() if value else ""
            lines.append(f"- {label}: {text if text else '未提供'}")

        def add_list(label: str, items: list[str], empty_hint: str) -> None:
            if items:
                lines.append(f"- {label}: {'、'.join(items)}")
            else:
                lines.append(f"- {label}: {empty_hint}")

        add("product_name", self.product_name)
        add("product_description", self.product_description)
        add("target_audience", self.target_audience)
        add("market_scope", self.market_scope or "未指定（请结合资料与检索自行界定）")
        add("goals", self.goals)
        add("budget_range", self.budget_range)
        add_list(
            "focus_areas",
            self.focus_areas,
            "未指定（请从用户资料中自行提炼分析重点）",
        )
        add_list(
            "known_competitors",
            self.known_competitors,
            "未指定（请通过检索识别直接/间接竞品，并说明选择理由）",
        )
        add_list("material_files", self.material_files, "未指定")
        add_list(
            "channel_priority",
            self.channel_priority,
            "未指定（V1 不要求输出渠道策略）",
        )
        add_list("constraints", self.constraints, "无")

        if self.product_materials.strip():
            lines.append("\n## 用户提供的产品资料（优先引用）\n")
            lines.append(self.product_materials.strip())
        if self.user_notes.strip():
            lines.append("\n## 用户补充说明\n")
            lines.append(self.user_notes.strip())

        return "\n".join(lines)

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> ProjectBrief:
        allowed = {f.name for f in cls.__dataclass_fields__.values()}
        filtered = {k: v for k, v in payload.items() if k in allowed}
        return cls(**filtered)


@dataclass
class AblationResult:
    variant: str
    output_files: list[str]
    metrics: dict[str, Any]
