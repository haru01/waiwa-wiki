# 現在のプロジェクト（個人案件）

```yaml
current-project: self
```

現在アクティブな案件は **self**（このツール自体のドッグフーディング）。`/new-person` で別の人の案件を作ると切り替わる。

スキル（`/surface` `/formulate-purpose` `/hand` `/reflect` `ゆさぶり` ほか）は、まずこのファイルで現在の案件 `<slug>` を確認し、`projects/<slug>/` 配下の `sources/`・`wiki/` を対象に動く。別の人（案件）に切り替えるときは `current-project` を書き換える（または対話で対象を指定する）。

## プロジェクト一覧

| slug | 接頭辞 | 説明 |
|---|---|---|
| self | SELF | このツール自体のドッグフーディング（キャリア目的形成） |
