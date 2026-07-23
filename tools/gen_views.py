#!/usr/bin/env python3
"""キャリア目的形成Wiki のビュー機械生成（board / list / relations）。

レコード（SSoT）からビューを決定論的に生成する。/view（LLM）と違い推論・要約・因果の
キュレーションは行わず、frontmatter・固定見出し・リンクの射影/逐語転記だけで組む。
確信度・ステータス・log は一切変更しない（読み取り専用）。

hwlint.py の Project クラス（records/history/log のパーサ）と共有ヘルパをそのまま再利用する。
"""
import argparse
import datetime
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from hwlint import (  # noqa: E402
    Project, parse_id_array, strip_comments, entity_of, referenced_ids,
)
# 型・関係・状態機械の定義は ontology.yaml が唯一の正本（ここに再定義しない）。
from ontology import (  # noqa: E402
    STATUS_EMOJI, STATUS_ORDER, RELATIONS, FICTIONAL_MARKERS, ENTITY_INFIXES, ENTITY_LABELS,
)


# ---- 共通ヘルパ ----

def fictional_acts(project) -> list:
    """本文に架空/シミュレーションマーカーを含む ACT の stem を並べる。"""
    return sorted(s for s in project.records if "-ACT-" in s
                  and any(m in project.records[s][2] for m in FICTIONAL_MARKERS))


def next_to_verify(project, purps) -> list:
    """次に外界で確かめるべき目的仮説＝確信度低 × 未検証/探索中。

    検証活動(ACT)が1本も紐づかない（未着手）ものを最優先に並べる。返り値は (stem, fm, has_act)。"""
    tested = referenced_ids(project, "purposes", infix="-ACT-")
    nxt = [(s, fm, s in tested) for s, fm, *_ in purps
           if fm.get("status") in {"未検証", "探索中"}]
    return sorted(nxt, key=lambda x: (x[2], int(x[1].get("confidence", "0") or 0), x[0]))


def testcard(text: str) -> str:
    m = re.search(r"## テストカード.*?(?=## 学習カード|\Z)", text, re.DOTALL)
    return m.group(0) if m else ""


def learning(text: str) -> str:
    m = re.search(r"## 学習カード.*\Z", text, re.DOTALL)
    return m.group(0) if m else ""


def collapse(text: str) -> str:
    """複数行・箇条書きを1行に畳む（インライン項目用）。HTMLコメントは除去。"""
    parts = [re.sub(r"^\s*[-*+]\s+", "", ln).strip()
             for ln in strip_comments(text).strip().splitlines() if ln.strip()]
    return " ".join(parts) if parts else "—"


def field_value(section: str, label: str) -> str:
    """テストカードのフィールドを逐語抽出（見出し形式／箇条書き形式の両対応）。"""
    m = re.search(rf"^###\s*{label}[^\n]*\n(.*?)(?=\n##|\Z)", section, re.DOTALL | re.MULTILINE)
    if not m:
        m = re.search(rf"^-\s*\*\*{label}[^*\n]*\*\*[^:：\n]*[:：]\s*(.*?)(?=\n-\s*\*\*|\n###|\n##|\Z)",
                      section, re.DOTALL | re.MULTILINE)
    if not m:
        return "—"
    block = re.split(r"\n\s*\|", m.group(1), maxsplit=1)[0]
    return collapse(block)


def h3_block(section: str, header: str) -> str:
    m = re.search(rf"###\s*{re.escape(header)}[^\n]*\n(.*?)(?=\n### |\n## |\Z)", section, re.DOTALL)
    return m.group(1).strip() if m else ""


def is_executed(lc: str) -> bool:
    """学習カードが実際に記入済みか（未実施の計画 ACT はプレースホルダのみ）を判定する。"""
    real = [ln.strip() for ln in strip_comments(h3_block(lc, "事実")).splitlines()
            if ln.strip() and not ln.strip().startswith("（") and "記入" not in ln
            and not ln.strip().startswith("観測した事実")]
    return bool(real)


def learning_point(lc: str) -> str:
    return collapse(h3_block(lc, "学びの要点"))


def index_by(project, kind, key_field) -> dict:
    idx = {}
    for stem, (_, fm, _) in project.records.items():
        if kind in stem:
            for ref in parse_id_array(fm.get(key_field, "")):
                idx.setdefault(ref, []).append(stem)
    return idx


