"""检验工具自身的回归测试。

## 为什么单独给"检验工具"写测试

这个项目里，`citation_check` / `scoring_check` / guardrail 是用来判断报告质量的**尺子**。
尺子错了比报告错了更严重——报告错了只影响一份产出，尺子错了会让**所有版本的对比结论都反过来**。
项目里真实发生过两次：

1. 校验工具漏掉两类问题，基线被记成「5 处严重」，真实值是 15 处
2. QA benchmark 用品牌名当匹配键，召回率从真实的 38% 虚高到 75%

所以这里的每个用例都对应一个**真实踩过的坑**，注释里写明出处。

运行：`python -m pytest tests/ -q` 或 `python tests/test_checks.py`
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.marketing_crew.citation_check import (  # noqa: E402
    _check_tbd_placeholders,
    _strip_guardrail_banner,
    check_text,
)
from src.marketing_crew.config_loader import _resolve_registry_knowledge_files  # noqa: E402
from src.marketing_crew.scoring_check import check_scoring_text  # noqa: E402

PROJECT_ROOT = Path(__file__).resolve().parents[1]


# --------------------------------------------------------------------------
# 1. 占位符检测：区分「推诿」与「诚实声明」
#    出处：石头科技 v1。模型按 brief 要求写「未找到 | 级别 N/A」，
#    这是**正确行为**，却被判违规。根因是 TBD 与 N/A 被放进了同一张模式表。
# --------------------------------------------------------------------------

TBD_CASES = [
    # (文本, 应否拦截, 说明)
    ("- 未找到 Stiftung Warentest 评测。 | URL: 未找到 | 级别 N/A", False, "诚实声明缺失 + N/A"),
    ("| 能效登记 | 证据不足 | 级别 N/A |", False, "证据不足 + N/A"),
    ("| 竞品均价 | N/A | 来源 N/A |", True, "纯 N/A，没说明为什么没有"),
    ("| 依据 | TBD |", True, "推诿型：TBD"),
    ("| 依据 | 待补充 |", True, "推诿型：中文"),
    ("| 依据 | 未找到 | 备注 TBD |", True, "有诚实词也不放过 TBD"),
    ("| 市占 34% | URL: N/A |", True, "有数字却 N/A 且无说明"),
    # 出处：花知晓。URL 里的 `/en/all-brands/` 含子串 "en/a"，曾被误判成 n/a
    ("详见 https://www.watsons.co.th/en/all-brands/ 依据", False, "URL 内部字符误报"),
    ("我们在 N/A 市场没有布局", False, "非证据位，不该管"),
]


def test_tbd_placeholders() -> None:
    for text, should_flag, why in TBD_CASES:
        flagged = len(_check_tbd_placeholders(text, "t")) > 0
        assert flagged == should_flag, f"占位符检测失败：{why} | {text!r}"


# --------------------------------------------------------------------------
# 2. guardrail 失败标记剥离
#    出处：石头科技 v1。guardrail 把「miele.de 是裸域名首页」写进文首标记，
#    下一轮校验读到这句话，又把 miele.de 当成一条新违规重报一遍。
#    这是「检测器读到了自己的输出」，会让指标单调虚增。
# --------------------------------------------------------------------------


def test_strip_guardrail_banner_preserves_normal_text() -> None:
    plain = "# 报告\n\n> 这是一句普通引用\n\n正文 https://miele.de"
    assert _strip_guardrail_banner(plain) == plain, "无标记的文本不应被改动"


def test_strip_guardrail_banner_removes_self_report() -> None:
    banner = (
        "> ⚠️ **本文未通过引用校验，且已达到自动重试上限**（2 次）\n"
        "> - 【品牌首页当商品页】https://www.miele.de 是裸域名首页\n"
        ">\n\n# 竞品报告\n\n正文保留 https://www.amazon.de/dp/B0F3\n"
    )
    out = _strip_guardrail_banner(banner)
    assert "miele.de" not in out, "标记块里的违规 URL 应被剥离"
    assert "amazon.de" in out and "# 竞品报告" in out, "正文必须完整保留"


# --------------------------------------------------------------------------
# 3. 评分表自洽性
#    出处：全归档扫描发现 12 个带评分表的版本里 9 个算错自己的加权总分，
#    其中东边野兽 v8 写 3.35（按阈值该判「暂缓」）却下了「建议进入」的结论。
# --------------------------------------------------------------------------


def test_scoring_consistent_report_passes() -> None:
    t = (
        "- 结论：先验证假设、暂缓铺货\n\n"
        "加权总分 = (0.25×3) + (0.15×4) + (0.20×3) + (0.20×3) + (0.20×3) = 3.15\n"
    )
    assert not check_scoring_text(t, "ok").errors, "自洽的评分表不该报错"


def test_scoring_detects_arithmetic_error_and_contradiction() -> None:
    # 这就是东边野兽 v8 的真实数据
    t = "- 结论：建议进入\n\n加权总分 = 0.25*4 + 0.15*3 + 0.20*3 + 0.20*4 + 0.20*4 = 3.35\n"
    kinds = {i.kind for i in check_scoring_text(t, "v8").errors}
    assert "加权总分算错" in kinds, "应查出算术错误（真实 3.65）"
    assert "结论与评分表矛盾" in kinds, "3.35 按阈值应判暂缓，报告却写建议进入"


def test_scoring_detects_bad_weights() -> None:
    t = "- 结论：建议进入\n\n加权总分 = 0.3*4 + 0.3*4 + 0.3*4 = 3.6\n"
    assert "权重和不等于 1" in {i.kind for i in check_scoring_text(t, "w").errors}


def test_scoring_detects_out_of_range_score() -> None:
    t = "- 结论：建议进入\n\n加权总分 = 0.5*7 + 0.5*4 = 5.5\n"
    assert "维度得分越界" in {i.kind for i in check_scoring_text(t, "r").errors}


CLAIMED_TOTAL_CASES = [
    # (文本, 期望取到的总分, 说明)
    ("- 结论：建议进入。目标市场 2024 年增长 12.5%，加权总分见下表", None,
     "同行的无关数字（增长率）不能被当成总分"),
    ("- 结论：建议进入（加权总分 3.45）", 3.45, "括号形式"),
    ("| **总分** | 1.00 |  | **3.45** |", 3.45,
     "表格里权重和 1.00 离「总分」更近，但总分在最后一列"),
    ("| **加权总分** | | | **3.5** |", 3.5, "表格单元格"),
    ("总分3.45，建议进入泰国市场", 3.45, "数字紧贴无分隔符"),
    ("加权总分 = 3.5", 3.5, "等号形式"),
    ("| 维度 | 权重 | 评分 | 总分 |", None, "表头行没有数字"),
]


def test_claimed_total_extraction_does_not_invent_numbers() -> None:
    """取「声称总分」时不能抓错数字 —— 抓错会凭空造出违规。

    两个真实踩过的坑：
    1. 「建议进入。2024 年增长 12.5%」→ 早期实现取该行第一个小数，得到 12.5，
       再与重算的 3.45 比对，报出「总分算错：写 12.5 实际 3.45」这条**不存在的问题**
    2. 「| **总分** | 1.00 | | **3.45** |」→ 按「离总分最近」取值会得到权重和 1.00

    **校验工具误报比漏检更糟**：漏检只是没帮上忙，误报会让人不再信任整套指标，
    而这套指标正是本项目立论的基础。
    """
    from src.marketing_crew.scoring_check import _claimed_total_elsewhere

    for text, expected, why in CLAIMED_TOTAL_CASES:
        got = _claimed_total_elsewhere(text)
        assert got == expected, f"{why}：期望 {expected}，实际 {got}（原文 {text!r}）"


def test_missing_formula_is_warning_when_arithmetic_still_verifiable() -> None:
    """没有算式行但表格能重算且对得上 → 只是格式问题，不该判严重。

    出处：花知晓 depth_v1 / depth_research_v1 两份报告**数字完全正确**
    （声称 3.45、按表格行重算也是 3.45），却因为「没写算式行」被判 error。
    严重度必须与实际风险挂钩：算术已经被核对过了，就不是严重问题。
    """
    text = (
        "- 结论：建议进入\n\n"
        "| 维度 | 权重 | 评分 |\n"
        "| 需求匹配 | 0.25 | 4 |\n"
        "| 合规 | 0.25 | 3 |\n"
        "| 渠道 | 0.25 | 4 |\n"
        "| 竞争 | 0.25 | 3 |\n"
        "| **总分** | 1.00 | **3.50** |\n"
    )
    rep = check_scoring_text(text, "t")
    kinds = {(i.severity, i.kind) for i in rep.issues}
    assert ("warning", "缺少加权总分算式") in kinds, f"应降级为警告，实际 {kinds}"
    assert not rep.errors, f"数字对得上时不该有严重问题，实际 {[i.kind for i in rep.errors]}"


def test_missing_formula_is_error_when_unverifiable() -> None:
    """没有算式行、也重算不出来 → 算术闸真的关掉了 → 严重。"""
    text = "- 结论：建议进入\n\n需求匹配 0.25 权重，评分不错。\n"
    rep = check_scoring_text(text, "t")
    if rep.found_table:
        assert rep.errors, "无法核对时必须判严重"


def test_scoring_skips_documents_without_table() -> None:
    assert not check_scoring_text("# 竞品战卡\n\n没有评分表。", "x").found_table


# --------------------------------------------------------------------------
# 4. 知识包路由：短匹配词不能误命中
#    出处：本次自查。registry 里泰国的匹配词是 `th`，而匹配是子串比对，
#    导致 South Africa / Netherlands / North America / Ethiopia / Lithuania
#    **全部加载了泰国知识包**；`sea` 让「Seattle 地区」加载东南亚包。
#    这与当初把「英国」写死进模板是同一类 bug，且不会报错、只会安静带偏整份报告。
# --------------------------------------------------------------------------

MARKET_ROUTING_CASES = [
    # 必须命中
    ("泰国", "thailand"), ("Thailand", "thailand"), ("TH", "thailand"), ("th market", "thailand"),
    ("英国", "uk"), ("UK", "uk"), ("uk market", "uk"),
    ("德国", "germany"), ("Germany", "germany"), ("Deutschland", "germany"),
    ("越南", "vietnam"), ("VN", "vietnam"),
    ("东南亚", "sea_common"), ("SEA", "sea_common"),
    # 欧盟成员国：即便还没有国别包，也必须拿到欧盟通用框架
    ("法国", "eu_common"), ("France", "eu_common"), ("意大利", "eu_common"),
    ("Netherlands", "eu_common"), ("Sweden", "eu_common"), ("Denmark", "eu_common"),
    ("Lithuania", "eu_common"), ("欧盟", "eu_common"),
    ("德国", "eu_common"),  # 德国同时加载通用包与国别包
    # 必须回落到默认包 —— 修复前 South Africa / Ethiopia 这些全被误判成泰国
    ("South Africa", "_default"), ("North America", "_default"),
    ("Ethiopia", "_default"), ("Ukraine", "_default"),
    ("Seattle 地区", "_default"), ("新加坡", "_default"),
    ("Vancouver", "_default"), ("Bangladesh", "_default"), ("巴西", "_default"),
]


def test_market_knowledge_routing() -> None:
    """每个 market_scope 必须**包含**它应有的知识包。

    注意断言的是「包含」不是「等于第一个」：一个市场可以加载多个包
    （德国 = eu_common + germany，通用在前、国别在后）。
    早期版本这里断言 `files[0] == expected`，拆出欧盟通用包之后就失效了——
    这是断言写得比实际契约更严，属于测试自身的问题，不是行为回归。
    """
    knowledge_dir = PROJECT_ROOT / "knowledge"
    for scope, expected in MARKET_ROUTING_CASES:
        files = [
            f.replace("markets/", "").replace(".md", "")
            for f in _resolve_registry_knowledge_files(knowledge_dir, scope)
            if f.startswith("markets/")
        ]
        assert expected in files, f"market_scope={scope!r} 期望包含 {expected}，实际 {files}"


# --------------------------------------------------------------------------
# 4b. 知识包与地区码必须来自同一次匹配
#     出处：石头科技 v1。当时 market_scope→知识包 和 market_scope→地区码
#     是**两份手维护的表**，德国只进了前者，于是知识包按德国加载、
#     地区检测按空串整轮跳过，全程无提示。
#     现在合并成 registry.yaml 一张表，这些用例保证它不会再被拆开。
# --------------------------------------------------------------------------

LOCALE_CASES = [
    ("英国", "uk", False), ("UK", "uk", False),
    ("泰国", "th", False), ("Thailand", "th", False),
    ("德国", "de", False), ("Germany", "de", False),
    ("越南", "vn", False),
    # 有地区码但没有专属知识包 —— 必须仍返回地区码，并标记用了默认包
    ("日本", "jp", True), ("新加坡", "sg", True), ("马来西亚", "my", True),
    # 区域级：有知识包但**故意**没有地区码
    ("东南亚", "", False),
    # 完全没匹配上
    ("巴西", "", True),
]


def test_locale_and_pack_come_from_same_lookup() -> None:
    from src.marketing_crew.config_loader import resolve_market

    knowledge_dir = PROJECT_ROOT / "knowledge"
    for scope, want_locale, want_default_pack in LOCALE_CASES:
        r = resolve_market(knowledge_dir, scope)
        assert r.locale == want_locale, f"{scope}: 期望 locale={want_locale!r}，实际 {r.locale!r}"
        assert r.used_default_pack == want_default_pack, (
            f"{scope}: 期望 used_default_pack={want_default_pack}，实际 {r.used_default_pack}"
        )


def test_unknown_market_warns_loudly() -> None:
    """没匹配上时必须给出警告 —— 静默回落是这个项目反复出问题的根源。"""
    from src.marketing_crew.config_loader import resolve_market

    r = resolve_market(PROJECT_ROOT / "knowledge", "巴西")
    warns = r.warnings("巴西")
    assert warns, "未知市场必须产生警告"
    assert any("未匹配" in w for w in warns)


def test_known_market_with_full_pack_has_no_warning() -> None:
    from src.marketing_crew.config_loader import resolve_market

    for scope in ("英国", "泰国", "德国"):
        r = resolve_market(PROJECT_ROOT / "knowledge", scope)
        assert not r.warnings(scope), f"{scope} 配置完整，不该有警告"


def test_eu_country_gets_shared_pack_and_is_flagged_as_partial() -> None:
    """法国这类欧盟国家：拿得到欧盟通用框架，但必须提示「没有国别包」。

    出处：`germany.md` 里原本混着 CE / EU 能效标签 / GDPR 这些**全欧盟通用**的内容，
    导致研究法国时完全拿不到。拆出 `eu_common.md` 后，法国至少有统一制度框架；
    但语言标签、EPR 注册、VAT、主流电商逐国不同，
    所以「加载到了知识包」不能被当成「这个市场准备好了」。
    """
    from src.marketing_crew.config_loader import resolve_market

    r = resolve_market(PROJECT_ROOT / "knowledge", "法国")
    assert r.locale == "fr"
    assert [Path(f).stem for f in r.market_files] == ["eu_common"]
    assert r.only_shared_pack, "只有区域共享包时必须能被识别"
    assert any("没有该国的国别知识包" in w for w in r.warnings("法国"))


def test_germany_loads_shared_plus_country_pack() -> None:
    """德国 = 欧盟通用包 + 国别包，且顺序为「通用在前、国别在后」。"""
    from src.marketing_crew.config_loader import resolve_market

    r = resolve_market(PROJECT_ROOT / "knowledge", "德国")
    assert [Path(f).stem for f in r.market_files] == ["eu_common", "germany"]
    assert not r.only_shared_pack
    assert not r.warnings("德国"), "配置完整的市场不该有警告"


def test_eu_locales_are_known_to_citation_check() -> None:
    """registry 里配了 locale 的市场，citation_check 必须认得该地区段。

    否则「他国站点当本地商品页」检测会**静默失效**：路径里的地区段认不出来，
    检查直接跳过且不报错。这正是德国那次整轮跳过的翻版。
    """
    import yaml

    from src.marketing_crew.citation_check import _LOCALE_SEGMENTS

    registry = yaml.safe_load((PROJECT_ROOT / "knowledge" / "registry.yaml").read_text(encoding="utf-8"))
    configured = {
        str(m.get("locale") or "").strip().lower()
        for m in registry.get("market_mappings", [])
    } - {""}
    missing = configured - _LOCALE_SEGMENTS
    assert not missing, (
        f"registry.yaml 配了这些 locale 但 citation_check._LOCALE_SEGMENTS 里没有：{missing}。"
        "会导致这些市场的地区一致性检测静默失效。"
    )


def test_market_without_pack_warns_but_keeps_locale() -> None:
    """日本这类「有地区码、没知识包」的情况要提示，但地区检测不能跟着一起失效。"""
    from src.marketing_crew.config_loader import resolve_market

    r = resolve_market(PROJECT_ROOT / "knowledge", "日本")
    assert r.locale == "jp", "没有知识包不影响地区码"
    assert any("还没有专属知识包" in w for w in r.warnings("日本"))


def test_no_second_locale_table_in_code() -> None:
    """防止有人日后又在代码里加一份地区映射表。

    这条测试看起来很怪，但它守的正是本项目里代价最大的一类 bug：
    同一份知识维护在两个地方，漂移之后不报错。
    """
    crew_src = (PROJECT_ROOT / "src" / "marketing_crew" / "crew.py").read_text(encoding="utf-8")
    assert "_SCOPE_TO_LOCALE = (" not in crew_src, (
        "crew.py 里又出现了第二份地区映射表；市场映射只能维护在 knowledge/registry.yaml"
    )


# --------------------------------------------------------------------------
# 5. search_effort guardrail：判据取自审计日志，不看报告自述
#    出处：gap_fill_zero_search。补证 agent 跨三个案例 0 次工具调用，
#    报告里却写着三条「检索策略：搜索 xxx」。
# --------------------------------------------------------------------------


class _FakeListener:
    """替身 listener，避免测试时真去订阅 CrewAI 事件总线。"""

    def __init__(self, calls: list) -> None:
        self.calls = calls

    def calls_by_agent(self, role: str, status: str = "finished") -> list:
        return [c for c in self.calls if c.agent_role == role and c.status == status]


class _Out:
    def __init__(self, raw: str) -> None:
        self.raw = raw


ROLE = "证据缺口补证研究员"
CLEAN_TEXT = "# 报告\n\n- 事实 | https://www.amazon.de/dp/B01 | 级别 A\n"


def _guardrail_with(calls: list, **kw):
    from src.marketing_crew import tool_audit
    from src.marketing_crew.guardrails import build_guardrail
    from src.marketing_crew.tool_audit import ToolCall  # noqa: F401

    tool_audit._ACTIVE_LISTENER = _FakeListener(calls)
    return build_guardrail("search_effort", agent_role=ROLE, **kw)


def _call(query: str, role: str = ROLE, status: str = "finished"):
    from src.marketing_crew.tool_audit import ToolCall

    return ToolCall(tool_name="search", agent_role=role, args=f"search_query={query}", status=status)


def test_search_effort_blocks_zero_calls() -> None:
    ok, msg = _guardrail_with([])(_Out(CLEAN_TEXT))
    assert not ok, "0 次调用必须拦下"
    assert "0 次" in msg, "反馈里要给出真实调用次数，否则模型无从改起"


def test_search_effort_blocks_too_few_calls() -> None:
    ok, _ = _guardrail_with([_call("a"), _call("b")])(_Out(CLEAN_TEXT))
    assert not ok, "少于 3 次应拦下"


def test_search_effort_blocks_repeated_same_query() -> None:
    ok, _ = _guardrail_with([_call("a")] * 4)(_Out(CLEAN_TEXT))
    assert not ok, "同一 query 复读 4 次不算覆盖了多个角度"


def test_search_effort_passes_when_genuine() -> None:
    ok, _ = _guardrail_with([_call(q) for q in "abc"])(_Out(CLEAN_TEXT))
    assert ok, "3 次调用 / 3 个不同查询应通过"


def test_search_effort_does_not_count_other_agents() -> None:
    calls = [_call(q, role="竞品分析师") for q in "abcdef"]
    ok, _ = _guardrail_with(calls)(_Out(CLEAN_TEXT))
    assert not ok, "别的 agent 搜了多少都不算本 agent 的工作量"


def test_search_effort_soft_limit_passes_with_banner() -> None:
    g = _guardrail_with([], soft_max_retries=2)
    payload = ""
    for _ in range(3):
        ok, payload = g(_Out(CLEAN_TEXT))
    assert ok, "超过软上限后应放行，而不是让 CrewAI 抛异常中断流水线"
    assert "未通过检索投入校验" in payload, "放行时必须留下失败标记"


def test_search_effort_skips_when_audit_disabled() -> None:
    from src.marketing_crew import tool_audit
    from src.marketing_crew.guardrails import build_guardrail

    tool_audit._ACTIVE_LISTENER = None
    g = build_guardrail("search_effort", agent_role=ROLE)
    ok, _ = g(_Out(CLEAN_TEXT))
    assert ok, "--no-tool-audit 时没有客观依据，应放行而不是误伤"


def test_composed_guardrail_reports_search_first() -> None:
    """顺序有意义：一份零检索但格式漂亮的报告不该先通过引用校验。"""
    from src.marketing_crew import tool_audit
    from src.marketing_crew.guardrails import build_guardrail

    tool_audit._ACTIVE_LISTENER = _FakeListener([])
    g = build_guardrail("search_effort,citation", agent_role=ROLE, locale="de")
    ok, msg = g(_Out("# 报告\n\n| 市占 34% | https://example.com |\n"))
    assert not ok
    assert "次成功的工具调用" in str(msg), "应先报检索不足，而不是先报引用问题"


# --------------------------------------------------------------------------
# 6. 引用校验的老回归项：确保今天的改动没放松已有检测
# --------------------------------------------------------------------------


def test_fake_domain_still_detected() -> None:
    r = check_text("参考：https://example.com/report 高置信度", "t")
    assert any(i.severity == "error" for i in r.issues), "example.com 必须仍被拦"


def test_number_without_source_still_detected() -> None:
    """含数字却无来源，加「证据不足」也不豁免。

    注意字符串形态：必须带「依据 / 来源 / URL」这类**证据位标记**，检测才会介入。
    这是刻意的——正文里出现「市场增长约 25%」这种叙述性句子不该被当成引用违规，
    否则误报会淹没真问题。第一版测试就是漏了这个标记而误以为检测失效了。
    """
    r = check_text("- 市场份额：约 25%（证据不足） | 依据：无", "t")
    kinds = {i.kind for i in r.issues if i.severity == "error"}
    assert "无来源数字（兜底措辞不豁免）" in kinds, f"实际查出 {kinds}"


def test_opinion_without_source_still_detected() -> None:
    r = check_text("公开舆论/口碑线索：消费者反馈普遍积极", "t")
    assert any(i.severity == "error" for i in r.issues), "无来源的口碑断言必须拦"


# --------------------------------------------------------------------------
# 7. 真实归档文件回归 —— 比构造字符串更可信的基线
#    这些数字来自 experiments/rule_compliance_matrix.py 的历史记录。
#    如果哪天改动让它们对不上，说明尺子变了，跨版本对比就不再成立。
# --------------------------------------------------------------------------

ARCHIVE_BASELINES = [
    # (相对路径, 期望的严重问题种类与条数)
    (
        "outputs/花知晓/v2/competitor_battlecard.md",
        {"无来源数字（兜底措辞不豁免）": 3, "社媒账号页当舆论证据": 3, "品牌首页当商品页": 1},
    ),
]


def test_archived_files_match_recorded_baseline() -> None:
    from collections import Counter

    for rel, expected in ARCHIVE_BASELINES:
        path = PROJECT_ROOT / rel
        if not path.exists():
            continue  # 归档被移动时跳过，不制造假失败
        got = Counter(
            i.kind for i in check_text(path.read_text(encoding="utf-8"), rel).issues
            if i.severity == "error"
        )
        assert dict(got) == expected, f"{rel} 基线漂移：期望 {expected}，实际 {dict(got)}"


def _run_all() -> int:
    tests = [(n, f) for n, f in sorted(globals().items()) if n.startswith("test_") and callable(f)]
    failed = 0
    for name, fn in tests:
        try:
            fn()
            print(f"  ✓ {name}")
        except AssertionError as e:
            failed += 1
            print(f"  ✗ {name}\n      {e}")
    print(f"\n{len(tests) - failed}/{len(tests)} 通过")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(_run_all())
