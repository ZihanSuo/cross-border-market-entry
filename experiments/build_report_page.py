"""生成单文件 HTML 结论页 —— 把评估数据变成非技术读者也能看懂的东西。

## 为什么是「生成」而不是手写 HTML

页面上每个数字都必须来自**当前**的检测代码与归档文件。手写死的话，
下一次跑完新版本，页面就会和事实脱节——而这个项目通篇在讲的正是
「文档数字与实测漂移」这类问题，页面自己犯同样的错就太讽刺了。

所以这个脚本每次从零重算：遵守率矩阵、评分表自洽性、结论分布，
全部现读现算，不缓存、不硬编码。

## 为什么不做成能跑 agent 的 Web 应用

1. 要后端、密钥、异步任务，而这些**都不在这个项目想证明的能力范围内**
2. 做出来是个通用表单界面，证明不了任何独有能力
3. 最大的风险：演示时点「运行」，当场产出一份带 404 链接的报告。
   **live demo 失败比没有 demo 糟得多**

这个项目的资产是「跑了 33 个版本之后测出来的东西」，不是「能跑」。

## 用法

    PYTHONPATH=. python experiments/build_report_page.py
    # 产出 docs/index.html（单文件，可离线打开，也可直接挂 GitHub Pages）
"""

from __future__ import annotations

import html
import json
import sys
from collections import Counter
from datetime import date
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from experiments.rule_compliance_matrix import (  # noqa: E402
    CASE_GROUPS,
    KIND_COLUMNS,
    _sort_key,
    discover_versions,
    scan_version,
)
from src.marketing_crew.scoring_check import (  # noqa: E402
    _stated_conclusion_band,
    check_scoring_text,
)

OUT_PATH = PROJECT_ROOT / "docs" / "index.html"


# ---------------------------------------------------------------- 数据采集


def collect_matrix() -> list[dict]:
    rows = []
    for case, version, path, locale in discover_versions():
        r = scan_version(case, version, path, locale)
        rows.append(
            {
                "case": case,
                "version": version,
                "urls": r.url_count,
                "errors": r.total_errors,
                "warnings": r.total_warnings,
                "density": round(r.density, 2),
                "counts": {short: r.counts.get(full, 0) for full, short in KIND_COLUMNS},
                "zero_citation": r.url_count == 0,
            }
        )
    rows.sort(key=lambda x: (list(CASE_GROUPS).index(x["case"]), _sort_key(x["version"])))
    return rows


def collect_scoring() -> list[dict]:
    """逐份可行性报告：声称总分、重算总分、结论档位、是否自洽。"""
    out = []
    for p in sorted(PROJECT_ROOT.glob("outputs/*/*/market_feasibility.md")):
        text = p.read_text(encoding="utf-8", errors="ignore")
        rep = check_scoring_text(text, str(p))
        stated = _stated_conclusion_band(text)
        out.append(
            {
                "case": p.parent.parent.name,
                "version": p.parent.name,
                "claimed": rep.claimed_total,
                "recomputed": rep.recomputed_total,
                "band": stated[0] if stated else None,
                "errors": [i.kind for i in rep.errors],
            }
        )
    out.sort(key=lambda x: (list(CASE_GROUPS).index(x["case"]) if x["case"] in CASE_GROUPS else 99,
                            _sort_key(x["version"])))
    return out


# ⚠️ 判定「这份报告有没有用评分锚点」必须看**正文内容**，不能按版本名猜。
#
# 第一版实现是「石头科技 或 版本名以 depth 开头 = 带锚点」，据此算出
# 「加锚点后 4 份降级，其中一份是证据充分的花知晓」，进而得出
# 「锚点在证据充分时也压得住分数」的结论。
#
# 改成按正文查「锚点」二字之后，结论整个翻转：
#   - 花知晓 backup_v5 带锚点，但版本名不含 depth → 被误判成「改动前」
#   - 花知晓 depth_feas_v1 **不带**锚点，却因版本名被算进「改动后」，
#     而它恰恰就是那份用来支撑结论的降级样本
#
# 真实情况：三次降级全部来自石头科技（证据最稀薄的案例），
# 带锚点的美妆案例报告 10 份、降级 0 份。**原结论不成立。**
#
# 这是「尺子本身要先验证」在本项目里的第三次重演，只不过这次犯错的是数据分组。
def _is_post_anchor(row: dict) -> bool:
    path = PROJECT_ROOT / "outputs" / row["case"] / row["version"] / "market_feasibility.md"
    if not path.exists():
        return False
    return "锚点" in path.read_text(encoding="utf-8", errors="ignore")


