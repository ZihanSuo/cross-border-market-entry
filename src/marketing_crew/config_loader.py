from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

DEFAULT_TASK_ORDER = [
    "market_feasibility_task",
    "evidence_gap_fill_task",
    "market_expansion_task",
    "competitor_analysis_task",
    "channel_strategy_task",
    "xhs_content_task",
    "douyin_plan_task",
    "qa_review_task",
]


def load_yaml(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}
    if not isinstance(data, dict):
        raise ValueError(f"Expected mapping yaml at {path}, got {type(data).__name__}")
    return data


def project_paths(base_dir: Path) -> dict[str, Path]:
    config_dir = base_dir / "config"
    return {
        "base_dir": base_dir,
        "config_dir": config_dir,
        "agents_yaml": config_dir / "agents.yaml",
        "tasks_yaml": config_dir / "tasks.yaml",
        "tasks_dir": config_dir / "tasks",
        "prompts_dir": config_dir / "prompts",
        "outputs_dir": base_dir.parent.parent / "outputs",
        "knowledge_dir": base_dir.parent.parent / "knowledge",
    }


def _read_text_if_exists(path: Path) -> str:
    return path.read_text(encoding="utf-8") if path.exists() else ""


def _resolve_config_path(config_dir: Path, relative_path: str) -> Path:
    candidate = config_dir / relative_path
    if candidate.exists():
        return candidate
    raise FileNotFoundError(f"Config file not found: {candidate}")


def _normalize_task_spec(task_name: str, spec: dict[str, Any], config_dir: Path) -> dict[str, Any]:
    if "file" in spec and len(spec) == 1:
        task_path = _resolve_config_path(config_dir, spec["file"])
        loaded = load_yaml(task_path)
        if not isinstance(loaded, dict):
            raise ValueError(f"Task file must be a mapping: {task_path}")
        spec = loaded

    if "task_file" in spec:
        task_path = _resolve_config_path(config_dir, spec["task_file"])
        file_spec = load_yaml(task_path)
        merged = {**file_spec, **{k: v for k, v in spec.items() if k != "task_file"}}
        spec = merged

    if "name" not in spec:
        spec = {**spec, "name": task_name}
    return spec


def _load_task_file(config_dir: Path, tasks_dir: Path, file_path: Path) -> tuple[str, dict[str, Any]]:
    raw = load_yaml(file_path)
    if "name" in raw:
        task_name = str(raw["name"])
    else:
        task_name = file_path.stem
    return task_name, _normalize_task_spec(task_name, raw, config_dir)


def load_tasks_registry(config_dir: Path) -> dict[str, Any]:
    """
    Load task definitions from:
    1) config/tasks/*.yaml (one task per file)
    2) config/tasks.yaml inline `tasks` entries (override / backward compatible)
    """
    tasks_yaml_path = config_dir / "tasks.yaml"
    manifest = load_yaml(tasks_yaml_path) if tasks_yaml_path.exists() else {}

    tasks: dict[str, dict[str, Any]] = {}
    tasks_dir = config_dir / "tasks"
    if tasks_dir.exists():
        for file_path in sorted(tasks_dir.glob("*.yaml")):
            task_name, spec = _load_task_file(config_dir, tasks_dir, file_path)
            tasks[task_name] = spec

    inline_tasks = manifest.get("tasks", {})
    if isinstance(inline_tasks, dict):
        for task_name, spec in inline_tasks.items():
            if not isinstance(spec, dict):
                raise ValueError(f"Task `{task_name}` must be a mapping")
            if task_name in tasks:
                tasks[task_name] = {**tasks[task_name], **_normalize_task_spec(task_name, spec, config_dir)}
            else:
                tasks[task_name] = _normalize_task_spec(task_name, spec, config_dir)

    if not tasks:
        raise ValueError(
            "No tasks found. Add config/tasks/*.yaml or config/tasks.yaml `tasks` entries."
        )

    task_order = manifest.get("task_order", DEFAULT_TASK_ORDER)
    if not isinstance(task_order, list):
        raise ValueError("`task_order` must be a list of task names")

    unknown = [name for name in task_order if name not in tasks]
    if unknown:
        raise ValueError(f"`task_order` references unknown tasks: {unknown}")

    return {"task_order": task_order, "tasks": tasks}


