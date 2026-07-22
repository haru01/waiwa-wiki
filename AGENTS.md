# AGENTS.md — キャリア目的形成Wiki（エージェント共通の入口）

このリポジトリの規約の正典は [CLAUDE.md](CLAUDE.md)。**どのエージェントも、まず CLAUDE.md を読み、「規律あるWikiの保守者」として振る舞うこと。** 本ファイルには Claude Code 以外のエージェント向けの差分だけを書く（内容を二重管理しない）。

## Claude Code 以外での使い方

- `.claude/skills/` のスキル（`/surface` `/formulate-purpose` `/hand` `/afford` `/quilt` `/reflect` `/lemonade` `/pilot` `/decide` `/view` `/lint` `/new-person`。完全な対応表は CLAUDE.md「ワークフロー」）は Claude Code 用の入口にすぎない。各スキルの実体はただの Markdown 手順書なので、**スキル機構がないエージェントは `.claude/skills/<name>/SKILL.md` を読み、その手順に従って作業する**（対応表は CLAUDE.md「ワークフロー」）。
- 変更後は必ず決定論 lint を実行し、error を残さない:

  ```bash
  python3 tools/hwlint.py
  ```

- 型・関係・状態機械の正本は [ontology.yaml](ontology.yaml)（人間可読は `ontology.md`）。`ontology.yaml` を変更したら人間可読版を再生成する:

  ```bash
  python3 tools/gen_ontology_doc.py         # ontology.yaml → ontology.md
  ```

- 機械生成ビュー（`board`・`list`・`relations`）はレコードから決定論射影する。レコードを変更したら再生成する（Claude Code では Stop フックが自動再生成。他エージェントは手動で）:

  ```bash
  python3 tools/gen_views.py board          # 現在案件（--project <slug> で指定可）
  python3 tools/gen_views.py list           # 目的仮説リスト（系譜グラフ）
  python3 tools/gen_views.py relations      # 型付き関係グラフ・接地フィット
  ```

- 初回クローン後に `git config core.hooksPath .githooks` を一度実行し、コミット時フックを有効にする。
- 不変ルール（CLAUDE.md「不変ルール」）は全エージェント共通。特に: `sources/` は読み取り専用・冒頭に種別タグ／**確信度を上げるのは外界に触れた証拠（〈試行〉以上）があるときだけ**（壁打ち単体では上げない）／確信度変更は必ず ACT/DEC に紐づける／`log.md`・`explore-log.md` は追記のみ。

## 記述言語

すべて日本語。技術用語・ID・frontmatter キーは原文のまま。
