"""把机械校验接成 CrewAI guardrail —— 让 workflow 具备 agent 式的自我修正循环。

## 这解决什么问题

在此之前，`citation_check` 是**事后**把关：跑完打印一份报告，人看到问题再决定要不要
手工改或重跑。模型本身从来不知道自己违规了。

CrewAI 的 `Task.guardrail` 提供了一个机制：校验函数返回 `(False, 错误说明)` 时，
框架会把错误说明拼进 context **喂回给同一个 agent 重跑**（见 `crewai/task.py`
的 `_invoke_guardrail_function`），最多重试 `guardrail_max_retries` 次。

于是把 `citation_check` 挂上去，就得到一个闭环：

    产出 → 机械校验 → 有严重问题？
      ├─ 是 → 把具体违规逐条喂回模型 → 自动重跑
      └─ 否 → 通过，进入下一步

## 为什么这算「workflow 更像 agent」，又没丢掉可评估性

- **像 agent 的部分**：观察→行动→再观察的闭环、根据结果调整、自己收敛到合格。
  这是 agent 的核心特征之一（self-correction / reflexion）。
- **仍是 workflow 的部分**：控制流在代码手里、任务顺序固定、输出结构不变，
  所以跨版本遵守率矩阵依然成立。

关键区别在于**裁判是谁**：之前做过的 agentic 实验把「判断做得对不对」交给了模型
（结果它写了 10 条"已核实"、对质通过 0 条）；guardrail 把这个判断交给了代码。
**同样是循环，但裁判可信。**

## 已知取舍

1. **会增加成本**：每次重试都是一次完整的 task 执行（含工具调用）。
   所以默认只对「严重问题」触发重试，warning 不拦。
2. **不保证收敛**：模型可能连续 N 次都改不对，此时 CrewAI 会抛异常中断整条链路。
   因此 `guardrail_max_retries` 不宜设太大，且要能一键关掉（`--no-guardrails`）。
3. **只覆盖机械可查的问题**：编造的统计数字、过度推断这类语义问题仍然漏网，
   那是 QA 层和人工的职责。
"""

from __future__ import annotations

import os
from typing import Any

from .citation_check import check_text


def _format_issues(report: Any, max_items: int = 12) -> str:
    """把校验结果整理成模型能直接照着改的清单。

    刻意写得具体：每条包含「问题类型 + 出问题的 URL/原文 + 该怎么改」，
    而不是只说"有 N 处引用问题"——后者模型无从下手，大概率原样重写一遍。
    """
    errors = [i for i in report.issues if i.severity == "error"]
    lines: list[str] = [
        f"你的上一版产出没有通过机械引用校验，发现 {len(errors)} 处**严重问题**。",
        "这些是代码逐条扫出来的客观事实，不是主观意见。请针对每一条修改后重新输出完整报告。",
        "",
    ]
    for idx, issue in enumerate(errors[:max_items], 1):
        lines.append(f"{idx}. 【{issue.kind}】{issue.detail}")
        if issue.context:
            snippet = issue.context.strip().replace("\n", " ")[:150]
            lines.append(f"   出处：{snippet}")
    if len(errors) > max_items:
        lines.append(f"…… 另有 {len(errors) - max_items} 处同类问题，请一并检查。")

    lines += [
        "",
        "修改要求：",
        "- **不要**为了通过校验而删掉整段内容或改成含糊表述；",
        "  正确做法是换成合格的证据，或如实写「证据不足」",
        "- 「证据不足」只能用于**不含具体数字**的定性描述；",
        "  含百分比/标价/排名的行必须有可点击 URL，加免责词不豁免",
        "- 保持原有章节结构不变，只修有问题的地方",
    ]
    return "\n".join(lines)