def load_prompt_text(config_dir: Path, prompt_file: str | None) -> str:
    if not prompt_file:
        return ""
    prompt_path = _resolve_config_path(config_dir, prompt_file)
    return prompt_path.read_text(encoding="utf-8").strip()


def load_task_knowledge(
    knowledge_dir: Path,
    include_global_knowledge: bool,
    knowledge_files: list[str] | None,
) -> str:
    sections: list[str] = []

    if knowledge_files:
        for filename in knowledge_files:
            file_path = knowledge_dir / filename
            content = _read_text_if_exists(file_path)
            if content:
                sections.append(content)

    if include_global_knowledge:
        if knowledge_dir.exists():
            for file_path in sorted(knowledge_dir.glob("*.md")):
                if knowledge_files and file_path.name in knowledge_files:
                    continue
                content = file_path.read_text(encoding="utf-8")
                if content not in sections:
                    sections.append(content)

    return "\n\n".join(sections).strip()


def _normalize_scope(scope: str) -> str:
    return "".join(scope.lower().split())


# 短的拉丁字母匹配词（uk / th / vn / de / sea …）用子串比对会误命中一大片。
# 实测踩过：`th` 让 South Africa、Netherlands、North America、Ethiopia、Lithuania
# **全部加载了泰国知识包**；`sea` 让「Seattle 地区」加载东南亚包；`uk` 会命中 Ukraine。
# 后果跟当初把「英国」写死进模板是同一类——一份荷兰报告会引用泰国 FDA 备案制度，
# 而且因为知识包是"背景资料"，它不会报错，只会安静地把整份报告带偏。
#
# 解法：按长度分流。长词和中日韩词足够独特，子串比对没问题；
# **短拉丁词改成按「词」匹配**（在保留空格/标点的原文上切词），
# 这样 "UK market" 仍能命中 uk，而 "Ukraine" / "South Africa" 不会。
_SHORT_KEYWORD_MAX_LEN = 3
_WORD_SPLIT_RE = re.compile(r"[^a-z0-9]+")


def _is_short_latin(keyword: str) -> bool:
    return len(keyword) <= _SHORT_KEYWORD_MAX_LEN and keyword.isascii() and keyword.isalnum()


def _scope_matches_keyword(scope_raw: str, keyword_normalized: str) -> bool:
    """market_scope 是否命中某个匹配词。短拉丁词按词匹配，其余按子串匹配。"""
    if not keyword_normalized:
        return False
    if _is_short_latin(keyword_normalized):
        tokens = {t for t in _WORD_SPLIT_RE.split(scope_raw.lower()) if t}
        return keyword_normalized in tokens
    return keyword_normalized in _normalize_scope(scope_raw)


def _load_knowledge_registry(knowledge_dir: Path) -> dict[str, Any]:
    registry_path = knowledge_dir / "registry.yaml"
    if not registry_path.exists():
        return {}
    return load_yaml(registry_path)


