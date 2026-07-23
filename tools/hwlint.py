#!/usr/bin/env python3
"""キャリア目的形成Wiki の決定論的 lint。

CLAUDE.md の不変ルールのうち機械検証可能なものだけをチェックする。
意味的チェック（矛盾する目的・長期放置など）は /lint スキル（LLM）が担い、両者で併用する。
"""
import argparse
import re
import sys
from dataclasses import dataclass
from functools import cached_property
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
# 語彙(enum)・型・関係・状態機械の定義は ontology.yaml が唯一の正本。ここには再定義しない。
from ontology import (  # noqa: E402
    STATUSES, TYPES_BY_ENTITY, C_TYPES, ACT_TYPES, DEC_TYPES, ID_RE, ENTITY_INFIXES, ENTITY_DIRS,
    CONFIDENCE_MIN, CONFIDENCE_MAX, FICTIONAL_CAP, FICTIONAL_MARKERS,
    EVIDENCE_TAGS, EVIDENCE_LADDER, EVIDENCE_RANK, EVIDENCE_FLOOR, EXTERNAL_RANK_MIN,
    STATUS_BOUNDS, RELATIONS, RELATIONS_BY_FIELD,
)


@dataclass
class Problem:
    level: str    # "error" | "warning"
    where: str    # レコードID または パス
    check: str    # チェック名（kebab-case）
    message: str


def parse_frontmatter(text: str) -> dict:
    m = re.match(r"^---\n(.*?)\n---(?:\n|$)", text, re.DOTALL)
    if not m:
        return {}
    fm = {}
    for line in m.group(1).splitlines():
        if ":" not in line:
            continue
        key, value = line.split(":", 1)
        fm[key.strip()] = re.sub(r"\s+#.*$", "", value).strip()
    return fm


def parse_id_array(value: str) -> list:
    return [x.strip() for x in value.strip("[]").split(",") if x.strip()]


def entity_of(stem: str) -> str:
    """レコード stem からエンティティ種別（P/C/ACT/REF/DEC）を返す。該当なしは空。"""
    for infix in ENTITY_INFIXES:
        if f"-{infix}-" in stem:
            return infix
    return ""


def strip_frontmatter(text: str) -> str:
    return re.sub(r"^---\n.*?\n---\n", "", text, count=1, flags=re.DOTALL)


def strip_comments(text: str) -> str:
    """HTMLコメント（<!-- ... -->）を除去する。コメント内の例示 wikilink は
    Obsidian でもグラフ辺を作らないため、リンク検査の対象から外す。"""
    return re.sub(r"<!--.*?-->", "", text, flags=re.DOTALL)


HISTORY_HEADER = "## 確信度履歴"


def parse_history(body: str) -> list:
    rows, in_section = [], False
    for line in body.splitlines():
        if line.startswith("## "):
            in_section = line.strip() == HISTORY_HEADER
            continue
        if in_section and line.lstrip().startswith("|"):
            cells = [c.strip() for c in line.strip().strip("|").split("|")]
            if len(cells) >= 5 and re.match(r"\d{4}-\d{2}-\d{2}$", cells[0]):
                rows.append({"date": cells[0], "confidence": cells[1],
                             "status": cells[2], "reason": cells[3], "activity": cells[4]})
    return rows


def referenced_ids(project, field, infix=None, where=None) -> set:
    """`field`（frontmatter の関係キー）で指されている終点IDの集合を返す。

    infix を渡すと始点レコード種別（例 "-ACT-"）で、where(fm)->bool を渡すと始点 frontmatter で
    さらに絞る。関係グラフの入次数（被参照）を「有無」で見る用途の共有ヘルパ。"""
    out = set()
    for stem, (_, fm, _) in project.records.items():
        if infix and infix not in stem:
            continue
        if where and not where(fm):
            continue
        out.update(parse_id_array(fm.get(field, "")))
    return out