def make_citation_guardrail(
    locale: str = "",
    max_report_items: int = 12,
    soft_max_retries: int = 2,
    agent_role: str = "",  # 未使用；为与 search_effort 保持统一签名，便于 build_guardrail 统一调用
):
    """构造一个 guardrail 函数，签名符合 CrewAI 的 `Callable[[TaskOutput], tuple[bool, Any]]`。

    Args:
        locale: 目标市场地区码（如 'uk'/'th'），用于「他国站点当本地商品页」检测。
                不传则跳过该项。
        max_report_items: 反馈给模型的问题条数上限，避免 context 过长。
        soft_max_retries: 软上限。超过后**放行并加失败标记**，而不是让 CrewAI
                抛异常中断流水线。应设得比 Task 的 `guardrail_max_retries` 小或相等，
                确保由我们这边先兜住。

    Returns:
        guardrail 函数。返回 `(True, 原文)` 表示通过；
        `(False, 错误说明)` 会让 CrewAI 把错误说明喂回 agent 并重跑。
    """

    # 闭包内自己数重试次数：CrewAI 在重试耗尽时会 **抛异常中断整条链路**
    # （`crewai/task.py`：raise Exception("Task failed ... after N retries")）。
    # 那会导致三个坏结果：
    #   1. 后续 task 全部不执行
    #   2. 本 task 的 callback 不触发 → 输出文件不会被写
    #   3. **上一次运行的旧文件原样留在磁盘上**，如果直接 cp 归档，
    #      看起来就像"跑成功了"——实测踩过：石头科技那轮的竞品报告，
    #      拷出来的其实是上一轮花知晓的泰国彩妆内容，逐字节相同。
    # 所以这里自己兜底：达到上限后**放行**，但在产出顶部插入醒目的失败标记，
    # 让问题留在文件里被后续机械校验和人工发现，而不是让整条链路猝死。
    state = {"attempts": 0}

    def _guardrail(task_output: Any) -> tuple[bool, Any]:
        text = getattr(task_output, "raw", None) or str(task_output)
        report = check_text(text, file_label="<guardrail>", expected_locale=locale)

        severe = [i for i in report.issues if i.severity == "error"]
        if not severe:
            # 通过。warning 不拦——那些需要人工判断，拦下来会让链路频繁卡死
            return (True, text)

        state["attempts"] += 1
        if state["attempts"] > soft_max_retries:
            banner = (
                "> ⚠️ **本文未通过引用校验，且已达到自动重试上限**"
                f"（{soft_max_retries} 次）。以下内容仍存在 "
                f"{len(severe)} 处严重问题，**不可直接当成品交付**，需人工修改。\n>\n"
                + "\n".join(f"> - 【{i.kind}】{i.detail[:110]}" for i in severe[:6])
                + "\n\n"
            )
            return (True, banner + text)

        return (False, _format_issues(report, max_report_items))

    # 给函数一个可读的名字，CrewAI 打印重试日志时会用到
    _guardrail.__name__ = f"citation_guardrail({locale or 'no-locale'})"

    # ⚠️ 必须显式把返回注解设回**真实的类型对象**。
    # 本文件开头有 `from __future__ import annotations`，会让所有注解在运行时变成
    # 字符串（这里就是 `"tuple[bool, Any]"`）。而 CrewAI 校验 guardrail 时会跑
    # `get_origin(sig.return_annotation) is tuple`（见 crewai/task.py:346），
    # 对字符串求 get_origin 得到 None，于是报
    # 「If return type is annotated, it must be Tuple[bool, Any]」。
    # 直接赋类型对象即可绕过，且保留了注解的文档价值。
    _guardrail.__annotations__["return"] = tuple[bool, Any]

    return _guardrail


