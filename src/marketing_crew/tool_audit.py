"""工具调用审计：记录 agent 每一次真实的工具调用，用来核对报告里的「已核实」是不是真的。

## 为什么需要这个

agentic 版竞品分析的报告里写着：

    商品页 URL：https://www.weleda.co.uk/product/skin-food
    核实状态：**已用 scrape_page 核实，页面显示标价 £12.95**

但用 `experiments/verify_urls.py` 独立请求这条 URL，返回 **HTTP 404**——页面不存在，
不可能显示任何标价。同一份报告里另一条 Neal's Yard 的链接也是 404。

也就是说「已核实」这一栏是模型自己填的，而它填的内容与事实不符。这跟之前
QA 声称「相关网页的抓取和数据验证已成功完成」但报告里 0 个链接，是同一类问题：
**自我报告不可信，必须由代码独立记录。**

这个模块订阅 CrewAI 的工具事件总线，把每次工具调用的**真实情况**写进日志：
调用了哪个工具、传了什么参数（比如抓的是哪个 URL）、返回成功还是报错、
返回内容多长。跑完之后就能回答两个之前只能猜的问题：

1. 模型到底有没有调用 scrape_page？调了几次？抓的是哪些 URL？
2. 那些抓取是成功了还是报错了？报错了它有没有如实写进报告？

## 用法

    from marketing_crew.tool_audit import ToolAuditListener

    audit = ToolAuditListener(log_path=Path("outputs/tool_audit.jsonl"))
    crew.kickoff()
    print(audit.render_summary())

注意：listener 必须在 kickoff **之前**创建（构造函数里就完成了事件订阅）。
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

try:
    from crewai.events import BaseEventListener, crewai_event_bus  # type: ignore
    from crewai.events.types.tool_usage_events import (  # type: ignore
        ToolUsageErrorEvent,
        ToolUsageFinishedEvent,
        ToolUsageStartedEvent,
    )

    _EVENTS_AVAILABLE = True
except Exception:  # pragma: no cover - 老版本 CrewAI 没有事件总线
    BaseEventListener = object  # type: ignore
    crewai_event_bus = None  # type: ignore
    ToolUsageStartedEvent = ToolUsageFinishedEvent = ToolUsageErrorEvent = None  # type: ignore
    _EVENTS_AVAILABLE = False


# 当前活跃的审计 listener。由 ToolAuditListener.__init__ 设置，供 guardrail 查询。
# 一次运行只会创建一个 listener，所以模块级单例在这里是安全的。
_ACTIVE_LISTENER: "ToolAuditListener | None" = None


def get_active_listener() -> "ToolAuditListener | None":
    """取当前运行的审计 listener；没开审计（--no-tool-audit）时返回 None。"""
    return _ACTIVE_LISTENER


# 抓取类调用保存的内容长度上限。
# 取 20000 是权衡：足够覆盖商品页正文里出现价格的位置（实测抓回来的页面
# 多在 8000～25000 字符），又不至于让日志文件膨胀到难以处理。
SCRAPE_CONTENT_LIMIT = 20000


@dataclass
class ToolCall:
    tool_name: str
    agent_role: str = ""
    args: str = ""
    status: str = "started"     # started / finished / error
    output_preview: str = ""
    output_length: int = 0
    error: str = ""
    timestamp: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "timestamp": self.timestamp,
            "tool": self.tool_name,
            "agent": self.agent_role,
            "args": self.args,
            "status": self.status,
            "output_length": self.output_length,
            "output_preview": self.output_preview,
            "error": self.error,
        }


@dataclass
class ToolAuditListener(BaseEventListener):  # type: ignore[misc]
    """订阅工具事件，把真实调用记录下来。

    log_path 给了就同时写 jsonl，便于跑完之后用脚本核对。
    """

    log_path: Path | None = None
    calls: list[ToolCall] = field(default_factory=list)

    def __post_init__(self) -> None:
        if _EVENTS_AVAILABLE:
            # BaseEventListener 的 __init__ 会调用 setup_listeners 完成订阅
            super().__init__()
        if self.log_path:
            self.log_path.parent.mkdir(parents=True, exist_ok=True)
            self.log_path.write_text("", encoding="utf-8")

    # dataclass + BaseEventListener 混用时需要手动触发 __post_init__
    def __init__(self, log_path: Path | None = None) -> None:  # noqa: D107
        self.log_path = log_path
        self.calls = []
        self.__post_init__()
        # 注册为「当前活跃 listener」，让 guardrail 能在**运行中**查到实时调用记录。
        # 为什么需要：`search_effort` guardrail 要判断某个 agent 到底搜没搜，
        # 而它拿不到 listener 实例（guardrail 是在 build 阶段构造的，
        # listener 在 main 里创建）。用模块级引用是这里最省事且无副作用的接法——
        # 一次运行只会有一个 listener。
        global _ACTIVE_LISTENER
        _ACTIVE_LISTENER = self

    def calls_by_agent(self, agent_role: str, status: str = "finished") -> list[ToolCall]:
        """某个 agent 角色的调用记录。guardrail 用它判断「到底干活没有」。"""
        role = (agent_role or "").strip()
        return [c for c in self.calls if c.agent_role.strip() == role and c.status == status]

    def _record(self, call: ToolCall) -> None:
        self.calls.append(call)
        if self.log_path:
            with self.log_path.open("a", encoding="utf-8") as f:
                f.write(json.dumps(call.to_dict(), ensure_ascii=False) + "\n")

    @staticmethod
    def _is_scrape_args(args: str) -> bool:
        low = args.lower()
        return low.startswith("website_url=") or low.startswith("url=")

    @staticmethod
    def _fmt_args(raw: Any) -> str:
        if isinstance(raw, dict):
            # 抓取工具的关键参数是 website_url，搜索工具是 search_query
            for key in ("website_url", "url", "search_query", "query"):
                if key in raw:
                    return f"{key}={raw[key]}"
            return json.dumps(raw, ensure_ascii=False)[:200]
        return str(raw)[:200]

    def setup_listeners(self, bus: Any) -> None:  # noqa: D102
        if not _EVENTS_AVAILABLE:
            return

        @bus.on(ToolUsageStartedEvent)
        def _on_start(source: Any, event: Any) -> None:  # noqa: ANN401
            self._record(
                ToolCall(
                    tool_name=event.tool_name,
                    agent_role=event.agent_role or "",
                    args=self._fmt_args(event.tool_args),
                    status="started",
                    timestamp=datetime.now().isoformat(timespec="seconds"),
                )
            )

        @bus.on(ToolUsageFinishedEvent)
        def _on_finish(source: Any, event: Any) -> None:  # noqa: ANN401
            out = str(getattr(event, "output", "") or "")
            call = ToolCall(
                tool_name=event.tool_name,
                agent_role=event.agent_role or "",
                args=self._fmt_args(event.tool_args),
                status="finished",
                output_length=len(out),
                timestamp=datetime.now().isoformat(timespec="seconds"),
            )
            # 抓取类调用要留足内容：下游 experiments/verify_claims.py 靠它判断
            # 「报告声称的标价到底在不在页面上」。只存 300 字符时这个判据形同虚设
            # ——8 条声明全被判成"标价未见于预览"，而价格很可能就在第 400 字符处。
            # 搜索类调用不需要这么多，留短的即可控制日志体积。
            limit = SCRAPE_CONTENT_LIMIT if self._is_scrape_args(call.args) else 300
            call.output_preview = out[:limit].replace("\n", " ")
            self._record(call)

        @bus.on(ToolUsageErrorEvent)
        def _on_error(source: Any, event: Any) -> None:  # noqa: ANN401
            self._record(
                ToolCall(
                    tool_name=event.tool_name,
                    agent_role=event.agent_role or "",
                    args=self._fmt_args(event.tool_args),
                    status="error",
                    error=str(getattr(event, "error", ""))[:300],
                    timestamp=datetime.now().isoformat(timespec="seconds"),
                )
            )

    # ---------- 汇总 ----------

    @property
    def finished_calls(self) -> list[ToolCall]:
        return [c for c in self.calls if c.status == "finished"]

    @property
    def error_calls(self) -> list[ToolCall]:
        return [c for c in self.calls if c.status == "error"]

    @staticmethod
    def _is_scrape_call(call: ToolCall) -> bool:
        """判断一次调用是不是「抓网页」。

        **不能只按工具名里有没有 'scrape' 来判断**——这里踩过一个会导致
        完全错误结论的坑：`ScrapeWebsiteTool` 在 CrewAI 里的显示名是
        **"Read website content"**，压根不含 scrape 字样
        （同理 SerperDevTool 显示名是 "Search the internet with Serper"，
        不是配置里写的 `serper_search`）。
        如果只按名字过滤，审计会报「没有任何抓取调用」，
        而这个假阴性恰好出现在最关键的测量上，会让人误判成"模型纯编造"。

        所以改成双重判据：**参数里带 website_url/url 的**一律算抓取调用，
        名字匹配只作为补充。
        """
        args_low = call.args.lower()
        if args_low.startswith("website_url=") or args_low.startswith("url="):
            return True
        name_low = call.tool_name.lower()
        return any(k in name_low for k in ("scrape", "read website", "website content", "crawl"))

    def scraped_urls(self) -> list[tuple[str, str, int]]:
        """返回 (url, 状态, 返回内容长度)，只看抓取类工具。"""
        out: list[tuple[str, str, int]] = []
        for c in self.calls:
            if c.status == "started":
                continue
            if not self._is_scrape_call(c):
                continue
            url = c.args.split("=", 1)[1] if "=" in c.args else c.args
            out.append((url, c.status if c.status != "finished" else "ok", c.output_length))
        return out

    def render_summary(self) -> str:
        if not _EVENTS_AVAILABLE:
            return "（当前 CrewAI 版本不支持工具事件总线，未采集到调用记录）"
        lines = ["=" * 78, "工具调用审计（真实记录，非模型自述）", "=" * 78]
        if not self.calls:
            lines.append("\n⚠️ 本次运行**没有采集到任何工具调用**。")
            lines.append("   如果报告里写了「已核实」，那是模型编的。")
            return "\n".join(lines)

        by_tool: dict[str, list[ToolCall]] = {}
        for c in self.calls:
            if c.status != "started":
                by_tool.setdefault(c.tool_name, []).append(c)

        lines.append("")
        for tool, calls in sorted(by_tool.items()):
            ok = sum(1 for c in calls if c.status == "finished")
            err = sum(1 for c in calls if c.status == "error")
            lines.append(f"  {tool}: 共 {len(calls)} 次（成功 {ok}，报错 {err}）")

        scraped = self.scraped_urls()
        if scraped:
            lines.append("\n## 实际抓取过的 URL")
            for url, status, length in scraped:
                icon = "✅" if status == "ok" and length > 200 else "⚠️"
                extra = f"返回 {length} 字符" if status == "ok" else status
                lines.append(f"  {icon} {url}  （{extra}）")
            lines.append("")
            lines.append("  核对方法：把这份列表与报告「证据核实记录」里声称抓过的 URL 对照。")
            lines.append("  报告里有、这里没有的 → 那条「已核实」是编的。")
        elif any("website_url" in c.args or "scrape" in c.tool_name.lower() for c in self.calls):
            lines.append("\n⚠️ 检测到抓取类调用但未能解析出 URL，请查看 jsonl 原始记录。")
        else:
            lines.append("\n⚠️ **本次运行没有任何抓取工具调用记录**。")
            lines.append("   如果这次跑的 agent 配置里带了抓取工具，而报告又写了「已核实」，")
            lines.append("   那就是伪造；如果这个 agent 本来就没配抓取工具（如 feasibility_only），")
            lines.append("   则属正常，忽略此条。")

        if self.error_calls:
            lines.append("\n## 报错的调用（模型收到过这些错误，应如实写进报告）")
            for c in self.error_calls[:10]:
                lines.append(f"  ❌ {c.tool_name}  {c.args}")
                lines.append(f"     {c.error[:160]}")
        return "\n".join(lines)