class Project:
    def __init__(self, root: Path):
        self.root = root
        self.slug = root.name
        self.wiki = root / "wiki"
        self.records = {}
        self.history = {}   # P レコードの確信度履歴を読込時に1回だけパースしてキャッシュ
        self.stray = []
        for sub in ENTITY_DIRS.values():
            d = self.wiki / sub
            if not d.is_dir():
                continue
            for p in sorted(d.glob("*.md")):
                if not ID_RE.match(p.stem):
                    if not p.stem.endswith("-script"):
                        self.stray.append(p)
                    continue
                text = p.read_text(encoding="utf-8")
                self.records[p.stem] = (p, parse_frontmatter(text), text)
                if "-P-" in p.stem:
                    self.history[p.stem] = parse_history(text)
        log_path = self.wiki / "log.md"
        self.log = log_path.read_text(encoding="utf-8") if log_path.exists() else ""

    @cached_property
    def mode(self) -> str:
        """現在の探索モード（stage.md の current-mode。無ければ空）。表示専用・検証には使わない。"""
        p = self.wiki / "stage.md"
        if p.exists():
            m = re.search(r"current-mode:\s*(\S+)", p.read_text(encoding="utf-8"))
            if m:
                return m.group(1)
        return ""

    @cached_property
    def prefix(self) -> str:
        for rid in self.records:
            m = re.match(r"^([A-Z0-9]+)-", rid)
            if m:
                return m.group(1)
        return self.slug.upper()

    def purpose_records(self):
        """目的仮説レコードを (stem, fm, body, history) で列挙する。history はキャッシュ済み。"""
        for stem, (_, fm, body) in self.records.items():
            if "-P-" in stem:
                yield stem, fm, body, self.history[stem]


def check_id_matches_filename(project) -> list:
    """frontmatter id はファイル名と完全一致（接頭辞つき）。規約外ファイル名も報告。"""
    problems = []
    for stem, (path, fm, _) in project.records.items():
        fid = fm.get("id", "")
        if fid != stem:
            problems.append(Problem("error", stem, "id-filename",
                                    f"frontmatter id '{fid}' がファイル名 '{stem}' と一致しない"))
    for p in project.stray:
        problems.append(Problem("warning", str(p), "id-filename",
                                "レコード名が ID 規約（<PREFIX>-P/C/ACT/REF/DEC-NNN）に合わない"))
    return problems


def check_vocabulary(project) -> list:
    """status・type・confidence の語彙/範囲を規約に照らして検証する。

    - P: status・confidence（1-10 整数）を検証。type は持たない。
    - C/ACT/DEC: type がそのエンティティのサブタイプ enum に含まれること。
    - REF: type/confidence を持たない（内省は確信度なし）。"""
    problems = []
    for stem, (_, fm, _) in project.records.items():
        ent = entity_of(stem)
        if ent == "P":
            if fm.get("status") not in STATUSES:
                problems.append(Problem("error", stem, "vocab", f"status '{fm.get('status')}' は規約外"))
            c = fm.get("confidence", "")
            if not (c.isdigit() and CONFIDENCE_MIN <= int(c) <= CONFIDENCE_MAX):
                problems.append(Problem("error", stem, "vocab",
                    f"confidence '{c}' は {CONFIDENCE_MIN}-{CONFIDENCE_MAX} の整数でない"))
        elif ent in ("C", "ACT", "DEC"):
            enum = TYPES_BY_ENTITY[ent]
            if fm.get("type") not in enum:
                problems.append(Problem("error", stem, "vocab", f"type '{fm.get('type')}' は規約外"))
    return problems


EVIDENCE_RE = re.compile(r"\[\[([A-Z0-9]+-(?:ACT|DEC)-\d+)\]\]")


def check_history_consistency(project) -> list:
    """不変ルール2: frontmatter の confidence/status は確信度履歴テーブルの最終行と一致する。"""
    problems = []
    for stem, fm, _, rows in project.purpose_records():
        if not rows:
            problems.append(Problem("error", stem, "history", "確信度履歴テーブルが無い/パースできない"))
            continue
        last = rows[-1]
        if last["confidence"] != fm.get("confidence"):
            problems.append(Problem("error", stem, "history",
                f"frontmatter confidence={fm.get('confidence')} と履歴最終行 {last['confidence']} が不一致"))
        if last["status"] != fm.get("status"):
            problems.append(Problem("error", stem, "history",
                f"frontmatter status={fm.get('status')} と履歴最終行 {last['status']} が不一致"))
    return problems