def make_search_effort_guardrail(
    locale: str = "",
    max_report_items: int = 12,
    soft_max_retries: int = 2,
    agent_role: str = "",
    min_searches: int = 3,
    min_distinct_queries: int = 2,
):
    """要求这一步**真的做过检索**，判据取自工具审计日志而不是报告自述。

    ## 这解决什么问题

    「缺口补证」这一步跨三个案例都是 0 次搜索。一开始我以为是搜索失败，
    查审计日志才发现更糟：**这个 agent 一次工具调用都没有发起过**，
    但它的报告里写着

        - 检索策略：搜索 "Zeo洗烘一体机 德国销量"；使用德语与英语增加覆盖面。
        - 检索策略：搜索 "Stiftung Warentest Zeo洗烘一体机 评测"。

    三条「检索策略」，零次真实检索。而它给出的 URL，2/3 是从上游可行性报告里
    照抄的（同一条 jiemian.com 链接用了两次），剩下 1 条来路不明。

    ## 根因不是模型偷懒，是任务设计留了一条零成本的合规路径

    任务规则写着「没有真实链接就写『证据不足 / 本轮检索无果』」。这条规则本意是
    反对编造，但它同时造成了一个后果：**每个缺口都写「本轮检索无果」是完全合规的输出，
    而且不需要做任何工作。**验收标准只看产出格式，不看有没有真的去查。

    模型找到了这条路径。这跟引用规则被逐条绕过是同一个模式：
    **只要「假装做了」比「真的做」便宜，模型就会选前者**，
    而这跟提示词写得多严厉无关——得让「假装」在结构上不可能通过。

    ## 判据

    完全客观，全部来自审计日志，不需要模型配合：

    - 该 agent 角色名下 **finished 状态**的调用次数 ≥ `min_searches`
    - 其中不同 query 的个数 ≥ `min_distinct_queries`（防止同一条 query 复读充数）

    ## 已知限制（写出来免得以后误以为它保证了什么）

    1. 它只能证明「搜过」，**不能证明「搜到的东西被用进了报告」**。
       模型完全可以搜三次然后无视结果——这正是「工具用了却不看结果」那个老问题，
       归 `verify_claims.py` 的事后对质负责，不归这里。
    2. `--no-tool-audit` 时审计关闭，本 guardrail 会**放行并提示**，
       因为此时没有任何客观依据，拦下来只会变成误伤。
    """
    from .tool_audit import get_active_listener

    state = {"attempts": 0}

    def _guardrail(task_output: Any) -> tuple[bool, Any]:
        text = getattr(task_output, "raw", None) or str(task_output)
        listener = get_active_listener()

        if listener is None or not agent_role:
            # 没有审计就没有客观依据 —— 放行，但不假装检查过
            return (True, text)

        calls = listener.calls_by_agent(agent_role, status="finished")
        queries = {c.args for c in calls if c.args}
        n_calls, n_queries = len(calls), len(queries)

        if n_calls >= min_searches and n_queries >= min_distinct_queries:
            return (True, text)

        state["attempts"] += 1
        if state["attempts"] > soft_max_retries:
            banner = (
                "> ⚠️ **本文未通过检索投入校验，且已达到自动重试上限**"
                f"（{soft_max_retries} 次）。工具审计显示本步骤只发起了 "
                f"**{n_calls} 次**成功的工具调用（{n_queries} 个不同查询），"
                f"低于要求的 {min_searches} 次 / {min_distinct_queries} 个。\n>\n"
                "> 因此本文中所有「检索策略」「本轮检索无果」的表述**都不能当作真的检索过**，"
                "其中的 URL 很可能来自上游报告或模型记忆。**需人工重新核实。**\n\n"
            )
            return (True, banner + text)

        feedback = (
            f"你这一步只发起了 {n_calls} 次成功的工具调用"
            f"（{n_queries} 个不同查询），**这是工具审计日志记录的客观事实，不是主观判断**。\n\n"
            f"本任务的核心就是「做第二轮真实检索」，要求至少 {min_searches} 次调用、"
            f"覆盖至少 {min_distinct_queries} 个不同查询。\n\n"
            "特别注意以下几点：\n"
            "- **「本轮检索无果」只有在真的搜过之后才能写**；没搜就写它属于伪造过程描述\n"
            "- **不要把上游报告里已有的 URL 当成自己新查到的事实**——那不是补证，是复述\n"
            "- 每个缺口至少覆盖两个角度：(A) 态度/概念/趋势，(B) 当地零售平台或品牌名+渠道名\n"
            "- 换关键词、换语言（目标市场本地语言往往比中文/英文更有效）\n\n"
            "请**先实际调用搜索工具**，再根据真实返回结果重写这份报告。"
        )
        return (False, feedback)

    _guardrail.__name__ = f"search_effort_guardrail({agent_role or 'no-role'})"
    _guardrail.__annotations__["return"] = tuple[bool, Any]
    return _guardrail