def latest_dec_next_move(project):
    decs = sorted((s for s in project.records if "-DEC-" in s),
                  key=lambda s: (project.records[s][1].get("date", ""), s))
    if not decs:
        return None, None
    stem = decs[-1]
    m = re.search(r"##\s*次の一手\s*\n(.*?)(?=\n##|\Z)", project.records[stem][2], re.DOTALL)
    return stem, (collapse(m.group(1)) if m else None)


def header_lines(view: str, mode: str, today: str, fictional: list) -> list:
    lines = [f"<!-- 生成物: gen_views.py {view} による機械生成。手編集禁止。"
             f"`python3 tools/gen_views.py {view}` で再生成する。生成基準日: {today}（モード {mode or '—'}） -->"]
    if fictional:
        links = " ".join(f"[[{s}]]" for s in fictional)
        lines.append(f"<!-- ⚠️ 架空/シミュレーションデータを含む活動: {links}。"
                     f"これら由来の確信度・判断は実データ未検証。 -->")
    return lines


def mermaid_id(stem: str) -> str:
    return stem.replace("-", "_")


_SHORT_RE = re.compile(r"((?:" + "|".join(ENTITY_INFIXES) + r")-\d+)$")


def short_id(stem: str) -> str:
    m = _SHORT_RE.search(stem)
    return m.group(1) if m else stem


def trunc(s: str, n: int = 16) -> str:
    return s if len(s) <= n else s[:n] + "…"


def latest_reason(history) -> str:
    return history[-1]["reason"] if history else ""


def is_core(fm) -> bool:
    return fm.get("core", "").strip() == "true"


def purpose_links(project, ids) -> str:
    out = [f"[[{rid}]]" for rid in ids if rid in project.records and entity_of(rid) == "P"]
    return " ".join(out) if out else "—"


# ---- board ビュー（試行を1実験として時系列に） ----

def gen_board(project) -> str:
    mode = project.mode
    today = datetime.date.today().isoformat()
    purps = list(project.purpose_records())
    acts = sorted((s for s in project.records if "-ACT-" in s),
                  key=lambda s: (project.records[s][1].get("date", ""), s))

    dec_by_act = {}
    for stem, (_, fm, _) in project.records.items():
        if "-DEC-" in stem:
            label = f"{fm.get('type', '')}: {fm.get('title', '')} [[{stem}]]"
            for a in parse_id_array(fm.get("based-on", "")):
                dec_by_act.setdefault(a, []).append(label)

    def entry(stem) -> dict:
        _, fm, text = project.records[stem]
        lc = learning(text)
        executed = is_executed(lc)
        tc = testcard(text)
        return {
            "fm": fm, "ids": parse_id_array(fm.get("purposes", "")),
            "risk": fm.get("riskiest-assumption", "—") or "—",
            "method": field_value(tc, "方法"), "criteria": field_value(tc, "成功基準"),
            "result": (learning_point(lc) or "—") if executed else "（未実施・計画のみ）",
            "outcome": fm.get("outcome", "").strip() or ("—" if executed else "未実施"),
            "judgment": " / ".join(dec_by_act.get(stem, [])) or "—",
        }

    entries = {s: entry(s) for s in acts}

    L = header_lines("board", mode, today, fictional_acts(project))
    L += ["", f"# 試行ボード（{project.slug}）", ""]
    L.append("各 ACT（試行）を1実験として date 昇順に並べる。「最もリスクの高い前提」「結果（学びの要点）」"
             "「判定」はレコード（ACT frontmatter `riskiest-assumption`/`outcome`・学習カード）、"
             "「判断」は当該 ACT を `based-on` に持つ DEC 由来。すべて射影・逐語転記。")
    L.append("")

    L += ["## サマリ", "", "| # | 試行 | 最もリスクの高い前提 | 判定 | 判断（DEC） |", "|---|---|---|---|---|"]
    for i, s in enumerate(acts, 1):
        e = entries[s]
        L.append(f"| {i} | [[{s}]] {e['fm'].get('title', '')} | {e['risk']} | {e['outcome']} | {e['judgment']} |")
    L += ["", "---", ""]

    for i, s in enumerate(acts, 1):
        e = entries[s]
        fm = e["fm"]
        L.append(f"## 試行{i} — {fm.get('title', '')}"
                 f"（{fm.get('date', '')}・{fm.get('type', '')}） [[{s}]]")
        L += [
            "",
            f"- **対象目的**: {purpose_links(project, e['ids'])}",
            f"- **最もリスクの高い前提**: {e['risk']}",
            f"- **検証方法**: {e['method']}",
            f"- **成功基準**: {e['criteria']}",
            f"- **結果（学びの要点）**: {e['result']}",
            f"- **判定 / 判断**: {e['outcome']} ／ {e['judgment']}",
            "",
            "---",
            "",
        ]

    # 現在地（P スナップショット＋最新DECの戦略的現在地）
    L += ["## 現在地", ""]
    dec_stem, next_move = latest_dec_next_move(project)
    if next_move:
        L.append(f"- 次の一手（[[{dec_stem}]] より）: {next_move}")
        L.append("")
    L += ["| 目的仮説 | 確信度 | ステータス |", "|---|---|---|"]
    for stem, fm, _, _ in sorted(purps, key=lambda r: -int(r[1].get("confidence", "0") or 0)):
        emo = STATUS_EMOJI.get(fm.get("status", ""), "")
        L.append(f"| [[{stem}]] {fm.get('title', '')} | "
                 f"{fm.get('confidence', '')} | {emo}{fm.get('status', '')} |")
    nxt = next_to_verify(project, purps)
    legend = "・⚠️＝試行なし＝最優先" if any(not has_act for *_, has_act in nxt) else ""
    L += ["", f"**次に外界で確かめるべき目的**（確信度低 × 未検証/探索中{legend}）:", ""]
    for stem, fm, has_act in nxt:
        mark = "" if has_act else " ⚠️未着手（試行なし）"
        L.append(f"- [[{stem}]] {fm.get('title', '')}"
                 f"（確信度{fm.get('confidence', '')}・{fm.get('status', '')}）{mark}")
    L.append("")
    return "\n".join(L)


