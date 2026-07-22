#!/usr/bin/env python3
"""ontology.yaml から人間可読な ontology.md を生成する（決定論・手編集禁止）。

正本は ontology.yaml。このスクリプトはそれを Markdown の表に射影するだけ。
`python3 tools/gen_ontology_doc.py` で ../ontology.md を上書きする。
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import ontology  # noqa: E402

OUT = Path(__file__).resolve().parent.parent / "ontology.md"


def build() -> str:
    o = ontology.load()
    L = ["<!-- 生成物: gen_ontology_doc.py による ontology.yaml からの機械生成。手編集禁止。",
         "     `python3 tools/gen_ontology_doc.py` で再生成する。正本は ontology.yaml。 -->",
         "",
         "# キャリア目的形成Wiki オントロジー",
         "",
         "レコードの**型**（エンティティ）と、レコード間の**型付きリンク**（関係）、および"
         "形成の**状態機械**を定義する。正本は [ontology.yaml](ontology.yaml)。"
         "ツール（`tools/hwlint.py`・`tools/gen_views.py`）は `tools/ontology.py` 経由でここを読む。",
         ""]

    # エンティティ
    L += ["## エンティティ（レコード種別）", "",
          "| 種別 | 名称 | ディレクトリ | サブタイプ（frontmatter `type`） |",
          "|---|---|---|---|"]
    for key, ent in o["entities"].items():
        subs = "・".join(s["name"] for s in ent["subtypes"]) or "（サブタイプなし）"
        L.append(f"| `{key}` | {ent['label']} | `wiki/{ent['dir']}/` | {subs} |")
    L.append("")

    # 関係
    L += ["## 関係（型付きリンク）", "",
          "各関係は frontmatter 配列と本文 wikilink の**二重表現**を持つ"
          "（`must-wikilink: true` のものは本文にも `[[…]]` を張る＝Obsidian グラフに辺を出すため）。", "",
          "| 関係 | frontmatter | domain → range | cardinality | 逆方向(inverse) | 本文wikilink | 意味 |",
          "|---|---|---|---|---|---|---|"]
    for r in ontology.RELATIONS:
        dom = r.domain + (f"（{'・'.join(sorted(r.domain_subtypes))}）" if r.domain_subtypes else "")
        rng = r.range + (f"（{'・'.join(sorted(r.range_subtypes))}）" if r.range_subtypes else "")
        card = "単一(one)" if r.is_single else "配列(many)"
        wl = "必須" if r.must_wikilink else "任意"
        L.append(f"| **{r.label}** | `{r.field}` | {dom} → {rng} | {card} | "
                 f"{r.inverse}（{r.inverse_label}） | {wl} | {r.description} |")
    L.append("")

    # 状態機械
    L += ["## 状態機械", "", "### ステータス（形成の進捗）", "", "| ステータス | 記号 |", "|---|---|"]
    for name in ontology.STATUS_ORDER:
        L.append(f"| {name} | {ontology.STATUS_EMOJI[name]} |")
    L.append("")

    L += ["### 確信度（1軸目＝目的の硬さ）", "",
          f"- 範囲: **{ontology.CONFIDENCE_MIN}–{ontology.CONFIDENCE_MAX}**（その目的仮説がどれだけ「これだ」と感じられているか）",
          f"- 架空/脳内シミュレーション由来の確信度は上限 **{ontology.FICTIONAL_CAP}**"
          f"（本文マーカー: {'・'.join(ontology.FICTIONAL_MARKERS)}）",
          "- 証拠の階梯（外界にどれだけ触れたか。弱→強）: "
          + " ＜ ".join(f"〈{t}〉" for t in ontology.EVIDENCE_LADDER),
          "- 階梯外の補助タグ: " + "・".join(f"〈{t}〉" for t in ontology.EVIDENCE_AUX),
          "- **証拠の非対称性**: 確信度を上げてよいのは〈試行〉以上（外界に触れた証拠）に紐づくときのみ。"
          "〈壁打ち〉（対話のみ）単体では上げない。"]
    for min_conf, floor in sorted(ontology.EVIDENCE_FLOOR):
        L.append(f"- 確信度 {min_conf} 以上には〈{floor}〉以上の証拠を要する")
    L.append("")

    # status × confidence の許容域
    if ontology.STATUS_BOUNDS:
        L += ["### status × 確信度の許容域", "", "| ステータス | 制約 |", "|---|---|"]
        for st, b in ontology.STATUS_BOUNDS.items():
            cond = "・".join(f"{k} {v}" for k, v in b.items())
            L.append(f"| {st} | {cond} |")
        L.append("")

    L += ["### 当事者性温度（2軸目＝関わりの深さ）", "",
          "P frontmatter の `engagement-temp`（1-10）に予約。**フェーズ1では未使用**"
          "（状態機械で検証せず・ビューに出さず・ゲーム化防止のため本人にも見せない）。"
          "停滞検知・ハンドオフを作るフェーズ2以降で本実装する。", ""]
    return "\n".join(L)


def main() -> int:
    OUT.write_text(build(), encoding="utf-8")
    print(f"生成: {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