def make_artifact_feasibility_guardrail(
    locale: str = "",
    max_report_items: int = 12,
    soft_max_retries: int = 2,
    agent_role: str = "",
):
    """Depth V1：可行性硬证据地板不过就喂回重跑（裁判是代码）。"""
    from .artifact_check import check_feasibility_artifacts
    from .tool_audit import get_active_listener

    state = {"attempts": 0}

    def _guardrail(task_output: Any) -> tuple[bool, Any]:
        text = getattr(task_output, "raw", None) or str(task_output)
        audit = get_active_listener()
        report = check_feasibility_artifacts(text, audit=audit)
        severe = report.errors
        if not severe:
            return (True, text)

        state["attempts"] += 1
        if state["attempts"] > soft_max_retries:
            banner = (
                "> ⚠️ **本文未通过 Depth 硬证据地板，且已达到自动重试上限**"
                f"（{soft_max_retries} 次）。仍有 {len(severe)} 处严重问题，"
                "**不可直接当成品交付**。\n>\n"
                + "\n".join(f"> - 【{i.code}】{i.message[:120]}" for i in severe[:6])
                + "\n\n"
            )
            return (True, banner + text)

        lines = [
            f"你的上一版未通过 Depth 硬证据地板（{len(severe)} 处严重）。",
            "以下是代码扫出来的客观问题，请按条修改后输出**完整**报告：",
            "",
        ]
        for idx, issue in enumerate(severe[:max_report_items], 1):
            lines.append(f"{idx}. 【{issue.code}】{issue.message}")
        lines += [
            "",
            "关键提醒：",
            "- 市场规模报告 / 法规页 / 品牌官网首页 / 社媒 **不能**充当渠道地板；",
            "- 请先搜索 KONVY、Shopee、Lazada、Beautrium 等零售触点；",
            "- 真找不到就在 `### 渠道/零售可见度` 写「证据不足」+ 已试 query（须真实搜过）。",
            "- 保持标准评分表；加权总分算式必须算术正确。",
        ]
        return (False, "\n".join(lines))

    _guardrail.__name__ = "artifact_feasibility_guardrail"
    _guardrail.__annotations__["return"] = tuple[bool, Any]
    return _guardrail