def check_evidence_links(project) -> list:
    """不変ルール1: 初期行以降の確信度・ステータス変更は必ず実在する ACT/DEC に紐づく。"""
    problems = []
    for stem, _, _, rows in project.purpose_records():
        for i, row in enumerate(rows):
            if i == 0:
                continue  # 初期作成行のみ根拠レコード免除
            ids = EVIDENCE_RE.findall(row["activity"])
            if not ids:
                problems.append(Problem("error", stem, "evidence",
                    f"履歴 {row['date']} 行（確信度{row['confidence']}）に [[ACT/DEC]] の証拠リンクが無い"))
            for rid in ids:
                if rid not in project.records:
                    problems.append(Problem("error", stem, "evidence",
                        f"履歴の証拠 [[{rid}]] のレコードが存在しない"))
    return problems


def _row_max_rank(reason: str):
    """根拠セルに現れる階梯タグの最強順位を返す（階梯タグが無ければ None）。"""
    ranks = [EVIDENCE_RANK[name] for name in EVIDENCE_RANK if f"〈{name}〉" in reason]
    return max(ranks) if ranks else None


def check_evidence_asymmetry(project) -> list:
    """証拠の非対称性: 確信度を**上げた**履歴行は、外界に触れた証拠（〈試行〉以上）を要する。

    〈壁打ち〉（エージェントとの対話のみ）は外界に触れていないので、単体では確信度を上げられない。
    確信度が前行より増えた行で、根拠タグの最強が〈壁打ち〉止まり、または外界タグが1つも無いとき error。
    （下降・据え置きは対象外。壁打ちで目的文を磨くのは自由。上げるときだけ外界の証拠を要求する。）"""
    problems = []
    for stem, _, _, rows in project.purpose_records():
        prev = None
        for i, row in enumerate(rows):
            cur = int(row["confidence"]) if row["confidence"].isdigit() else None
            if i > 0 and cur is not None and prev is not None and cur > prev:
                rank = _row_max_rank(row["reason"])
                if rank is None or rank < EXTERNAL_RANK_MIN:
                    have = f"〈{EVIDENCE_LADDER[rank]}〉止まり" if rank is not None else "外界の証拠タグ無し"
                    problems.append(Problem("error", stem, "evidence-asymmetry",
                        f"履歴 {row['date']} 行で確信度を {prev}→{cur} に上げているが、外界に触れた証拠"
                        f"（〈試行〉〈他者反応〉〈継続〉）が無い（{have}）。壁打ち単体では確信度を上げない"))
            if cur is not None:
                prev = cur
    return problems


WIKILINK_RE = re.compile(r"\[\[([^\]|#]+)(?:[|#][^\]]*)?\]\]")