@dataclass
class MarketResolution:
    """market_scope 解析结果。

    把「加载哪个知识包」和「按哪个地区做引用校验」放在一个结果里返回，
    是为了保证这两件事**永远来自同一次匹配**。它们曾经是两份独立的手维护表，
    结果德国只进了其中一份，导致整轮跑下来地区检测从未执行且无人察觉。
    """

    matched: bool = False          # 是否命中了某个市场条目
    locale: str = ""               # 引用校验地区码；空串表示不做地区检查
    market_files: list[str] = field(default_factory=list)
    used_default_pack: bool = True  # 是否回落到了默认知识包
    matched_keywords: list[str] = field(default_factory=list)

    @property
    def only_shared_pack(self) -> bool:
        """是否只拿到了区域共享包（如 eu_common / sea_common），没有国别包。

        约定：文件名以 `_common` 结尾的是跨国共享包。
        法国这种「有欧盟通用框架、无国别包」的情况必须能被识别出来并提示，
        否则「加载到了知识包」会被当成「这个市场准备好了」。
        """
        if not self.market_files or self.used_default_pack:
            return False
        return all(Path(f).stem.endswith("_common") for f in self.market_files)

    def warnings(self, market_scope: str) -> list[str]:
        """需要在运行前**显式提示**的情况。

        核心原则：**静默回落是这个项目里反复出问题的根源。**
        知识包没匹配上、地区码为空，都不算错误——但必须让人看见，
        否则「没报错」会被误读成「查过了没问题」。
        """
        out: list[str] = []
        if not self.matched:
            out.append(
                f"market_scope「{market_scope}」未匹配 knowledge/registry.yaml 里的任何市场条目。"
                "将使用默认知识包，且**不做地区一致性检查**"
                "（「他国站点当本地商品页」这项检测会整轮跳过）。"
                "若这是个正式案例，请到 registry.yaml 里补一条 market_mappings。"
            )
            return out
        if self.used_default_pack:
            out.append(
                f"market_scope「{market_scope}」命中了地区码 `{self.locale or '(空)'}`，"
                "但该市场**还没有专属知识包**，本次使用默认包。"
                "合规/渠道类内容将完全依赖模型检索，可信度低于已有知识包的市场。"
            )
        elif self.only_shared_pack:
            shared = "、".join(Path(f).stem for f in self.market_files)
            out.append(
                f"market_scope「{market_scope}」只加载到了区域共享包（{shared}），"
                "**没有该国的国别知识包**。区域包覆盖跨国统一的制度框架，"
                "但**语言标签、EPR/回收注册、VAT、主流电商、权威测评机构逐国不同**，"
                "这些必须靠现场检索，可信度低于有国别包的市场。"
            )
        if not self.locale:
            out.append(
                f"market_scope「{market_scope}」没有配置 locale，"
                "**「他国站点当本地商品页」检测将不执行**。"
                "这不等于该项通过——它没有被检查过。"
            )
        return out


def resolve_market(knowledge_dir: Path, market_scope: str) -> MarketResolution:
    """按 market_scope 解析知识包与地区码 —— 全项目唯一的市场映射入口。"""
    result = MarketResolution()
    registry = _load_knowledge_registry(knowledge_dir)
    if not registry:
        return result

    if _normalize_scope(market_scope):
        for mapping in registry.get("market_mappings", []) or []:
            if not isinstance(mapping, dict):
                continue
            keywords = mapping.get("match", []) or []
            if not isinstance(keywords, list):
                continue
            hits = [
                kw
                for kw in keywords
                if isinstance(kw, str)
                and _scope_matches_keyword(market_scope, _normalize_scope(kw))
            ]
            if not hits:
                continue
            result.matched = True
            result.matched_keywords = hits
            result.locale = str(mapping.get("locale") or "").strip().lower()
            files = [f for f in (mapping.get("files") or []) if isinstance(f, str)]
            result.market_files = files
            result.used_default_pack = not files
            break

    if not result.market_files:
        result.market_files = [
            f for f in (registry.get("default_market_files") or []) if isinstance(f, str)
        ]
        result.used_default_pack = True

    return result


def _resolve_registry_knowledge_files(knowledge_dir: Path, market_scope: str) -> list[str]:
    registry = _load_knowledge_registry(knowledge_dir)
    if not registry:
        return []

    files: list[str] = [
        f for f in (registry.get("core_files") or []) if isinstance(f, str)
    ]
    files.extend(resolve_market(knowledge_dir, market_scope).market_files)

    deduped_files: list[str] = []
    for file_path in files:
        if file_path not in deduped_files:
            deduped_files.append(file_path)
    return deduped_files


def build_task_description(
    spec: dict[str, Any],
    config_dir: Path,
    knowledge_dir: Path,
    brief_block: str,
    market_scope: str = "",
) -> str:
    parts: list[str] = []

    prompt_text = load_prompt_text(config_dir, spec.get("prompt_file"))
    if prompt_text:
        parts.append(prompt_text)

    description = spec.get("description", "")
    if description:
        parts.append(description.replace("{brief}", brief_block))

    include_global = bool(spec.get("include_global_knowledge", True))
    extra_files = list(spec.get("knowledge_files") or [])
    knowledge_mode = str(spec.get("knowledge_mode", "")).strip().lower()
    if knowledge_mode == "registry":
        for file_path in _resolve_registry_knowledge_files(knowledge_dir, market_scope):
            if file_path not in extra_files:
                extra_files.append(file_path)

    knowledge_text = load_task_knowledge(knowledge_dir, include_global, extra_files)
    if knowledge_text:
        parts.append("补充知识与规则（优先遵循）：\n" + knowledge_text)

    return "\n\n".join(part for part in parts if part.strip()).strip()