def make_scrape_effort_guardrail(
    locale: str = "",
    max_report_items: int = 12,
    soft_max_retries: int = 2,
    agent_role: str = "",
    min_scrapes: int = 2,
):
    """要求本步真的做过网页抓取（对照 tool_audit），专打「0 scrape 却写核实」。"""
    from .tool_audit import get_active_listener

    state = {"attempts": 0}

    def _is_scrape(call) -> bool:
        name = (call.tool_name or "").lower()
        args = (call.args or "").lower()
        if "website_url=" in args:
            return True
        return any(h in name for h in ("scrape", "read website", "website content"))

    def _guardrail(task_output: Any) -> tuple[bool, Any]:
        text = getattr(task_output, "raw", None) or str(task_output)
        listener = get_active_listener()
        if listener is None:
            return (True, text)

        scrapes = [
            c
            for c in listener.calls
            if c.status == "finished"
            and _is_scrape(c)
            and (not agent_role or agent_role in (c.agent_role or "") or "竞品" in (c.agent_role or ""))
        ]
        if len(scrapes) >= min_scrapes:
            return (True, text)

        state["attempts"] += 1
        if state["attempts"] > soft_max_retries:
            banner = (
                "> ⚠️ **本文未通过抓取投入校验，且已达到自动重试上限**"
                f"（{soft_max_retries} 次）。审计显示有效 scrape **{len(scrapes)}** 次，"
                f"低于要求的 {min_scrapes} 次。文中任何「已核实」都不可信。\n\n"
            )
            return (True, banner + text)

        feedback = (
            f"工具审计显示你只完成了 **{len(scrapes)}** 次有效网页抓取，"
            f"本任务要求至少 {min_scrapes} 次 `scrape_page`（website_url=…）。\n\n"
            "请先实际调用抓取工具打开至少 2 个单品页核对标价/SKU，再重写报告。"
            "只搜不抓、或把品牌官网首页当核实，都不算数。"
        )
        return (False, feedback)

    _guardrail.__name__ = f"scrape_effort_guardrail({agent_role or 'any'})"
    _guardrail.__annotations__["return"] = tuple[bool, Any]
    return _guardrail


def make_scoring_guardrail(
    locale: str = "",
    max_report_items: int = 12,
    soft_max_retries: int = 2,
    agent_role: str = "",
):
    """可行性评分表算术/档位不过就喂回重跑。

    专打「写 3.5、重算 3.65」这类伪装成量化的错误——必须由代码重算，不能靠模型自查。
    没有「加权总分 =」行时放行（非可行性产出）。
    """
    from .scoring_check import check_scoring_text

    state = {"attempts": 0}

    def _guardrail(task_output: Any) -> tuple[bool, Any]:
        text = getattr(task_output, "raw", None) or str(task_output)
        report = check_scoring_text(text, file_label="<scoring_guardrail>")
        if not report.found_table:
            return (True, text)

        severe = report.errors
        if not severe:
            return (True, text)

        state["attempts"] += 1
        if state["attempts"] > soft_max_retries:
            banner = (
                "> ⚠️ **本文未通过评分表自洽性校验，且已达到自动重试上限**"
                f"（{soft_max_retries} 次）。仍有 {len(severe)} 处严重问题，"
                "**不可直接当成品交付**。\n>\n"
                + "\n".join(f"> - 【{i.kind}】{i.detail[:120]}" for i in severe[:6])
                + "\n\n"
            )
            return (True, banner + text)

        lines = [
            f"你的上一版评分表未通过代码重算（{len(severe)} 处严重）。",
            "这是确定性算术错误，不是文风问题。请修正后输出完整报告：",
            "",
        ]
        for idx, issue in enumerate(severe[:max_report_items], 1):
            lines.append(f"{idx}. 【{issue.kind}】{issue.detail}")
            if issue.context:
                lines.append(f"   出处：{issue.context[:150]}")
        if report.recomputed_total is not None:
            lines += [
                "",
                f"正确加权总分应约为 **{report.recomputed_total:.2f}**。"
                "请写单独一行算式（权重乘得分再相加），把末尾数字改成该值，"
                "并确认开头结论档位与该分数一致"
                "（≥3.5 建议进入 / 2.5–3.5 先验证假设、暂缓铺货 / <2.5 暂不建议）。",
            ]
        lines += [
            "",
            "修改要求：先用计算器把 Σ(权重×得分) 算对，再写结论；不要先写结论再凑数字。",
        ]
        return (False, "\n".join(lines))

    _guardrail.__name__ = "scoring_guardrail"
    _guardrail.__annotations__["return"] = tuple[bool, Any]
    return _guardrail