def check_frontmatter_refs(project) -> list:
    """frontmatter の関係リンクを ontology.yaml の宣言で検証する。

    各関係（derived-from / leads-to / grounded-in / revises / purposes / reflects-on / based-on）
    について、その関係の domain 種別を持つレコードの frontmatter 参照を、接頭辞つき・実在・
    range 種別・（サブタイプ制約があればサブタイプ）・（単一関係の）cardinality で検証する。
    """
    problems = []
    prefix = project.prefix
    for stem, (_, fm, _) in project.records.items():
        ent = entity_of(stem)
        for rel in RELATIONS:
            if rel.domain != ent:
                continue
            ids = parse_id_array(fm.get(rel.field, ""))
            if not ids:
                continue
            # domain サブタイプ制約（今の関係群には無いが、将来のため残す）
            if rel.domain_subtypes and fm.get("type") not in rel.domain_subtypes:
                problems.append(Problem("error", stem, "refs",
                    f"frontmatter {rel.field} は {'・'.join(sorted(rel.domain_subtypes))} だけが持てる"
                    f"（このレコードは '{fm.get('type')}'）"))
            # cardinality（単一関係に複数）
            if rel.is_single and len(ids) > 1:
                problems.append(Problem("error", stem, "refs",
                    f"frontmatter {rel.field} は単一参照（cardinality one）だが {len(ids)} 件ある"))
            for rid in ids:
                if not rid.startswith(prefix + "-"):
                    problems.append(Problem("error", stem, "refs",
                        f"frontmatter {rel.field} '{rid}' が接頭辞つきでない（{prefix}-… に統一する）"))
                    continue
                if rid not in project.records:
                    problems.append(Problem("error", stem, "refs",
                        f"frontmatter {rel.field} '{rid}' のレコードが存在しない"))
                    continue
                # range 種別（例: purposes は P を、based-on は ACT を指す）
                target_fm = project.records[rid][1]
                if entity_of(rid) != rel.range:
                    problems.append(Problem("error", stem, "refs",
                        f"frontmatter {rel.field} '{rid}' は {rel.range} を指すべき"
                        f"（{entity_of(rid)} を指している）"))
                elif rel.range_subtypes and target_fm.get("type") not in rel.range_subtypes:
                    problems.append(Problem("error", stem, "refs",
                        f"frontmatter {rel.field} '{rid}' は {'・'.join(sorted(rel.range_subtypes))} を指すべき"
                        f"（'{target_fm.get('type')}' を指している）"))
    return problems


def check_relation_wikilinks(project) -> list:
    """二重表現規約: must-wikilink な関係は frontmatter 参照が本文 wikilink にも現れる（warning）。"""
    problems = []
    prefix = project.prefix
    for stem, (_, fm, body) in project.records.items():
        ent = entity_of(stem)
        body_links = {t.strip() for t in WIKILINK_RE.findall(strip_comments(strip_frontmatter(body)))}
        for rel in RELATIONS:
            if rel.domain != ent or not rel.must_wikilink:
                continue
            for rid in parse_id_array(fm.get(rel.field, "")):
                if rid.startswith(prefix + "-") and rid in project.records and rid not in body_links:
                    problems.append(Problem("warning", stem, "relation-wikilink",
                        f"frontmatter {rel.field}（{rel.label}）'{rid}' が本文 wikilink [[{rid}]] に無い"
                        f"（二重表現規約: Obsidian グラフに辺を出すため本文にも張る）"))
    return problems


def check_wikilinks(project) -> list:
    """本文の wikilink が vault 内で解決すること。schema層（/入り）への wikilink は規約違反。"""
    problems = []
    all_names = {p.stem for p in project.root.parent.glob("*/wiki/**/*.md")}
    for stem, (_, _, body) in project.records.items():
        for target in WIKILINK_RE.findall(strip_comments(strip_frontmatter(body))):
            target = target.strip()
            if "/" in target:
                problems.append(Problem("error", stem, "wikilink",
                    f"[[{target}]] — schema層への参照は wikilink でなく相対mdリンクで書く規約"))
            elif target not in all_names:
                problems.append(Problem("error", stem, "wikilink", f"[[{target}]] が解決しない（リンク切れ）"))
    return problems


INDEX_ROW_RE = re.compile(r"^\|\s*\[\[([A-Z0-9]+-P-\d+)\]\]\s*\|[^|]*\|\s*(\d+)\s*\|\s*([^|]+?)\s*\|")


def check_id_sequence(project) -> list:
    """不変ルール5: ID 重複禁止。欠番は log.md の取り下げ記録があれば正常、なければ warning。"""
    problems = []
    prefix = project.prefix
    seen = {}
    for stem, (_, fm, _) in project.records.items():
        fid = fm.get("id", stem)
        if fid in seen:
            problems.append(Problem("error", stem, "id-seq", f"id '{fid}' が {seen[fid]} と重複"))
        seen[fid] = stem
    log_lines = project.log.splitlines()
    for kind in ENTITY_INFIXES:
        pat = re.compile(rf"^{re.escape(prefix)}-{kind}-(\d+)$")
        nums = sorted(int(m.group(1)) for rid in project.records if (m := pat.match(rid)))
        if not nums:
            continue
        for missing in sorted(set(range(1, max(nums) + 1)) - set(nums)):
            mid = f"{prefix}-{kind}-{missing:03d}"
            if not any(mid in line and "取り下げ" in line for line in log_lines):
                problems.append(Problem("warning", mid, "id-seq",
                                        "欠番だが log.md に取り下げ記録が見当たらない"))
    return problems


