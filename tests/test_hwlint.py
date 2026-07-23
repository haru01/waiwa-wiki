import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

TOOLS = Path(__file__).resolve().parent.parent / "tools"
sys.path.insert(0, str(TOOLS))
import hwlint  # noqa: E402
import ontology  # noqa: E402


def write(root: Path, rel: str, text: str):
    p = root / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(text, encoding="utf-8")


def make_project(tmp: str, files: dict) -> Path:
    root = Path(tmp) / "projects" / "demo"
    if "wiki/log.md" not in files:
        write(root, "wiki/log.md", "")
    for rel, text in files.items():
        write(root, rel, text)
    return root


def purpose(id="DEMO-P-001", status="未検証", confidence="1", rows=None, extra="", body_extra=""):
    """目的仮説(P)レコード。extra=frontmatter 追加行、body_extra=本文末尾追加。"""
    rows_text = "\n".join(rows or ["| 2026-07-01 | 1 | 未検証 | 初期作成 | — |"])
    extra_line = (extra + "\n") if extra else ""
    return f"""---
id: {id}
title: テスト目的
status: {status}
confidence: {confidence}
{extra_line}---

# テスト目的

## 目的仮説文（反証可能な形式で）

> テスト。

## 確信度履歴

| 日付 | 確信度 | ステータス | 根拠 | 活動 |
|---|---|---|---|---|
{rows_text}
{body_extra}
"""


def constraint(id="DEMO-C-001", type="自分は誰か", body="価値観の記述。"):
    return f"""---
id: {id}
title: テスト制約
type: {type}
---

# テスト制約

{body}
"""


def act(id="DEMO-ACT-001", type="面談", purposes="[DEMO-P-001]", body="対象目的: [[DEMO-P-001]]"):
    return f"""---
id: {id}
title: テスト試行
type: {type}
date: 2026-07-01
purposes: {purposes}
---

# テスト試行

{body}
"""


def ref(id="DEMO-REF-001", reflects_on="[DEMO-P-001]", body="内省対象: [[DEMO-P-001]]"):
    return f"""---
id: {id}
title: テスト内省
reflects-on: {reflects_on}
---

# テスト内省

### 事実

観測した。

{body}
"""


def dec(id="DEMO-DEC-001", type="ピボット", based_on="[DEMO-ACT-001]", body="根拠: [[DEMO-ACT-001]]",
        extra=""):
    extra_line = (extra + "\n") if extra else ""
    return f"""---
id: {id}
title: テスト決定
date: 2026-07-02
type: {type}
based-on: {based_on}
{extra_line}---

# テスト決定

{body}
"""


def only(root, check):
    return [p for p in hwlint.lint_project(root) if p.check == check]


