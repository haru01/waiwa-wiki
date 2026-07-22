---
name: new-person
description: 新しい個人案件を projects/<slug>/ に雛形から作成し、現在の案件に設定する。ユーザーが「新しい案件を作りたい」「自分用に始めたい」「new-person」「ドッグフーディングを始める」と言ったときに使う。
---

# /new-person — 新しい個人案件の作成

`templates/project/` の雛形から `projects/<slug>/` を作り、現在の案件に設定する。目的形成は人（案件）単位で分ける。

## 手順

1. **slug と接頭辞を決める** — ユーザーに確認する（`AskUserQuestion` 可）:
   - `<slug>`: ディレクトリ名（小文字・ハイフン。ドッグフーディングは `self`）。既存の `projects/` と重複しないこと。
   - `<PREFIX>`: ID接頭辞（大文字。`self` なら `SELF`）。他案件と重複しないこと（Obsidianのリンク一意性のため）。`projects/current.md` の一覧と照合する。

2. **雛形をコピーする** — `cp -r templates/project/. projects/<slug>/`。これで `sources/`（README付き）と `wiki/`（`purposes/` `constraints/` `activities/` `reflections/` `decisions/`＝空・`.gitkeep`、`views/`＝README、`index.md`・`log.md`・`stage.md`・`explore-log.md`）が揃う。

3. **雛形のプレースホルダを埋める** — `wiki/stage.md`・`wiki/explore-log.md`・`wiki/log.md` の `YYYY-MM-DD` を今日の日付にする。`stage.md` の初期モードは `探索`。

4. **現在の案件に登録する** — `projects/current.md` を更新: `current-project: <slug>` に切り替え、「プロジェクト一覧」テーブルに `| <slug> | <PREFIX> | <説明> |` を1行追加する。

5. **確認して終了** — 作成したパスと、以後スキルが `projects/<slug>/` を対象に動くことを伝える。最初の一歩は `/surface`（漠然としたキャリア観から目的仮説の種を出す）へ誘導する。

## 守ること

- 接頭辞は**全案件で一意**にする。既存 `projects/*/wiki/purposes/` 等の接頭辞を確認する。
- 雛形（`templates/project/`）自体は編集しない（スキーマ層）。コピー先だけを編集する。
- 既存案件を上書きしない。`projects/<slug>/` が既にあれば中止してユーザーに確認する。
- このスキルはレコード（P/C/ACT/REF/DEC）を作らない。器を用意するだけ。中身は `/surface` 以降で作る。