def check_log_sync(project) -> list:
    """不変ルール2: 履歴テーブルへの追記（2行目以降）は log.md にも記録される。"""
    problems = []
    log_lines = project.log.splitlines()
    for stem, _, _, rows in project.purpose_records():
        m = re.search(r"(P-\d+)$", stem)
        short = m.group(1) if m else stem
        for row in rows[1:]:
            conf = row["confidence"]
            pattern = rf"(?:→\s*|確信度[^|]*?){re.escape(conf)}(?!\d)"
            if not any((stem in line or short in line) and re.search(pattern, line)
                       for line in log_lines):
                problems.append(Problem("warning", stem, "log-sync",
                    f"履歴 {row['date']} 行（確信度{conf}）に対応する log.md 記録が見当たらない"))
    return problems


def check_index_sync(project) -> list:
    """index.md の確信度・ステータスがレコード本体と一致する（lint 項目5の機械部分）。"""
    problems = []
    index_path = project.wiki / "index.md"
    if not index_path.exists():
        return [Problem("warning", "index.md", "index-sync", "index.md が無い")]
    for line in index_path.read_text(encoding="utf-8").splitlines():
        m = INDEX_ROW_RE.match(line.strip())
        if not m:
            continue
        rid, conf, status = m.group(1), m.group(2), m.group(3)
        if rid not in project.records:
            problems.append(Problem("error", "index.md", "index-sync", f"[[{rid}]] のレコードが存在しない"))
            continue
        fm = project.records[rid][1]
        if fm.get("confidence") != conf or fm.get("status") != status:
            problems.append(Problem("error", "index.md", "index-sync",
                f"[[{rid}]] index表（確信度{conf}/{status}）とレコード"
                f"（確信度{fm.get('confidence')}/{fm.get('status')}）が不一致"))
    return problems


def check_fictional_cap(project) -> list:
    """架空/脳内シミュレーション由来の確信度は上限 FICTIONAL_CAP（それ超は実観測に限る）。

    履歴の**全行**を走査する。行の根拠が架空と判定されるのは、(a) 紐づく ACT が架空マーカーを含む、
    (b) 根拠セルに 〈架空〉タグ、(c) 根拠セルに架空マーカー、のいずれか。"""
    problems = []
    fictional_acts = {stem for stem, (_, _, body) in project.records.items()
                      if "-ACT-" in stem and any(m in body for m in FICTIONAL_MARKERS)}
    for stem, _, _, rows in project.purpose_records():
        for row in rows:
            rc = row["confidence"]
            if not rc.isdigit() or int(rc) <= FICTIONAL_CAP:
                continue
            hit = [rid for rid in EVIDENCE_RE.findall(row["activity"]) if rid in fictional_acts]
            tagged = "〈架空〉" in row["reason"] or any(m in row["reason"] for m in FICTIONAL_MARKERS)
            if hit or tagged:
                src = "・".join(hit) if hit else "〈架空〉タグ"
                problems.append(Problem("error", stem, "fictional-cap",
                    f"履歴 {row['date']} 行 confidence={rc} だが根拠が架空/シミュレーション"
                    f"（{src}）。上限{FICTIONAL_CAP}"))
    return problems


def check_evidence_tags(project) -> list:
    """証拠の階梯: 履歴2行目以降の根拠セルには証拠種別タグを付ける（新規約のため warning 運用）。"""
    problems = []
    for stem, _, _, rows in project.purpose_records():
        for row in rows[1:]:
            if not any(tag in row["reason"] for tag in EVIDENCE_TAGS):
                problems.append(Problem("warning", stem, "evidence-tag",
                    f"履歴 {row['date']} 行の根拠に証拠種別タグ（〈試行〉〈他者反応〉等）が無い"))
    return problems