def make_artifact_competitor_guardrail(
    locale: str = "",
    max_report_items: int = 12,
    soft_max_retries: int = 2,
    agent_role: str = "",
):
    """Depth V1：竞品硬证据地板（价带/摘录/scrape/可证伪）不过就喂回重跑。"""
    from .artifact_check import check_competitor_artifacts
    from .tool_audit import get_active_listener

    state = {"attempts": 0}

    def _guardrail(task_output: Any) -> tuple[bool, Any]:
        text = getattr(task_output, "raw", None) or str(task_output)
        audit = get_active_listener()
        report = check_competitor_artifacts(text, audit=audit)
        severe = report.errors
        if not severe:
            return (True, text)

        state["attempts"] += 1
        if state["attempts"] > soft_max_retries:
            banner = (
                "> ⚠️ **本文未通过 Depth 竞品硬证据地板，且已达到自动重试上限**"
                f"（{soft_max_retries} 次）。仍有 {len(severe)} 处严重问题，"
                "**不可直接当成品交付**。\n>\n"
                + "\n".join(f"> - 【{i.code}】{i.message[:120]}" for i in severe[:6])
                + "\n\n"
            )
            return (True, banner + text)

        lines = [
            f"你的上一版未通过 Depth 竞品硬证据地板（{len(severe)} 处严重）。",
            "请按条修改后输出完整报告：",
            "",
        ]
        for idx, issue in enumerate(severe[:max_report_items], 1):
            lines.append(f"{idx}. 【{issue.code}】{issue.message}")
        lines += [
            "",
            "关键提醒：",
            "- 必须先 `scrape_page` 至少 2 次核对标价（工具审计可见，禁止只写「已核实」）；",
            "- 价带表 ≥5 行：具体 SKU + THB/฿ 标价 + **单品页 URL**（禁止 mistine.com 这类官网首页）；",
            "- 摘录 ≥3 条带 URL；可证伪主张要有打脸条件与验证方法；",
            "- 禁止「待补充 / TBD」行；搜不到就少写几行并在正文声明不足，但地板仍可能失败——优先真搜。",
        ]
        return (False, "\n".join(lines))

    _guardrail.__name__ = "artifact_competitor_guardrail"
    _guardrail.__annotations__["return"] = tuple[bool, Any]
    return _guardrail


# guardrail 名称 → 工厂函数。task yaml 里写 `guardrail: citation` 即可挂上；
# 需要多个时写成逗号分隔（`guardrail: citation,search_effort`），按顺序全部通过才算过。
GUARDRAIL_FACTORIES = {
    "citation": make_citation_guardrail,
    "search_effort": make_search_effort_guardrail,
    "scrape_effort": make_scrape_effort_guardrail,
    "artifact_feasibility": make_artifact_feasibility_guardrail,
    "artifact_competitor": make_artifact_competitor_guardrail,
    "scoring": make_scoring_guardrail,
}


def _compose(guards: list[Any], soft_max_retries: int = 2):
    """把多个 guardrail 串起来：任一不通过就返回它的反馈。

    顺序有意义。Depth 可行性推荐：
    `artifact_feasibility,scoring,citation`
    —— 先渠道地板，再算术，再引用。

    **共享软上限（depth_v2 踩坑）**：每个子 guardrail 若各自 soft-pass，
    组合链路可在 CrewAI 耗尽 retries 前累计 6+ 次 False，整条流水线直接抛异常。
    因此组合时由本函数统一计数：累计 False 超过 soft_max_retries 后放行并打失败标记，
    保证后续 task 仍能跑、产出落盘。
    """

    state = {"fails": 0}

    def _combined(task_output: Any) -> tuple[bool, Any]:
        current = task_output
        for g in guards:
            ok, payload = g(current)
            if not ok:
                state["fails"] += 1
                if state["fails"] > soft_max_retries:
                    text = getattr(task_output, "raw", None) or str(task_output)
                    if not isinstance(text, str):
                        text = str(text)
                    banner = (
                        "> ⚠️ **组合 guardrail 已达共享软上限**"
                        f"（累计 {state['fails']} 次未通过 / 上限 {soft_max_retries}）。"
                        "以下问题仍未修干净，**不可直接当成品**；流水线继续以免整条 Crew 中断。\n>\n"
                        f"> {str(payload).replace(chr(10), chr(10) + '> ')[:800]}\n\n"
                    )
                    return (True, banner + text)
                return (False, payload)
            # 前一个 guardrail 可能改写了内容（例如加失败标记），
            # 用它的结果继续往下传，避免后面的检查看到的是旧文本。
            current = payload
        return (True, current)

    _combined.__name__ = (
        "composed_guardrail("
        + ",".join(getattr(g, "__name__", "g") for g in guards)
        + f",soft={soft_max_retries})"
    )
    _combined.__annotations__["return"] = tuple[bool, Any]
    return _combined