# ---- list ビュー（目的の系譜） ----

def related_links(stem, fm, act_by_purp) -> str:
    """派生元(←)・因果先(→ leads-to)・書換(revises)・検証活動(ACT逆引き) を1セルに畳む。"""
    parts = []
    if (df := fm.get("derived-from", "").strip()):
        parts.append(f"← 派生 [[{df}]]")
    if (rv := fm.get("revises", "").strip()):
        parts.append(f"⟲ 書換 [[{rv}]]")
    if (lt := parse_id_array(fm.get("leads-to", ""))):
        parts.append("→ " + " ".join(f"[[{t}]]" for t in lt))
    if (ct := parse_id_array(fm.get("counters", ""))):
        parts.append("⚡対抗 " + " ".join(f"[[{t}]]" for t in ct))
    if (acts := sorted(act_by_purp.get(stem, []))):
        parts.append(" ".join(f"[[{a}]]" for a in acts))
    return " ・ ".join(parts) if parts else "—"


def gen_list(project) -> str:
    mode = project.mode
    today = datetime.date.today().isoformat()
    purps = list(project.purpose_records())  # (stem, fm, body, history)
    stems = {s for s, _, _, _ in purps}
    act_by_purp = index_by(project, "-ACT-", "purposes")

    L = header_lines("list", mode, today, fictional_acts(project))
    L += ["", f"# 目的仮説リスト（{project.slug}）", ""]
    L.append("★=核心目的（`core`）。関連列は ← 派生元（`derived-from`）／⟲ 書換（`revises`）／"
             "→ 因果先（`leads-to`）／⚡対抗（`counters`）／検証活動（ACT）。")

    # 系譜グラフ（ノード=目的、矢印=leads-to / derived-from / revises）
    L += ["", "## 目的の系譜", "", "```mermaid", "flowchart TB"]
    for s, fm, _, _ in purps:
        core = "★" if is_core(fm) else ""
        status = fm.get("status", "")
        emo = STATUS_EMOJI.get(status, "")
        label = fm.get("short-title", "").strip() or trunc(fm.get("title", ""))
        lbl = f'{short_id(s)}{core} {label}<br/>確信度{fm.get("confidence", "")} {emo}{status}'
        L.append(f'    {mermaid_id(s)}["{lbl}"]')
    for s, fm, _, _ in purps:
        for t in parse_id_array(fm.get("leads-to", "")):
            if t in stems:
                L.append(f"    {mermaid_id(s)} -->|因果| {mermaid_id(t)}")
        df = fm.get("derived-from", "").strip()
        if df in stems:
            L.append(f"    {mermaid_id(df)} -.->|派生| {mermaid_id(s)}")
        rv = fm.get("revises", "").strip()
        if rv in stems:
            L.append(f"    {mermaid_id(s)} ==>|書換| {mermaid_id(rv)}")
    L += ["```", ""]

    # 目的仮説テーブル（確信度降順）
    members = sorted(purps, key=lambda x: -int(x[1].get("confidence", "0") or 0))
    L += ["## 目的仮説", "", "| ID | タイトル | 確信度 | ステータス | 関連 | 直近の根拠 |",
          "|---|---|---|---|---|---|"]
    for s, fm, _, hist in members:
        core = "★" if is_core(fm) else ""
        emo = STATUS_EMOJI.get(fm.get("status", ""), "")
        L.append(f"| [[{s}]]{core} | {fm.get('title', '')} | {fm.get('confidence', '')} | "
                 f"{emo}{fm.get('status', '')} | {related_links(s, fm, act_by_purp)} | "
                 f"{trunc(latest_reason(hist), 44)} |")
    L.append("")

    # 次に確かめるべき
    nxt = next_to_verify(project, purps)
    legend = "。⚠️＝試行なし＝最優先" if any(not has_act for *_, has_act in nxt) else ""
    L += [f"## 次に外界で確かめるべき目的（確信度低 × 未検証/探索中{legend}）", ""]
    for s, fm, has_act in nxt:
        mark = "" if has_act else " ⚠️未着手（試行なし）"
        L.append(f"- [[{s}]] {fm.get('title', '')}（確信度{fm.get('confidence', '')}・{fm.get('status', '')}）{mark}")
    L.append("")

    # ステータス別サマリ
    L += ["## ステータス別サマリ", "", "| ステータス | 件数 |", "|---|---|"]
    for st in STATUS_ORDER:
        cnt = sum(1 for _, fm, _, _ in purps if fm.get("status") == st)
        L.append(f"| {STATUS_EMOJI.get(st, '')}{st} | {cnt} |")
    L.append("")
    return "\n".join(L)