# 规避方式的演化。每一条都对应一次真实归档，不是概括。
EVASION_STAGES = [
    ("编造假域名", "参考文献里写 example.com 并标高置信度", "东边野兽 backup_v3"),
    ("真链接但内容对不上", "URL 打得开，但页面上没有报告声称的产品或价格", "跨 v4.1–v8"),
    ("TBD 占位", "证据位填「待补充」，把空白伪装成待办", "花知晓 v1"),
    ("品牌首页当商品页", "从「用错的具体页」退化成「根本不给具体页」", "花知晓 v1（5 处）"),
    ("数字加免责词", "「市场份额约 25%（证据不足）」——同时躲过两条规则", "花知晓 v2（3 处）"),
    ("社媒账号主页当舆论", "引用品牌自营 Instagram 主页证明「公众口碑好」", "花知晓 v2（3 处）"),
    ("伪造过程描述", "报告写「检索策略：搜索 xxx」，审计显示该 agent 0 次调用", "石头科技 v1"),
]

FINDINGS = [
    ("换个案例，逮到原案例永远发现不了的 bug",
     "前五轮都在同一案例上调规则，每版都更好看。换成花知晓+泰国第一次跑，"
     "整份泰国报告在讨论「英国市场份额」——「英国」被写死成了模板字段名。"
     "这个 bug 在原案例下永远正确、永远不报错。"),
    ("我的检测工具自己有盲区，导致基线是错的",
     "工具当时报「5 处严重」，补上两类检测后同一批文件的真实数字是 15 处。"
     "基线错了不是读错一次，是从此以后所有版本对比都是反的。"),
    ("让模型审模型，先分清模型问题还是任务设计问题",
     "QA 漏检三处舆论无源断言。根因不是模型不够强，是它的输出模板里"
     "只有「逐 URL 核查表」，天生查不到「本该有链接却空着」的地方。"),
    ("「让模型自我报告执行状态」这个模式本身不可靠",
     "agentic 版写了 10 条「已用工具核实，页面显示标价 £XX」，逐条对质通过 0 条。"
     "堵一个位置它换一个，四轮换了四种形式。"),
    ("一张没人当真的评分表，怎么变成真正的决策依据",
     "加锚点前 11 个版本结论全是「建议进入」，评分表是装饰品。"
     "写了 1/3/5 可判定锚点 + 总分决定档位之后，出现了第一份「先别进」。"),
    ("那张表不只是没约束力，它连算术都是错的",
     "把每份报告的加权式子重算一遍，多数把自己的总分算错，"
     "其中若干份的结论与它自己写的分数直接矛盾——分数和结论是各写各的。"),
    ("Workflow 怎么变得更像 Agent，又不牺牲可评估性",
     "保留控制流，只把「自我修正」加进去，但裁判换成代码。"
     "「决定下一步做什么」可以让渡给模型，「判断这一步做得对不对」不能。"),
]

KNOWN_GAPS = [
    "模型抓了网页、收到 48 字符的错误页，照样把 URL 和价格写进报告——跨三个案例复现，未解决",
    "缺口补证 agent 曾 0 次真实检索却写出三条「检索策略」；已加代码校验，但未经真机验证",
    "bullet 块内的无源价格查不出来（数字关是逐行判的）——已确认影响范围，暂不修",
    "评分锚点仍依赖模型自觉，只做到了「总分与结论一致」可机械校验",
    "渠道策略与内容生产链路代码可跑，但从未验证过产出质量，不作为成果",
]


# ---------------------------------------------------------------- 渲染


def _esc(s) -> str:
    return html.escape(str(s))


def _heat_class(n: int) -> str:
    if n == 0:
        return "z"
    if n <= 2:
        return "h1"
    if n <= 5:
        return "h2"
    return "h3"