def check_status_confidence(project) -> list:
    """status × confidence の矛盾検出（2軸の食い違い）。ontology.yaml の status-bounds に照らす。"""
    problems = []
    for stem, fm, _, _ in project.purpose_records():
        status, c = fm.get("status"), fm.get("confidence", "")
        if not c.isdigit() or status not in STATUS_BOUNDS:
            continue
        conf, b = int(c), STATUS_BOUNDS[status]
        if "min" in b and conf < b["min"]:
            problems.append(Problem("warning", stem, "status-confidence",
                f"status={status} なのに confidence={conf}（{b['min']} 以上が自然）"))
        if "max" in b and conf > b["max"]:
            problems.append(Problem("warning", stem, "status-confidence",
                f"status={status} なのに confidence={conf}（{b['max']} 以下が自然）"))
    return problems


def _floor_for(conf: int):
    """確信度 conf に要求される証拠の階梯の最低段名を返す（無ければ None）。"""
    for min_conf, name in EVIDENCE_FLOOR:   # min-confidence の降順
        if conf >= min_conf:
            return name
    return None


def check_evidence_floor(project) -> list:
    """確信度の帯に対して証拠の階梯が弱すぎないか（例: confidence 7 を〈壁打ち〉だけで支えていないか）。

    根拠タグに階梯タグが1つも無い場合は evidence-tag の担当なので二重報告しない。
    階梯タグが在るのにその最強が要求段未満のときだけ warning にする。"""
    problems = []
    for stem, fm, _, rows in project.purpose_records():
        c = fm.get("confidence", "")
        if not c.isdigit():
            continue
        floor = _floor_for(int(c))
        if floor is None:
            continue
        ranks = [EVIDENCE_RANK[name] for name in EVIDENCE_RANK
                 for row in rows if f"〈{name}〉" in row["reason"]]
        if not ranks:
            continue
        if max(ranks) < EVIDENCE_RANK[floor]:
            problems.append(Problem("warning", stem, "evidence-floor",
                f"confidence={c} には〈{floor}〉以上の証拠が要るが、根拠タグの最強は"
                f"〈{EVIDENCE_LADDER[max(ranks)]}〉止まり（証拠の階梯に対し確信度が高い）"))
    return problems


def check_dec_based_on(project) -> list:
    """DEC は根拠となる活動（based-on）に紐づく。根拠なき意思決定を検出する（warning）。"""
    problems = []
    for stem, (_, fm, _) in project.records.items():
        if "-DEC-" not in stem:
            continue
        if not parse_id_array(fm.get("based-on", "")):
            problems.append(Problem("warning", stem, "dec-based-on",
                "DEC に based-on（根拠活動）が無い（意思決定は活動 [[ACT-NNN]] に紐づける）"))
    return problems


UNTESTED_CONFIDENCE = 5   # この確信度以上で検証活動ゼロなら「外界に殴られていない高確信」


def check_untested_focus(project) -> list:
    """OI-F1: 確信度が高い（>=UNTESTED_CONFIDENCE）のに検証活動(ACT)の purposes 入次数が0の目的仮説を
    検出する（warning）。外界に一度も殴られていない高確信＝偽の収束の兆候。トポロジー由来の探索域ギャップ。"""
    problems = []
    tested = referenced_ids(project, "purposes", infix="-ACT-")
    for stem, fm, _, _ in project.purpose_records():
        c = fm.get("confidence", "")
        if not c.isdigit() or int(c) < UNTESTED_CONFIDENCE or stem in tested:
            continue
        problems.append(Problem("warning", stem, "untested-focus",
            f"確信度{c} なのに検証活動(ACT)が1本も紐づいていない"
            "（外界に触れていない高確信＝偽の収束の疑い。/reflect で試行を紐づけるか ゆさぶり で引き下げる）"))
    return problems