# ---- relations（関係グラフ）ビュー ----

def node_label(project, stem) -> str:
    fm = project.records[stem][1]
    if entity_of(stem) == "P":
        core = "★" if is_core(fm) else ""
        emo = STATUS_EMOJI.get(fm.get("status", ""), "")
        label = fm.get("short-title", "").strip() or trunc(fm.get("title", ""))
        return (f'{short_id(stem)}{core} {label}<br/>'
                f'確信度{fm.get("confidence", "")} {emo}{fm.get("status", "")}')
    return f'{short_id(stem)} {trunc(fm.get("title", ""), 20)}'


def relation_edges(project) -> list:
    edges = []
    for stem, (_, fm, _) in project.records.items():
        ent = entity_of(stem)
        for rel in RELATIONS:
            if rel.domain != ent:
                continue
            for tgt in parse_id_array(fm.get(rel.field, "")):
                if tgt in project.records and entity_of(tgt) == rel.range:
                    edges.append((rel, stem, tgt))
    return edges


def gen_relations(project):
    if not project.records:
        return None
    mode = project.mode
    today = datetime.date.today().isoformat()
    edges = relation_edges(project)

    L = header_lines("relations", mode, today, fictional_acts(project))
    L += ["", f"# 関係グラフ（{project.slug}）", ""]
    L.append("レコード間の型付きリンク（オントロジーの関係）を frontmatter から射影する。"
             "ノード=レコード、矢印=関係（ラベル=関係名）。関係の定義は "
             "[ontology.md](../../../../ontology.md) を参照。")

    L += ["", "## 型付き関係グラフ", "", "```mermaid", "flowchart LR"]
    for ent in ENTITY_INFIXES:
        members = sorted(s for s in project.records if entity_of(s) == ent)
        if not members:
            continue
        L.append(f'    subgraph {ent}["{ENTITY_LABELS.get(ent, ent)} {ent}"]')
        for s in members:
            L.append(f'      {mermaid_id(s)}["{node_label(project, s)}"]')
        L.append("    end")
    for rel, s, t in edges:
        L.append(f"    {mermaid_id(s)} -->|{rel.label}| {mermaid_id(t)}")
    L += ["```", ""]

    # 関係インデックス（forward・全関係型を必ず節として出す）
    L += ["## 関係インデックス", ""]
    for rel in RELATIONS:
        rel_edges = [(s, t) for r, s, t in edges if r.name == rel.name]
        L += [f"### {rel.label}（`{rel.field}`: {rel.domain}→{rel.range}）", ""]
        if not rel_edges:
            L += ["（該当なし）", ""]
            continue
        L += ["| 始点 | 関係 | 終点 |", "|---|---|---|"]
        for s, t in rel_edges:
            L.append(f"| [[{s}]] | {rel.label} → | [[{t}]] |")
        L.append("")

    # バックリンク索引（inverse・誰から参照されているか）
    incoming = {}
    for rel, s, t in edges:
        incoming.setdefault(t, {}).setdefault(rel.inverse_label, []).append(s)
    L += ["## バックリンク索引（誰から・どの関係で参照されているか）", ""]
    referenced = [s for s in sorted(project.records) if s in incoming]
    for stem in referenced:
        seg = " ／ ".join(f"{lbl}: " + " ".join(f"[[{x}]]" for x in srcs)
                          for lbl, srcs in incoming[stem].items())
        L.append(f"- [[{stem}]] ← {seg}")
    if not referenced:
        L.append("（被参照リンクがまだ無い）")
    L.append("")

    # 目的↔制約 接地（grounded-in）フィット
    purps = [s for s in sorted(project.records) if entity_of(s) == "P"]
    consts = [s for s in sorted(project.records) if entity_of(s) == "C"]
    if purps and consts:
        grounds_by_purp = {}
        for r, s, t in edges:
            if r.name == "grounded-in":
                grounds_by_purp.setdefault(s, []).append(t)
        L += ["## 目的↔制約 接地（grounded-in）", "",
              "各目的仮説がどの手中の鳥（制約C）に接地しているか。空白＝地に足がついていない目的。", "",
              "| 目的 | 接地する制約 |", "|---|---|"]
        for s in purps:
            fm = project.records[s][1]
            gs = grounds_by_purp.get(s, [])
            cov = " ".join(f"[[{c}]]" for c in gs) if gs else "**空白**"
            L.append(f"| [[{s}]] {fm.get('title', '')} | {cov} |")
        ungrounded = [s for s in purps if s not in grounds_by_purp]
        L += ["", "- **未接地の目的**（接地する制約がない）: "
              + (" ".join(f"[[{s}]]" for s in ungrounded) if ungrounded else "なし"), ""]
    return "\n".join(L)


