---
name: view
description: 目的レコードからビュー（系譜／試行ボード／関係グラフ）を wiki/views/ に生成する。ユーザーが「一覧を見たい」「系譜を見たい」「ボードを見たい」「view」「list」「board」「relations」「ビューを生成」と言ったときに使う。
---

# /view — ビュー生成

レコード（SSoT）からビューを生成し `wiki/views/` に出力する。**ビューは生成物**であり、記録の修正はレコード側で行いビューは再生成する。

> **共通規約**（案件解決・ID/接頭辞・リンク記法・.gitkeep・承認規律）は [CLAUDE.md「スキル共通規約」](../../../CLAUDE.md) が正典。ビューは現在案件のレコードのみを対象にする（共通規約1）。以下は本スキル固有の手順。

## サブコマンド

引数に応じて生成するビューを切り替える。指定がなければどれを生成するか尋ねる。いずれも `python3 tools/gen_views.py <view>`（現在案件。`--project <slug>` で指定可）を実行して生成する（手作業で書かない）。

### `list` — 目的仮説リスト（機械生成）

generator が目的仮説 frontmatter を射影する: **目的の系譜**図（ノード=目的、矢印=`leads-to`〔因果〕/`derived-from`〔派生〕/`revises`〔書換〕、★=`core`）、目的仮説テーブル（ID・タイトル・確信度・ステータス・関連〔← 派生元／⟲ 書換／→ 因果先／検証活動 ACT〕・直近の根拠）、次に外界で確かめるべき目的、ステータス別サマリ。**系譜や ★ を出したいときはビューでなくレコード側（`leads-to`・`derived-from`・`revises`・`core`）に書く**。
- 出力: `wiki/views/purposes-list.md`

### `board` — 試行ボード（機械生成）

generator が ACT（試行）を1実験＝1エントリで date 昇順に並べ、`riskiest-assumption`・テストカード（方法・成功基準）・学習カードの `学びの要点`・frontmatter `outcome`・DEC逆引きの判断・現在地（P スナップショット＋最新DECの `次の一手`）を**レコードから射影**する。
- 出力: `wiki/views/board.md`

### `relations` — 型付き関係グラフ（機械生成）

オントロジー（[ontology.md](../../../ontology.md)）の全関係型を frontmatter から射影する: (1) 全レコード（P/C/ACT/REF/DEC）をノードにした mermaid 型付き関係グラフ、(2) 関係インデックス（関係型ごとの 始点→終点 表）、(3) **バックリンク索引**（各レコードが inverse で誰から参照されているか）、(4) **目的↔制約 接地**（`grounded-in`。未接地の目的を機械集計）。関係を増やしたいときは**ビューでなくレコード側の frontmatter**（`leads-to`・`grounded-in` 等）に書く。
- 出力: `wiki/views/relations.md`

## 守ること

- 生成ファイルの冒頭に必ず生成物マーカー（手編集禁止）が入る。手で編集しない。
- 記録とビューが矛盾する場合、**レコードが正**。ビューを直すのでなくレコードを直して再生成する。
- ビュー生成では確信度・ステータス・log を変更しない（読み取り専用の集計）。
- Claude Code では Stop フック（`tools/hooks/stop_view_gen.py`）がレコード変更時に board/list/relations を自動再生成する。手動実行は明示的に作り直したいときのみ。