def check_grounding_gaps(project) -> list:
    """OI-F2 相当: 確信度が高い（>=UNTESTED_CONFIDENCE）のに grounded-in（手中の鳥＝制約C）が空の
    目的仮説を検出する（warning）。制約に接地していない目的＝地に足がついていない可能性。"""
    problems = []
    for stem, fm, _, _ in project.purpose_records():
        c = fm.get("confidence", "")
        if not c.isdigit() or int(c) < UNTESTED_CONFIDENCE:
            continue
        if not parse_id_array(fm.get("grounded-in", "")):
            problems.append(Problem("warning", stem, "grounding-gap",
                f"確信度{c} なのに grounded-in（接地する制約C）が空"
                "（手中の鳥に根ざしていない目的。/hand で制約を数え grounded-in で結線する）"))
    return problems


def check_relation_cycles(project) -> list:
    """P→P 関係（derived-from / leads-to / revises）の自己参照・循環を検出する（error）。"""
    problems = []
    for rel in RELATIONS:
        if not (rel.domain == "P" and rel.range == "P"):
            continue
        graph = {}
        for stem, (_, fm, _) in project.records.items():
            if entity_of(stem) != "P":
                continue
            graph[stem] = [r for r in parse_id_array(fm.get(rel.field, "")) if r in project.records]
        for node, outs in graph.items():
            if node in outs:
                problems.append(Problem("error", node, "relation-cycle",
                    f"{rel.field}（{rel.label}）が自己参照している"))
        # DFS で閉路検出（自己参照は上で報告済みなので除く）
        WHITE, GRAY, BLACK = 0, 1, 2
        color = {n: WHITE for n in graph}
        reported = set()

        def visit(n, path):
            color[n] = GRAY
            for m in graph.get(n, []):
                if m == n:
                    continue
                if color.get(m) == GRAY and m in path:
                    cyc = path[path.index(m):] + [m]
                    key = frozenset(cyc)
                    if key not in reported:
                        reported.add(key)
                        problems.append(Problem("error", n, "relation-cycle",
                            f"{rel.field}（{rel.label}）に循環: {' → '.join(cyc)}"))
                elif color.get(m) == WHITE:
                    visit(m, path + [m])
            color[n] = BLACK

        for n in graph:
            if color[n] == WHITE:
                visit(n, [n])
    return problems


CHECKS = [check_id_matches_filename, check_vocabulary, check_history_consistency, check_evidence_links,
          check_evidence_asymmetry, check_frontmatter_refs, check_wikilinks, check_relation_wikilinks,
          check_id_sequence, check_log_sync, check_index_sync, check_fictional_cap,
          check_evidence_tags, check_status_confidence, check_evidence_floor,
          check_dec_based_on, check_untested_focus, check_grounding_gaps,
          check_relation_cycles]


def lint_project(root: Path) -> list:
    project = Project(root)
    problems = []
    for check in CHECKS:
        problems.extend(check(project))
    return problems


def resolve_targets(repo: Path, args) -> list:
    projects_dir = repo / "projects"
    if args.all:
        return [d for d in sorted(projects_dir.iterdir()) if (d / "wiki").is_dir()]
    slug = args.project
    if not slug:
        current = (projects_dir / "current.md").read_text(encoding="utf-8")
        m = re.search(r"current-project:\s*(\S+)", current)
        slug = m.group(1) if m else None
    if not slug or not (projects_dir / slug / "wiki").is_dir():
        sys.exit(f"プロジェクトが見つからない: {slug!r}")
    return [projects_dir / slug]


def main() -> int:
    ap = argparse.ArgumentParser(description="キャリア目的形成Wiki の決定論的 lint")
    ap.add_argument("--project", help="対象案件 slug（省略時は projects/current.md の current-project）")
    ap.add_argument("--all", action="store_true", help="全案件を対象にする")
    ap.add_argument("--repo", default=".", help="リポジトリルート")
    args = ap.parse_args()
    repo = Path(args.repo).resolve()
    exit_code = 0
    for root in resolve_targets(repo, args):
        problems = lint_project(root)
        errors = [p for p in problems if p.level == "error"]
        warnings = [p for p in problems if p.level == "warning"]
        print(f"== {root.name}: error {len(errors)} / warning {len(warnings)}")
        for p in problems:
            print(f"  [{p.level}] {p.check} | {p.where} | {p.message}")
        if errors:
            exit_code = 1
    return exit_code


if __name__ == "__main__":
    sys.exit(main())
