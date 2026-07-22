# projects/ — 個人案件（人単位）

目的形成は**案件（人）単位**で分ける。各案件は自分の生データ（`sources/`）と Wiki（`wiki/`）を1フォルダに持つ。スキーマ層（`ontology.yaml`・`CLAUDE.md`・`AGENTS.md`・`playbooks/`・`templates/`・`.claude/skills/`）はリポジトリ全体で共有する。

```
projects/
├── current.md            # 現在アクティブな案件（slug）を指すポインタ
├── <slug>/
│   ├── sources/          # この案件の生データ（不変層・AIは読むだけ・冒頭に種別タグ）
│   └── wiki/
│       ├── purposes/<PREFIX>-P-NNN.md       # 目的仮説
│       ├── constraints/<PREFIX>-C-NNN.md     # 制約・手中の鳥
│       ├── activities/<PREFIX>-ACT-NNN.md    # 試行
│       ├── reflections/<PREFIX>-REF-NNN.md   # 内省
│       ├── decisions/<PREFIX>-DEC-NNN.md     # 意思決定
│       ├── views/         # 生成物
│       ├── index.md ├── log.md ├── stage.md └── explore-log.md
└── ...
```

## ID は接頭辞つき（Obsidian のリンク一意性のため）

- ファイル名＝ID で、**案件接頭辞つき**（例 `SELF-P-001.md`）。infix は P/C/ACT/REF/DEC。
- 採番は**種別×案件ごと**の既存最大+1。ID再利用禁止（取り下げた番号は欠番）。

## 新しい案件の作り方

**推奨: `/new-person` スキル**を使う。`templates/project/` の雛形から `projects/<slug>/` を作り、`projects/current.md` を切り替えるところまで行う。

手動で作る場合:

1. `cp -r templates/project/. projects/<slug>/`（`sources/` と空の `wiki/` 一式が揃う）。
2. `wiki/stage.md`・`explore-log.md`・`log.md` の `YYYY-MM-DD` を今日の日付にする。
3. 接頭辞（大文字・他案件と重複しない）を決め、`projects/current.md` の一覧に追記して `current-project` を切り替える。

## 現在の案件

- （まだ無し。`/new-person` で最初の案件を作る。ドッグフーディングは `self`／接頭辞 `SELF`）