VIEWS = {
    "board": ("board.md", gen_board),
    "list": ("purposes-list.md", gen_list),
    "relations": ("relations.md", gen_relations),
}


def resolve_slug(repo: Path, project):
    if project:
        return project
    cur = (repo / "projects" / "current.md").read_text(encoding="utf-8")
    m = re.search(r"current-project:\s*(\S+)", cur)
    return m.group(1) if m else None


def main() -> int:
    ap = argparse.ArgumentParser(description="キャリア目的形成Wiki のビュー機械生成（board / list / relations）")
    ap.add_argument("view", choices=list(VIEWS))
    ap.add_argument("--project", help="対象案件 slug（省略時は projects/current.md）")
    ap.add_argument("--repo", default=".", help="リポジトリルート")
    ap.add_argument("--out", help="出力先パス（省略時は wiki/views/<既定名> に書き込む）")
    args = ap.parse_args()
    repo = Path(args.repo).resolve()
    slug = resolve_slug(repo, args.project)
    root = repo / "projects" / (slug or "")
    if not slug or not (root / "wiki").is_dir():
        sys.exit(f"案件が見つからない: {slug!r}")
    filename, fn = VIEWS[args.view]
    out = fn(Project(root))
    if out is None:
        print(f"{slug}/{args.view}: 生成条件を満たさずスキップ")
        return 0
    dest = Path(args.out) if args.out else (root / "wiki" / "views" / filename)
    dest.write_text(out, encoding="utf-8")
    print(f"生成: {dest}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