class IdFilenameTest(unittest.TestCase):
    def test_mismatch_detected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = make_project(tmp, {"wiki/purposes/DEMO-P-001.md": purpose(id="P-001")})
            self.assertTrue(only(root, "id-filename"))

    def test_match_ok(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = make_project(tmp, {"wiki/purposes/DEMO-P-001.md": purpose()})
            self.assertEqual(only(root, "id-filename"), [])


class VocabularyTest(unittest.TestCase):
    def test_bad_status_and_confidence_detected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = make_project(tmp, {"wiki/purposes/DEMO-P-001.md": purpose(status="確認中", confidence="11")})
            self.assertGreaterEqual(len(only(root, "vocab")), 2)

    def test_bad_constraint_type_detected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = make_project(tmp, {"wiki/constraints/DEMO-C-001.md": constraint(type="謎の型")})
            self.assertTrue(only(root, "vocab"))

    def test_bad_act_type_detected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = make_project(tmp, {"wiki/activities/DEMO-ACT-001.md": act(type="interview")})
            self.assertTrue(only(root, "vocab"))

    def test_valid_records_ok(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = make_project(tmp, {
                "wiki/purposes/DEMO-P-001.md": purpose(),
                "wiki/constraints/DEMO-C-001.md": constraint(),
                "wiki/activities/DEMO-ACT-001.md": act(),
                "wiki/reflections/DEMO-REF-001.md": ref(),
            })
            self.assertEqual(only(root, "vocab"), [])


class HistoryConsistencyTest(unittest.TestCase):
    def test_mismatch_detected(self):
        rows = ["| 2026-07-01 | 1 | 未検証 | 初期作成 | — |",
                "| 2026-07-05 | 5 | 探索中 | 〈試行〉手応え | [[DEMO-ACT-001]] |"]
        with tempfile.TemporaryDirectory() as tmp:
            root = make_project(tmp, {
                "wiki/purposes/DEMO-P-001.md": purpose(status="未検証", confidence="1", rows=rows),
                "wiki/activities/DEMO-ACT-001.md": act(),
            })
            self.assertTrue(only(root, "history"))


class EvidenceLinkTest(unittest.TestCase):
    def test_change_without_evidence_detected(self):
        rows = ["| 2026-07-01 | 1 | 未検証 | 初期作成 | — |",
                "| 2026-07-05 | 5 | 探索中 | 〈試行〉手応え | — |"]
        with tempfile.TemporaryDirectory() as tmp:
            root = make_project(tmp, {
                "wiki/purposes/DEMO-P-001.md": purpose(status="探索中", confidence="5", rows=rows)})
            self.assertTrue(only(root, "evidence"))

    def test_change_with_existing_evidence_ok(self):
        rows = ["| 2026-07-01 | 1 | 未検証 | 初期作成 | — |",
                "| 2026-07-05 | 5 | 探索中 | 〈試行〉 | [[DEMO-ACT-001]] |"]
        with tempfile.TemporaryDirectory() as tmp:
            root = make_project(tmp, {
                "wiki/purposes/DEMO-P-001.md": purpose(status="探索中", confidence="5", rows=rows),
                "wiki/activities/DEMO-ACT-001.md": act(),
            })
            self.assertEqual(only(root, "evidence"), [])


class EvidenceAsymmetryTest(unittest.TestCase):
    """証拠の非対称性: 壁打ち(dialogue)単体では確信度を上げられない。"""

    def _rows(self, tag):
        return ["| 2026-07-01 | 1 | 未検証 | 初期作成 | — |",
                f"| 2026-07-05 | 5 | 探索中 | {tag}手応え | [[DEMO-ACT-001]] |"]

    def _proj(self, tmp, tag):
        return make_project(tmp, {
            "wiki/purposes/DEMO-P-001.md": purpose(status="探索中", confidence="5", rows=self._rows(tag)),
            "wiki/activities/DEMO-ACT-001.md": act(),
        })

    def test_dialogue_only_increase_blocked(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.assertTrue(only(self._proj(tmp, "〈壁打ち〉"), "evidence-asymmetry"))

    def test_no_tag_increase_blocked(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.assertTrue(only(self._proj(tmp, ""), "evidence-asymmetry"))

    def test_trial_increase_ok(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.assertEqual(only(self._proj(tmp, "〈試行〉"), "evidence-asymmetry"), [])

    def test_third_party_increase_ok(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.assertEqual(only(self._proj(tmp, "〈他者反応〉"), "evidence-asymmetry"), [])

    def test_decrease_with_dialogue_ok(self):
        # 下降は非対称ルールの対象外（壁打ちでの引き下げは許される）
        rows = ["| 2026-07-01 | 5 | 探索中 | 〈試行〉 | [[DEMO-ACT-001]] |",
                "| 2026-07-05 | 3 | 探索中 | 〈壁打ち〉再考して引き下げ | [[DEMO-ACT-001]] |"]
        with tempfile.TemporaryDirectory() as tmp:
            root = make_project(tmp, {
                "wiki/purposes/DEMO-P-001.md": purpose(status="探索中", confidence="3", rows=rows),
                "wiki/activities/DEMO-ACT-001.md": act(),
            })
            self.assertEqual(only(root, "evidence-asymmetry"), [])


class RefsTest(unittest.TestCase):
    def test_unprefixed_ref_detected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = make_project(tmp, {
                "wiki/purposes/DEMO-P-001.md": purpose(),
                "wiki/activities/DEMO-ACT-001.md": act(purposes="[P-001]"),
            })
            self.assertTrue(only(root, "refs"))

    def test_purposes_range_violation_points_to_constraint(self):
        # purposes は P を指すべき（C を指したら違反）
        with tempfile.TemporaryDirectory() as tmp:
            root = make_project(tmp, {
                "wiki/constraints/DEMO-C-001.md": constraint(),
                "wiki/activities/DEMO-ACT-001.md": act(purposes="[DEMO-C-001]",
                                                       body="対象目的: [[DEMO-C-001]]"),
            })
            self.assertTrue(any("P を指すべき" in p.message for p in only(root, "refs")))

    def test_grounded_in_range_violation_points_to_purpose(self):
        # grounded-in は C を指すべき（P を指したら違反）
        rec = purpose(id="DEMO-P-002", extra="grounded-in: [DEMO-P-001]",
                      body_extra="接地する制約: [[DEMO-P-001]]")
        with tempfile.TemporaryDirectory() as tmp:
            root = make_project(tmp, {
                "wiki/purposes/DEMO-P-001.md": purpose(),
                "wiki/purposes/DEMO-P-002.md": rec,
            })
            self.assertTrue(any("C を指すべき" in p.message for p in only(root, "refs")))

    def test_based_on_range_violation_points_to_purpose(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = make_project(tmp, {
                "wiki/purposes/DEMO-P-001.md": purpose(),
                "wiki/decisions/DEMO-DEC-001.md": dec(based_on="[DEMO-P-001]",
                                                      body="根拠: [[DEMO-P-001]]"),
            })
            self.assertTrue(any("ACT を指すべき" in p.message for p in only(root, "refs")))

    def test_cardinality_violation_derived_from_multiple(self):
        rec = purpose(id="DEMO-P-003", extra="derived-from: [DEMO-P-001, DEMO-P-002]")
        with tempfile.TemporaryDirectory() as tmp:
            root = make_project(tmp, {
                "wiki/purposes/DEMO-P-001.md": purpose(),
                "wiki/purposes/DEMO-P-002.md": purpose(id="DEMO-P-002"),
                "wiki/purposes/DEMO-P-003.md": rec,
            })
            self.assertTrue(any("単一参照" in p.message for p in only(root, "refs")))

    def test_valid_grounded_in_ok(self):
        rec = purpose(id="DEMO-P-002", extra="grounded-in: [DEMO-C-001]",
                      body_extra="接地する制約: [[DEMO-C-001]]")
        with tempfile.TemporaryDirectory() as tmp:
            root = make_project(tmp, {
                "wiki/constraints/DEMO-C-001.md": constraint(),
                "wiki/purposes/DEMO-P-002.md": rec,
            })
            self.assertEqual(only(root, "refs"), [])

    def test_reflects_on_valid_ok(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = make_project(tmp, {
                "wiki/purposes/DEMO-P-001.md": purpose(),
                "wiki/reflections/DEMO-REF-001.md": ref(),
            })
            self.assertEqual(only(root, "refs"), [])


class WikilinkTest(unittest.TestCase):
    def test_broken_wikilink_detected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = make_project(tmp, {
                "wiki/purposes/DEMO-P-001.md": purpose(),
                "wiki/activities/DEMO-ACT-001.md": act(body="対象目的: [[DEMO-P-404]]"),
            })
            self.assertTrue(any("DEMO-P-404" in p.message for p in only(root, "wikilink")))

    def test_schema_layer_wikilink_detected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = make_project(tmp, {
                "wiki/purposes/DEMO-P-001.md": purpose(),
                "wiki/activities/DEMO-ACT-001.md": act(
                    body="対象目的: [[DEMO-P-001]]\n\n根拠: [[playbooks/formation.md]]"),
            })
            self.assertTrue(any("playbooks" in p.message for p in only(root, "wikilink")))

    def test_comment_wikilink_ignored(self):
        body = purpose(body_extra="\n<!--\n- 活動列に [[ACT-NNN]] を書く。派生元 [[P-NNN]] も例示。\n-->\n")
        with tempfile.TemporaryDirectory() as tmp:
            root = make_project(tmp, {"wiki/purposes/DEMO-P-001.md": body})
            self.assertEqual(only(root, "wikilink"), [])


class IdSequenceTest(unittest.TestCase):
    def test_gap_without_withdrawal_warned(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = make_project(tmp, {
                "wiki/purposes/DEMO-P-001.md": purpose(),
                "wiki/purposes/DEMO-P-003.md": purpose(id="DEMO-P-003"),
            })
            self.assertTrue(any("DEMO-P-002" in p.where for p in only(root, "id-seq")))

    def test_gap_with_withdrawal_ok(self):
        log = "## [2026-07-02] purpose | DEMO-P-002 取り下げ（ユーザー判断） → レコード削除\n"
        with tempfile.TemporaryDirectory() as tmp:
            root = make_project(tmp, {
                "wiki/purposes/DEMO-P-001.md": purpose(),
                "wiki/purposes/DEMO-P-003.md": purpose(id="DEMO-P-003"),
                "wiki/log.md": log,
            })
            self.assertEqual(only(root, "id-seq"), [])


class LogSyncTest(unittest.TestCase):
    def test_change_missing_in_log_warned(self):
        rows = ["| 2026-07-01 | 1 | 未検証 | 初期作成 | — |",
                "| 2026-07-05 | 5 | 探索中 | 〈試行〉 | [[DEMO-ACT-001]] |"]
        with tempfile.TemporaryDirectory() as tmp:
            root = make_project(tmp, {
                "wiki/purposes/DEMO-P-001.md": purpose(status="探索中", confidence="5", rows=rows),
                "wiki/activities/DEMO-ACT-001.md": act(),
            })
            self.assertTrue(only(root, "log-sync"))

    def test_change_recorded_in_log_ok(self):
        rows = ["| 2026-07-01 | 1 | 未検証 | 初期作成 | — |",
                "| 2026-07-05 | 5 | 探索中 | 〈試行〉 | [[DEMO-ACT-001]] |"]
        log = "## [2026-07-05] やってみる | DEMO-ACT-001 実施 → DEMO-P-001 確信度1→5/探索中\n"
        with tempfile.TemporaryDirectory() as tmp:
            root = make_project(tmp, {
                "wiki/purposes/DEMO-P-001.md": purpose(status="探索中", confidence="5", rows=rows),
                "wiki/activities/DEMO-ACT-001.md": act(),
                "wiki/log.md": log,
            })
            self.assertEqual(only(root, "log-sync"), [])


class IndexSyncTest(unittest.TestCase):
    def test_index_mismatch_detected(self):
        index = ("# 目的カタログ\n\n## 目的仮説\n\n"
                 "| ID | タイトル | 確信度 | ステータス |\n|---|---|---|---|\n"
                 "| [[DEMO-P-001]] | テスト目的 | 9 | 立ち上がった |\n")
        with tempfile.TemporaryDirectory() as tmp:
            root = make_project(tmp, {
                "wiki/purposes/DEMO-P-001.md": purpose(),
                "wiki/index.md": index,
            })
            self.assertTrue(only(root, "index-sync"))


class FictionalCapTest(unittest.TestCase):
    def _project(self, tmp, confidence):
        rows = ["| 2026-07-01 | 1 | 未検証 | 初期作成 | — |",
                f"| 2026-07-05 | {confidence} | 立ち上がった | 〈試行〉 | [[DEMO-ACT-001]] |"]
        return make_project(tmp, {
            "wiki/purposes/DEMO-P-001.md": purpose(status="立ち上がった", confidence=str(confidence), rows=rows),
            "wiki/activities/DEMO-ACT-001.md": act(
                body="対象目的: [[DEMO-P-001]]\n\n> ⚠️ 架空のシミュレーションデータ。実証拠として扱わない。"),
        })

    def test_confidence_9_on_fictional_act_detected(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.assertTrue(only(self._project(tmp, 9), "fictional-cap"))

    def test_confidence_8_on_fictional_act_ok(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.assertEqual(only(self._project(tmp, 8), "fictional-cap"), [])


class EvidenceTagTest(unittest.TestCase):
    def test_untagged_reason_warned(self):
        rows = ["| 2026-07-01 | 1 | 未検証 | 初期作成 | — |",
                "| 2026-07-05 | 3 | 探索中 | 手応えがあった | [[DEMO-ACT-001]] |"]
        with tempfile.TemporaryDirectory() as tmp:
            root = make_project(tmp, {
                "wiki/purposes/DEMO-P-001.md": purpose(status="探索中", confidence="3", rows=rows),
                "wiki/activities/DEMO-ACT-001.md": act(),
            })
            hits = only(root, "evidence-tag")
            self.assertEqual(len(hits), 1)
            self.assertEqual(hits[0].level, "warning")

    def test_tagged_reason_ok(self):
        rows = ["| 2026-07-01 | 1 | 未検証 | 初期作成 | — |",
                "| 2026-07-05 | 3 | 探索中 | 〈壁打ち〉言語化しただけ | [[DEMO-ACT-001]] |"]
        with tempfile.TemporaryDirectory() as tmp:
            root = make_project(tmp, {
                "wiki/purposes/DEMO-P-001.md": purpose(status="探索中", confidence="3", rows=rows),
                "wiki/activities/DEMO-ACT-001.md": act(),
            })
            self.assertEqual(only(root, "evidence-tag"), [])


class StatusConfidenceTest(unittest.TestCase):
    def _one(self, tmp, status, confidence):
        rows = [f"| 2026-07-01 | {confidence} | {status} | 初期作成 | — |"]
        return make_project(tmp, {"wiki/purposes/DEMO-P-001.md":
                                  purpose(status=status, confidence=confidence, rows=rows)})

    def test_shelved_high_confidence_warned(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.assertTrue(only(self._one(tmp, "棚上げ", "8"), "status-confidence"))

    def test_unverified_high_confidence_warned(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.assertTrue(only(self._one(tmp, "未検証", "7"), "status-confidence"))

    def test_launched_low_confidence_warned(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.assertTrue(only(self._one(tmp, "立ち上がった", "3"), "status-confidence"))

    def test_consistent_pairs_ok(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.assertEqual(only(self._one(tmp, "未検証", "3"), "status-confidence"), [])
        with tempfile.TemporaryDirectory() as tmp:
            self.assertEqual(only(self._one(tmp, "探索中", "5"), "status-confidence"), [])  # 探索中は境界なし


class EvidenceFloorTest(unittest.TestCase):
    def _proj(self, tmp, confidence, tag):
        rows = ["| 2026-07-01 | 1 | 未検証 | 初期作成 | — |",
                f"| 2026-07-05 | {confidence} | 探索中 | {tag}手応え | [[DEMO-ACT-001]] |"]
        return make_project(tmp, {
            "wiki/purposes/DEMO-P-001.md": purpose(status="探索中", confidence=str(confidence), rows=rows),
            "wiki/activities/DEMO-ACT-001.md": act(),
        })

    def test_high_confidence_weak_evidence_warned(self):
        with tempfile.TemporaryDirectory() as tmp:   # conf 5 を〈壁打ち〉だけで支える
            self.assertTrue(only(self._proj(tmp, 5, "〈壁打ち〉"), "evidence-floor"))

    def test_high_confidence_strong_evidence_ok(self):
        with tempfile.TemporaryDirectory() as tmp:   # conf 5 を〈試行〉で支える
            self.assertEqual(only(self._proj(tmp, 5, "〈試行〉"), "evidence-floor"), [])


class DecBasedOnTest(unittest.TestCase):
    def test_missing_based_on_warned(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = make_project(tmp, {"wiki/decisions/DEMO-DEC-001.md": dec(based_on="", body="—")})
            self.assertTrue(only(root, "dec-based-on"))

    def test_present_based_on_ok(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = make_project(tmp, {
                "wiki/decisions/DEMO-DEC-001.md": dec(),
                "wiki/activities/DEMO-ACT-001.md": act(),
            })
            self.assertEqual(only(root, "dec-based-on"), [])


class UntestedFocusTest(unittest.TestCase):
    """OI-F1: 確信度が高いのに検証活動(ACT)入次数0（外界に殴られていない高確信）。"""

    def _high(self, id="DEMO-P-001"):
        rows = ["| 2026-07-01 | 1 | 未検証 | 初期作成 | — |",
                "| 2026-07-05 | 6 | 探索中 | 〈試行〉 | [[DEMO-ACT-009]] |"]
        return purpose(id=id, status="探索中", confidence="6", rows=rows)

    def test_high_confidence_without_activity_detected(self):
        # 確信度6 だが purposes で参照する ACT が無い（履歴の ACT-009 は存在しない）
        with tempfile.TemporaryDirectory() as tmp:
            root = make_project(tmp, {"wiki/purposes/DEMO-P-001.md": self._high()})
            self.assertTrue(only(root, "untested-focus"))

    def test_high_confidence_with_activity_ok(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = make_project(tmp, {
                "wiki/purposes/DEMO-P-001.md": self._high(),
                "wiki/activities/DEMO-ACT-001.md": act(),   # purposes:[DEMO-P-001]
            })
            self.assertEqual(only(root, "untested-focus"), [])

    def test_low_confidence_without_activity_ok(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = make_project(tmp, {"wiki/purposes/DEMO-P-001.md": purpose(confidence="2")})
            self.assertEqual(only(root, "untested-focus"), [])


class GroundingGapTest(unittest.TestCase):
    """OI-F2 相当: 確信度が高いのに grounded-in（制約C）が空。"""

    def _high(self, extra=""):
        rows = ["| 2026-07-01 | 1 | 未検証 | 初期作成 | — |",
                "| 2026-07-05 | 6 | 探索中 | 〈試行〉 | [[DEMO-ACT-001]] |"]
        return purpose(status="探索中", confidence="6", rows=rows, extra=extra,
                       body_extra="接地する制約: [[DEMO-C-001]]" if extra else "")

    def test_high_confidence_ungrounded_detected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = make_project(tmp, {
                "wiki/purposes/DEMO-P-001.md": self._high(),
                "wiki/activities/DEMO-ACT-001.md": act(),
            })
            self.assertTrue(only(root, "grounding-gap"))

    def test_high_confidence_grounded_ok(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = make_project(tmp, {
                "wiki/purposes/DEMO-P-001.md": self._high(extra="grounded-in: [DEMO-C-001]"),
                "wiki/constraints/DEMO-C-001.md": constraint(),
                "wiki/activities/DEMO-ACT-001.md": act(),
            })
            self.assertEqual(only(root, "grounding-gap"), [])


class StalenessTest(unittest.TestCase):
    """OI-G1: 立ち上がった目的で確信度履歴の最終更新が古い（>staleness-days）ものを warning。"""

    def _launched(self, last_date):
        # 立ち上がった＝確信度 min 7。最終履歴行の日付を last_date にする。
        rows = ["| 2026-01-01 | 1 | 未検証 | 初期作成 | — |",
                f"| {last_date} | 7 | 立ち上がった | 〈他者反応〉繰り返し起きた | [[DEMO-ACT-001]] |"]
        return purpose(status="立ち上がった", confidence="7", rows=rows)

    def _staleness(self, root, today):
        return [p for p in hwlint.lint_project(root, today=today) if p.check == "staleness"]

    def test_stale_launched_detected(self):
        from datetime import date
        with tempfile.TemporaryDirectory() as tmp:
            root = make_project(tmp, {
                "wiki/purposes/DEMO-P-001.md": self._launched("2026-01-10"),
                "wiki/activities/DEMO-ACT-001.md": act(),
            })
            self.assertTrue(self._staleness(root, date(2026, 12, 31)))   # 約1年経過

    def test_fresh_launched_ok(self):
        from datetime import date
        with tempfile.TemporaryDirectory() as tmp:
            root = make_project(tmp, {
                "wiki/purposes/DEMO-P-001.md": self._launched("2026-12-01"),
                "wiki/activities/DEMO-ACT-001.md": act(),
            })
            self.assertEqual(self._staleness(root, date(2026, 12, 31)), [])   # 30日＜180日

    def test_non_launched_stale_ok(self):
        # 探索中は staleness の対象外（古い日付でも出さない）
        from datetime import date
        rows = ["| 2026-01-01 | 1 | 未検証 | 初期作成 | — |",
                "| 2026-01-10 | 6 | 探索中 | 〈試行〉 | [[DEMO-ACT-001]] |"]
        with tempfile.TemporaryDirectory() as tmp:
            root = make_project(tmp, {
                "wiki/purposes/DEMO-P-001.md": purpose(status="探索中", confidence="6", rows=rows),
                "wiki/activities/DEMO-ACT-001.md": act(),
            })
            self.assertEqual(self._staleness(root, date(2026, 12, 31)), [])

    def test_staleness_is_warning(self):
        from datetime import date
        with tempfile.TemporaryDirectory() as tmp:
            root = make_project(tmp, {
                "wiki/purposes/DEMO-P-001.md": self._launched("2026-01-10"),
                "wiki/activities/DEMO-ACT-001.md": act(),
            })
            hits = self._staleness(root, date(2026, 12, 31))
            self.assertTrue(all(p.level == "warning" for p in hits))


class RelationCycleTest(unittest.TestCase):
    def test_self_reference_detected(self):
        rec = purpose(id="DEMO-P-001", extra="derived-from: DEMO-P-001")
        with tempfile.TemporaryDirectory() as tmp:
            root = make_project(tmp, {"wiki/purposes/DEMO-P-001.md": rec})
            self.assertTrue(only(root, "relation-cycle"))

    def test_cycle_detected(self):
        h1 = purpose(id="DEMO-P-001", extra="leads-to: [DEMO-P-002]", body_extra="因果先: [[DEMO-P-002]]")
        h2 = purpose(id="DEMO-P-002", extra="leads-to: [DEMO-P-001]", body_extra="因果先: [[DEMO-P-001]]")
        with tempfile.TemporaryDirectory() as tmp:
            root = make_project(tmp, {"wiki/purposes/DEMO-P-001.md": h1,
                                      "wiki/purposes/DEMO-P-002.md": h2})
            self.assertTrue(only(root, "relation-cycle"))

    def test_acyclic_ok(self):
        h1 = purpose(id="DEMO-P-001", extra="leads-to: [DEMO-P-002]", body_extra="因果先: [[DEMO-P-002]]")
        h2 = purpose(id="DEMO-P-002")
        with tempfile.TemporaryDirectory() as tmp:
            root = make_project(tmp, {"wiki/purposes/DEMO-P-001.md": h1,
                                      "wiki/purposes/DEMO-P-002.md": h2})
            self.assertEqual(only(root, "relation-cycle"), [])


class AffectsTest(unittest.TestCase):
    """E3: DEC→P（affects）。意思決定が動かした目的仮説。"""

    def test_valid_affects_ok(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = make_project(tmp, {
                "wiki/purposes/DEMO-P-001.md": purpose(),
                "wiki/activities/DEMO-ACT-001.md": act(),
                "wiki/decisions/DEMO-DEC-001.md": dec(extra="affects: [DEMO-P-001]",
                                                      body="根拠: [[DEMO-ACT-001]]\n\n影響した目的: [[DEMO-P-001]]"),
            })
            self.assertEqual(only(root, "refs"), [])

    def test_affects_range_violation_points_to_purpose(self):
        # affects は P を指すべき（ACT を指したら違反）
        with tempfile.TemporaryDirectory() as tmp:
            root = make_project(tmp, {
                "wiki/activities/DEMO-ACT-001.md": act(),
                "wiki/decisions/DEMO-DEC-001.md": dec(extra="affects: [DEMO-ACT-001]",
                                                      body="根拠: [[DEMO-ACT-001]]"),
            })
            self.assertTrue(any("P を指すべき" in p.message for p in only(root, "refs")))


class SupersedesTest(unittest.TestCase):
    """E4: DEC→DEC（supersedes）。旧意思決定の上書き/後継。循環は禁止（acyclic）。"""

    def test_valid_supersedes_ok(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = make_project(tmp, {
                "wiki/purposes/DEMO-P-001.md": purpose(),      # act() の purposes 参照先
                "wiki/activities/DEMO-ACT-001.md": act(),
                "wiki/decisions/DEMO-DEC-001.md": dec(),
                "wiki/decisions/DEMO-DEC-002.md": dec(id="DEMO-DEC-002", extra="supersedes: [DEMO-DEC-001]",
                                                      body="根拠: [[DEMO-ACT-001]]\n\n上書き: [[DEMO-DEC-001]]"),
            })
            self.assertEqual(only(root, "refs"), [])
            self.assertEqual(only(root, "relation-cycle"), [])

    def test_self_reference_detected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = make_project(tmp, {
                "wiki/activities/DEMO-ACT-001.md": act(),
                "wiki/decisions/DEMO-DEC-001.md": dec(extra="supersedes: [DEMO-DEC-001]"),
            })
            self.assertTrue(only(root, "relation-cycle"))

    def test_cycle_detected(self):
        d1 = dec(id="DEMO-DEC-001", extra="supersedes: [DEMO-DEC-002]", body="上書き: [[DEMO-DEC-002]]")
        d2 = dec(id="DEMO-DEC-002", extra="supersedes: [DEMO-DEC-001]", body="上書き: [[DEMO-DEC-001]]")
        with tempfile.TemporaryDirectory() as tmp:
            root = make_project(tmp, {
                "wiki/activities/DEMO-ACT-001.md": act(),
                "wiki/decisions/DEMO-DEC-001.md": d1,
                "wiki/decisions/DEMO-DEC-002.md": d2,
            })
            self.assertTrue(only(root, "relation-cycle"))


class CountersTest(unittest.TestCase):
    """E4: P→P（counters）。対抗目的。自己参照は禁止だが相互対抗 A↔B は許容（acyclic:false）。"""

    def test_valid_counters_ok(self):
        p1 = purpose(id="DEMO-P-001", extra="counters: [DEMO-P-002]", body_extra="対抗: [[DEMO-P-002]]")
        with tempfile.TemporaryDirectory() as tmp:
            root = make_project(tmp, {
                "wiki/purposes/DEMO-P-001.md": p1,
                "wiki/purposes/DEMO-P-002.md": purpose(id="DEMO-P-002"),
            })
            self.assertEqual(only(root, "refs"), [])
            self.assertEqual(only(root, "relation-cycle"), [])

    def test_self_reference_detected(self):
        p1 = purpose(id="DEMO-P-001", extra="counters: [DEMO-P-001]")
        with tempfile.TemporaryDirectory() as tmp:
            root = make_project(tmp, {"wiki/purposes/DEMO-P-001.md": p1})
            self.assertTrue(only(root, "relation-cycle"))

    def test_mutual_counter_allowed(self):
        # A↔B の相互対抗は正当＝循環扱いしない（acyclic:false）
        p1 = purpose(id="DEMO-P-001", extra="counters: [DEMO-P-002]", body_extra="対抗: [[DEMO-P-002]]")
        p2 = purpose(id="DEMO-P-002", extra="counters: [DEMO-P-001]", body_extra="対抗: [[DEMO-P-001]]")
        with tempfile.TemporaryDirectory() as tmp:
            root = make_project(tmp, {"wiki/purposes/DEMO-P-001.md": p1,
                                      "wiki/purposes/DEMO-P-002.md": p2})
            self.assertEqual(only(root, "relation-cycle"), [])


class OntologyLoaderTest(unittest.TestCase):
    def test_selfcheck_passes(self):
        self.assertEqual(ontology._selfcheck(), 0)

    def test_constants_derived_from_yaml(self):
        self.assertEqual(ontology.STATUS_ORDER,
                         ["未検証", "探索中", "立ち上がりつつある", "立ち上がった", "棚上げ"])
        self.assertEqual({r.field for r in ontology.RELATIONS},
                         {"derived-from", "leads-to", "grounded-in", "revises", "counters",
                          "purposes", "reflects-on", "based-on", "affects", "supersedes"})
        self.assertIn("面談", ontology.ACT_TYPES)
        self.assertIn("self-reflection", ontology.ACT_TYPES)
        self.assertIn("自分は誰か", ontology.C_TYPES)
        self.assertEqual(ontology.P_TYPES, set())   # P はサブタイプなし
        for good in ("SELF-P-001", "SELF-C-001", "SELF-ACT-001", "SELF-REF-001", "SELF-DEC-001"):
            self.assertTrue(ontology.ID_RE.match(good), good)
        self.assertFalse(ontology.ID_RE.match("SELF-X-001"))

    def test_hwlint_uses_ontology_values(self):
        self.assertEqual(hwlint.STATUSES, ontology.STATUSES)
        self.assertIs(hwlint.RELATIONS, ontology.RELATIONS)
        self.assertIs(hwlint.EVIDENCE_TAGS, ontology.EVIDENCE_TAGS)
        self.assertIs(hwlint.FICTIONAL_MARKERS, ontology.FICTIONAL_MARKERS)


class OntologyDerivationTest(unittest.TestCase):
    def test_evidence_tags_derived(self):
        expected = tuple(f"〈{t}〉" for t in ontology.EVIDENCE_LADDER + ontology.EVIDENCE_AUX)
        self.assertEqual(ontology.EVIDENCE_TAGS, expected)
        self.assertIn("〈試行〉", ontology.EVIDENCE_TAGS)
        self.assertIn("〈架空〉", ontology.EVIDENCE_TAGS)

    def test_evidence_rank_orders_ladder(self):
        self.assertEqual(ontology.EVIDENCE_RANK["壁打ち"], 0)
        self.assertLess(ontology.EVIDENCE_RANK["壁打ち"], ontology.EVIDENCE_RANK["試行"])
        self.assertLess(ontology.EVIDENCE_RANK["試行"], ontology.EVIDENCE_RANK["他者反応"])
        self.assertLess(ontology.EVIDENCE_RANK["他者反応"], ontology.EVIDENCE_RANK["継続"])
        self.assertEqual(ontology.EXTERNAL_RANK_MIN, 1)

    def test_fictional_markers_from_ontology(self):
        self.assertIn("架空", ontology.FICTIONAL_MARKERS)
        self.assertIn("シミュレーション", ontology.FICTIONAL_MARKERS)


class GuardSourcesTest(unittest.TestCase):
    def _run(self, payload):
        return subprocess.run(
            [sys.executable, str(TOOLS / "hooks" / "guard_sources.py")],
            input=json.dumps(payload), capture_output=True, text=True)

    def test_edit_existing_source_blocked(self):
        with tempfile.TemporaryDirectory() as tmp:
            src = Path(tmp) / "projects" / "demo" / "sources" / "2026-07-01-dialogue.md"
            src.parent.mkdir(parents=True)
            src.write_text("生データ", encoding="utf-8")
            r = self._run({"tool_name": "Edit", "tool_input": {"file_path": str(src)}})
            self.assertEqual(r.returncode, 2)
            self.assertIn("不変層", r.stderr)

    def test_new_source_write_allowed(self):
        with tempfile.TemporaryDirectory() as tmp:
            d = Path(tmp) / "projects" / "demo" / "sources"
            d.mkdir(parents=True)
            r = self._run({"tool_name": "Write", "tool_input": {"file_path": str(d / "new.md")}})
            self.assertEqual(r.returncode, 0, r.stderr)

    def test_wiki_write_allowed(self):
        r = self._run({"tool_name": "Edit",
                       "tool_input": {"file_path": "/x/projects/demo/wiki/purposes/DEMO-P-001.md"}})
        self.assertEqual(r.returncode, 0, r.stderr)


class StopLintTest(unittest.TestCase):
    def _repo(self, tmp, record):
        write(Path(tmp), "projects/current.md", "current-project: demo\n")
        make_project(tmp, {"wiki/purposes/DEMO-P-001.md": record})
        return Path(tmp)

    def _run(self, repo, payload):
        return subprocess.run(
            [sys.executable, str(TOOLS / "hooks" / "stop_lint.py")],
            input=json.dumps(payload), cwd=repo, capture_output=True, text=True)

    def test_clean_project_allows_stop(self):
        with tempfile.TemporaryDirectory() as tmp:
            r = self._run(self._repo(tmp, purpose()), {})
            self.assertEqual(r.returncode, 0, r.stderr)

    def test_error_blocks_stop(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = self._repo(tmp, purpose(id="P-001"))  # id-filename error
            r = self._run(repo, {})
            self.assertEqual(r.returncode, 2)
            self.assertIn("hwlint", r.stderr)

    def test_stop_hook_active_passes_through(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = self._repo(tmp, purpose(id="P-001"))
            r = self._run(repo, {"stop_hook_active": True})
            self.assertEqual(r.returncode, 0, r.stderr)


BASE_ACT_FOR_GIT = """---
id: DEMO-ACT-001
title: テスト試行
type: 面談
date: 2026-07-01
purposes: [DEMO-P-001]
---

# テスト試行

## テストカード（検証前に記入・後から書き換えない）

- **成功基準**: 3名以上が前向きに反応する。

## 学習カード（検証後に記入）

### 事実（observed）

5名に打診し、2名が前向きだった。

### 解釈（inference）

成功基準は未達。
"""


class TestcardImmutableTest(unittest.TestCase):
    def _init_repo(self, repo: Path):
        run = lambda *a: subprocess.run(a, cwd=repo, check=True, capture_output=True, text=True)
        run("git", "init", "-b", "main")
        run("git", "config", "user.email", "t@example.com")
        run("git", "config", "user.name", "t")
        return run

    def _run_checker(self, repo: Path, *argv):
        return subprocess.run(
            [sys.executable, str(TOOLS / "check_testcard_immutable.py"), *argv],
            cwd=repo, capture_output=True, text=True)

    def test_rewrite_after_learning_detected(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            run = self._init_repo(repo)
            write(repo, "projects/demo/wiki/activities/DEMO-ACT-001.md", BASE_ACT_FOR_GIT)
            run("git", "add", "-A"); run("git", "commit", "-m", "base")
            write(repo, "projects/demo/wiki/activities/DEMO-ACT-001.md",
                  BASE_ACT_FOR_GIT.replace("3名以上", "1名以上"))
            run("git", "add", "-A"); run("git", "commit", "-m", "rewrite")
            result = self._run_checker(repo, "--base", "HEAD~1")
            self.assertEqual(result.returncode, 1, result.stdout + result.stderr)

    def test_learning_card_edit_allowed(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            run = self._init_repo(repo)
            write(repo, "projects/demo/wiki/activities/DEMO-ACT-001.md", BASE_ACT_FOR_GIT)
            run("git", "add", "-A"); run("git", "commit", "-m", "base")
            write(repo, "projects/demo/wiki/activities/DEMO-ACT-001.md",
                  BASE_ACT_FOR_GIT + "\n### 次のアクション\n\n- 再検証を計画する。\n")
            run("git", "add", "-A"); run("git", "commit", "-m", "learning update")
            result = self._run_checker(repo, "--base", "HEAD~1")
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


if __name__ == "__main__":
    unittest.main()