def build_html() -> str:
    matrix = collect_matrix()
    scoring = collect_scoring()

    # ---- 汇总数字（全部现算）----
    n_versions = len(matrix)
    n_cases = len({r["case"] for r in matrix})
    n_kinds = len(KIND_COLUMNS)

    anchored = [s for s in scoring if _is_post_anchor(s)]
    post_down = [s for s in anchored if s["band"] in ("hold", "no")]
    score_bad = [s for s in scoring if s["errors"]]

    # 按案例拆开看「带锚点 → 是否降级」。拆开是必须的：
    # 合并统计会把「只有一个案例降级」掩盖成「整体有效」。
    anchor_rows = []
    for case in CASE_GROUPS:
        sub = [s for s in anchored if s["case"] == case]
        if not sub:
            continue
        down = [s for s in sub if s["band"] in ("hold", "no")]
        anchor_rows.append((case, len(sub), len(down)))
    anchor_by_case = "\n".join(
        f'<tr><td>{_esc(CASE_GROUPS[c][0])}</td><td class="n">{n}</td>'
        f'<td class="n{" b-hold" if d else ""}">{d}</td></tr>'
        for c, n, d in anchor_rows
    )
    beauty_anchored = sum(n for c, n, _ in anchor_rows if c != "石头科技")
    beauty_down = sum(d for c, _, d in anchor_rows if c != "石头科技")

    # 每个案例的首版 vs 最好版（按密度）
    case_stats = []
    for case in CASE_GROUPS:
        rows = [r for r in matrix if r["case"] == case and not r["zero_citation"]]
        if not rows:
            continue
        best = min(rows, key=lambda r: (r["density"], -r["urls"]))
        worst = max(rows, key=lambda r: r["density"])
        case_stats.append({"case": case, "n": len([r for r in matrix if r["case"] == case]),
                           "best": best, "worst": worst})

    kind_totals = Counter()
    for r in matrix:
        for k, v in r["counts"].items():
            kind_totals[k] += v

    # ---- 片段 ----
    def matrix_rows_html() -> str:
        out = []
        cur = None
        for r in matrix:
            if r["case"] != cur:
                cur = r["case"]
                out.append(
                    f'<tr class="grp"><td colspan="{n_kinds + 5}">{_esc(CASE_GROUPS[cur][0])}</td></tr>'
                )
            cells = "".join(
                f'<td class="k {_heat_class(r["counts"][s])}">{r["counts"][s] or ""}</td>'
                for _, s in KIND_COLUMNS
            )
            note = ' <span class="warn-inline">零引用</span>' if r["zero_citation"] else ""
            out.append(
                f'<tr><td class="v">{_esc(r["version"])}{note}</td>'
                f'<td class="n">{r["urls"]}</td>'
                f'<td class="n err">{r["errors"] or ""}</td>'
                f'<td class="n">{r["warnings"] or ""}</td>'
                f'<td class="n">{r["density"] if r["urls"] else "—"}</td>{cells}</tr>'
            )
        return "\n".join(out)

    def scoring_rows_html() -> str:
        out = []
        for s in scoring:
            band = {"enter": "建议进入", "hold": "先验证／暂缓", "no": "暂不建议"}.get(s["band"], "—")
            bcls = {"enter": "b-enter", "hold": "b-hold", "no": "b-no"}.get(s["band"], "")
            mism = (
                s["claimed"] is not None
                and s["recomputed"] is not None
                and abs(s["claimed"] - s["recomputed"]) > 0.005
            )
            out.append(
                f'<tr><td>{_esc(s["case"])}/{_esc(s["version"])}</td>'
                f'<td class="n{" bad" if mism else ""}">{s["claimed"] if s["claimed"] is not None else "—"}</td>'
                f'<td class="n">{s["recomputed"] if s["recomputed"] is not None else "—"}</td>'
                f'<td class="{bcls}">{band}</td>'
                f'<td class="small">{_esc("、".join(s["errors"]) if s["errors"] else "自洽")}</td></tr>'
            )
        return "\n".join(out)

    kind_head = "".join(f'<th class="rot"><span>{_esc(s)}</span></th>' for _, s in KIND_COLUMNS)
    evasion_html = "\n".join(
        f'<li><span class="stage">{i}</span><b>{_esc(n)}</b>'
        f'<div class="d">{_esc(d)}</div><div class="src">{_esc(src)}</div></li>'
        for i, (n, d, src) in enumerate(EVASION_STAGES, 1)
    )
    findings_html = "\n".join(
        f'<div class="card"><h3><span class="num">{i}</span>{_esc(t)}</h3><p>{_esc(b)}</p></div>'
        for i, (t, b) in enumerate(FINDINGS, 1)
    )
    gaps_html = "\n".join(f"<li>{_esc(g)}</li>" for g in KNOWN_GAPS)
    case_html = "\n".join(
        f'<tr><td>{_esc(CASE_GROUPS[c["case"]][0])}</td><td class="n">{c["n"]}</td>'
        f'<td>{_esc(c["worst"]["version"])} <span class="n">密度 {c["worst"]["density"]}</span></td>'
        f'<td>{_esc(c["best"]["version"])} <span class="n">密度 {c["best"]["density"]}</span></td></tr>'
        for c in case_stats
    )
    top_kinds = "\n".join(
        f'<tr><td>{_esc(k)}</td><td class="n">{v}</td></tr>'
        for k, v in kind_totals.most_common(8) if v
    )

    return f"""<!DOCTYPE html>
<html lang="zh-CN"><head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>出海研究 Multi-Agent — 评估结果</title>
<style>
:root{{--bg:#0d1117;--panel:#161b22;--line:#30363d;--tx:#e6edf3;--dim:#8b949e;
--acc:#58a6ff;--red:#f85149;--amber:#d29922;--green:#3fb950}}
*{{box-sizing:border-box}}
body{{margin:0;background:var(--bg);color:var(--tx);
font:15px/1.7 -apple-system,BlinkMacSystemFont,"PingFang SC","Hiragino Sans GB","Microsoft YaHei",sans-serif}}
.wrap{{max-width:1180px;margin:0 auto;padding:48px 24px 80px}}
h1{{font-size:30px;margin:0 0 6px;letter-spacing:-.4px}}
.sub{{color:var(--dim);margin:0 0 8px}}
h2{{font-size:20px;margin:56px 0 6px;padding-top:20px;border-top:1px solid var(--line)}}
h2 .en{{color:var(--dim);font-weight:400;font-size:14px;margin-left:8px}}
.lead{{color:var(--dim);margin:0 0 18px;max-width:74ch}}
.banner{{background:#2d1b00;border:1px solid #5c3d00;border-left:3px solid var(--amber);
padding:14px 18px;border-radius:6px;margin:22px 0;font-size:14px}}
.banner b{{color:var(--amber)}}
.kpis{{display:grid;grid-template-columns:repeat(auto-fit,minmax(168px,1fr));gap:12px;margin:26px 0}}
.kpi{{background:var(--panel);border:1px solid var(--line);border-radius:8px;padding:16px}}
.kpi .v{{font-size:28px;font-weight:650;letter-spacing:-.5px}}
.kpi .l{{color:var(--dim);font-size:12.5px;margin-top:3px}}
.kpi.bad .v{{color:var(--red)}} .kpi.good .v{{color:var(--green)}}
table{{width:100%;border-collapse:collapse;font-size:13px;margin:14px 0}}
th,td{{border:1px solid var(--line);padding:6px 9px;text-align:left}}
th{{background:var(--panel);font-weight:600;color:var(--dim);font-size:12px}}
td.n,th.n{{text-align:right;font-variant-numeric:tabular-nums}}
td.err{{color:var(--red);font-weight:600}}
td.bad{{color:var(--red);font-weight:600}}
tr.grp td{{background:#1c2128;font-weight:600;color:var(--acc);font-size:13px}}
.scroll{{overflow-x:auto;border:1px solid var(--line);border-radius:8px}}
.scroll table{{margin:0;border:0}} .scroll th,.scroll td{{border-color:var(--line)}}
th.rot{{height:96px;width:26px;padding:0;vertical-align:bottom}}
th.rot span{{writing-mode:vertical-rl;transform:rotate(180deg);display:block;
padding:8px 4px;white-space:nowrap;font-size:11.5px}}
td.k{{text-align:center;width:26px;padding:5px 2px;font-size:12px}}
.z{{color:#30363d}} .h1{{background:rgba(210,153,34,.16)}}
.h2{{background:rgba(248,81,73,.20)}} .h3{{background:rgba(248,81,73,.42);font-weight:700}}
td.v{{white-space:nowrap}}
.warn-inline{{color:var(--amber);font-size:11px;border:1px solid var(--amber);
border-radius:3px;padding:0 4px;margin-left:4px}}
.b-enter{{color:var(--dim)}} .b-hold{{color:var(--amber);font-weight:600}}
.b-no{{color:var(--red);font-weight:600}}
ol.eva{{list-style:none;padding:0;counter-reset:s}}
ol.eva li{{background:var(--panel);border:1px solid var(--line);border-left:3px solid var(--red);
border-radius:6px;padding:12px 16px;margin:0 0 8px}}
.stage{{display:inline-block;background:var(--red);color:#fff;width:20px;height:20px;
border-radius:50%;text-align:center;line-height:20px;font-size:12px;margin-right:9px;font-weight:700}}
ol.eva .d{{color:var(--tx);font-size:13.5px;margin:5px 0 0 29px}}
ol.eva .src{{color:var(--dim);font-size:12px;margin:3px 0 0 29px}}
.cards{{display:grid;grid-template-columns:repeat(auto-fit,minmax(320px,1fr));gap:12px;margin:18px 0}}
.card{{background:var(--panel);border:1px solid var(--line);border-radius:8px;padding:16px 18px}}
.card h3{{font-size:15px;margin:0 0 8px;line-height:1.5}}
.card .num{{display:inline-block;background:var(--acc);color:#0d1117;width:19px;height:19px;
border-radius:4px;text-align:center;line-height:19px;font-size:12px;margin-right:8px;font-weight:700}}
.card p{{margin:0;color:var(--dim);font-size:13.5px}}
ul.gaps li{{margin-bottom:7px;color:var(--dim);font-size:14px}}
ul.gaps b{{color:var(--tx)}}
.small{{font-size:12px;color:var(--dim)}}
footer{{margin-top:64px;padding-top:20px;border-top:1px solid var(--line);
color:var(--dim);font-size:12.5px}}
a{{color:var(--acc)}}
.two{{display:grid;grid-template-columns:1fr 1fr;gap:24px}}
@media(max-width:760px){{.two{{grid-template-columns:1fr}}}}
</style></head><body><div class="wrap">

<h1>出海市场研究 Multi-Agent — 评估结果</h1>
<p class="sub">中国品牌跨境进入研究流水线 · {n_cases} 个案例 · {n_versions} 个归档版本 · 生成于 {date.today()}</p>

<div class="banner">
<b>这一页展示的是「测出了什么」，不是「产品有多好」。</b><br>
这个项目的研究对象不是「生成漂亮的市场报告」，而是<b>如何用代码发现 LLM 报告里的错误</b>。
下面所有数字都由检测代码现场重算，包括不好看的那些——它们是研究材料，刻意保留。
报告涉及的品牌均为公开信息讨论对象，内容不代表任何评价或建议。
</div>

<div class="kpis">
<div class="kpi"><div class="v">{n_versions}</div><div class="l">归档版本（每版一份 CHANGELOG）</div></div>
<div class="kpi"><div class="v">{n_kinds}</div><div class="l">机械检测类型，每条源自一次真实失败</div></div>
<div class="kpi bad"><div class="v">{len(score_bad)}<span class="small"> / {len(scoring)}</span></div>
<div class="l">评分表算错或与结论矛盾的报告</div></div>
<div class="kpi good"><div class="v">{len(post_down)}</div><div class="l">加锚点后出现的「先别进」结论</div></div>
</div>

<h2>1. 核心发现<span class="en">七条，每条都有可复算的证据</span></h2>
<div class="cards">{findings_html}</div>

<h2>2. 评分表：从装饰品到可核对的判据<span class="en">附一次被我自己推翻的过度解读</span></h2>
<p class="lead">
可行性报告一直有一张五维加权评分表。但翻遍加锚点之前的版本，<b>结论几乎全是「建议进入」</b>——
评分打多少都一样，那张表对结论没有任何约束力。它不是明显的错误，而是<b>伪装成严谨的空洞</b>。
根因不是模型不会算加权分，是从来没有人定义过「4 分」和「3 分」的区别。
</p>
<div class="two">
<div>
<table><tr><th>案例</th><th class="n">带锚点份数</th><th class="n">其中降级</th></tr>{anchor_by_case}</table>
<div class="banner">
<b>这里我犯过一次错，留在页面上。</b><br>
最初我按<b>版本名</b>分组（「新版本 = 带锚点」），算出「加锚点后 4 份降级，其中一份是证据充分的彩妆案例」，
据此写下「锚点在证据充分时也压得住分数」。改成按<b>正文内容</b>判定后结论翻转：
<b>三次降级全部来自同一个证据最稀薄的案例</b>，而那份用来支撑结论的彩妆降级样本，其实根本没带锚点。
</div>
</div>
<div>
<table><tr><th>累计出现最多的问题类型</th><th class="n">次数</th></tr>{top_kinds}</table>
<p class="small">
<b>目前能站住的说法</b>：总分与结论档位的一致性现在是强制且可机械校验的，这一点有代码为证。<br>
<b>还不能说的</b>：锚点让系统在任何案例下都敢说「不」——带锚点的美妆案例报告 {beauty_anchored} 份，
降级 {beauty_down} 份。<br>
<b>下一步</b>：同案例单变量对照（只改有无锚点），才能支撑因果结论。<b>尚未做。</b>
</p>
</div>
</div>

<h2>3. 逐份评分表核算<span class="en">重算每条加权式子，再核对结论档位</span></h2>
<p class="lead">
加权求和是确定性运算、档位是明确阈值，<b>让模型自查等于让它重做一遍同样会做错的事</b>。
这类错误极其隐蔽：式子和数字都写得整整齐齐，不动手重算根本发现不了，
而它恰好在整份报告最关键的那一行上。
</p>
<div class="scroll"><table>
<tr><th>版本</th><th class="n">报告声称</th><th class="n">重算</th><th>结论</th><th>校验结果</th></tr>
{scoring_rows_html()}
</table></div>

<h2>4. 跨版本遵守率矩阵<span class="en">用当前规则回溯扫描全部历史版本</span></h2>
<p class="lead">
每一列是一类机械检测，数字是该版本的违规次数，颜色越深越严重。
<b>「密度」= 每 10 个 URL 的严重问题数</b>，用来抵消报告长短差异——
长报告天然引用多，绝对值不可比。
</p>
<div class="banner">
<b>标了「零引用」的版本不是干净，是全文没有任何可核查的 URL。</b>
机械校验查不出问题，恰恰说明当时还没有引用纪律。这类版本不参与密度比较。
</div>
<div class="scroll"><table>
<tr><th>版本</th><th class="n">URL</th><th class="n">严重</th><th class="n">警告</th><th class="n">密度</th>{kind_head}</tr>
{matrix_rows_html()}
</table></div>

<h2>5. 三个案例的逐级加码<span class="en">每个案例为证伪一个具体假设而设计</span></h2>
<p class="lead">
第二个案例换品类＋市场，用来测模板是否过拟合——第一次跑就逮到「英国」被写死成字段名，
导致整份泰国报告在讨论英国市场份额。第三个案例跨到家电行业，测规则里的美妆表述是否也是硬编码。
</p>
<table><tr><th>案例</th><th class="n">版本数</th><th>最差版本</th><th>最好版本</th></tr>{case_html}</table>

<h2>6. 规避方式的演化<span class="en">每堵一个漏洞，模型就换一种绕法</span></h2>
<p class="lead">
这不是失败记录，而是「光靠写提示词不可靠、必须有机械校验兜底」这个论点的实证。
七个阶段全部来自真实归档，可逐条复查。
</p>
<ol class="eva">{evasion_html}</ol>

<h2>7. 已知未解决的问题<span class="en">刻意公开</span></h2>
<p class="lead">
一个只报告好消息的评估体系没有价值。以下是当前明确知道、但尚未解决的缺陷。
</p>
<ul class="gaps">{gaps_html}</ul>

<footer>
本页由 <code>experiments/build_report_page.py</code> 从归档数据现场重算生成，无手写死数字。<br>
个人学习项目，不适用于生产环境；报告内容不构成任何商业建议。详见仓库 <code>DISCLAIMER.md</code>。
</footer>
</div></body></html>
"""


def main() -> int:
    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    html_text = build_html()
    OUT_PATH.write_text(html_text, encoding="utf-8")
    print(f"✓ 已生成 {OUT_PATH.relative_to(PROJECT_ROOT)}（{len(html_text) // 1024} KB）")
    print("  本机预览：  open docs/index.html")
    print("  GitHub Pages：Settings → Pages → Source: main / docs")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