def build_guardrail(
    name: str,
    locale: str = "",
    soft_max_retries: int = 2,
    agent_role: str = "",
):
    """按名字构造 guardrail；未知名字返回 None（静默跳过，不阻断流水线）。

    `name` 支持逗号分隔的多个名字，例如 `citation,search_effort`。
    多个时：子 guardrail **不单独 soft-pass**（软上限交给组合层），避免重试预算被拆碎。
    """
    names = [n.strip().lower() for n in str(name).split(",") if n.strip()]
    if not names:
        return None

    def _make(n: str, child_soft: int):
        factory = GUARDRAIL_FACTORIES.get(n)
        if factory is None:
            return None
        return factory(
            locale=locale,
            soft_max_retries=child_soft,
            agent_role=agent_role,
        )

    if len(names) == 1:
        return _make(names[0], soft_max_retries)

    # 组合：子项永不单独放行；由 _compose 共享 soft_max_retries
    guards = []
    for n in names:
        g = _make(n, child_soft=10**9)
        if g is not None:
            guards.append(g)
    if not guards:
        return None
    if len(guards) == 1:
        return guards[0]
    return _compose(guards, soft_max_retries=soft_max_retries)


def guardrails_enabled() -> bool:
    """全局开关。设 `DISABLE_GUARDRAILS=1` 可关掉（调试或省钱时用）。"""
    return os.getenv("DISABLE_GUARDRAILS", "").strip() not in ("1", "true", "yes")


def make_output_writer(output_path: str):
    """构造一个 task callback，把**经过 guardrail 校验后**的产出写进文件。

    ## 为什么不能直接用 CrewAI 的 `output_file`

    这是踩出来的坑。CrewAI 的 `Task._execute_core` 里：

        result = agent.execute_task(...)        # 第 790 行，只在这里赋值一次
        ...
        task_output = self._invoke_guardrail_function(...)   # 第 839 行，重试在这里发生
        ...
        if self.output_file:
            content = (... else result)         # 第 865 行，写的是**没更新的 result**
            self._save_file(content)

    guardrail 重试产生的新内容只体现在返回的 `task_output` 里，而
    `_invoke_guardrail_function` 内部那个 `result` 是局部变量。所以：
    **guardrail 会正常拦截、模型也会改，但落到磁盘上的仍是第一次执行的原始版本。**

    实测证据：东边野兽那一轮，最终文件里有 4 处严重问题（品牌首页当商品页 ×2、
    市场份额舆论缺证据 ×2），而把同一份文件喂给 guardrail 函数会被正确拦下——
    说明 guardrail 逻辑没问题，问题在写文件用错了变量。

    ## 解法

    改用 `callback`：它在第 850 行执行（**早于** output_file 写入），
    收到的 `self.output` 就是 guardrail 校验后的 `task_output`。
    所以挂了 callback 的 task **必须不设 `output_file`**，否则会被原始版本覆盖。
    """
    from pathlib import Path

    def _write(task_output: Any) -> None:
        text = getattr(task_output, "raw", None) or str(task_output)
        path = Path(output_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")

    _write.__name__ = f"write_validated_output({output_path})"
    return _write
