# オントロジー改善バックログ（現オントロジー版）

オントロジー層（`ontology.yaml` を SSoT とする型・関係・状態機械。`ontology.py` がローダ、
`hwlint.py`／`gen_views.py` が駆動）の**未着手の改善余地**だけを記録する。各項目は
「対象／状態／課題／改善案／根拠」で書く。状態は `未対応` `対応中` `対応済み`。

> **このドキュメントの範囲について**
> 旧版は写像元（`hypothesis-wiki`）の語彙（`hypotheses`/`addresses`/ステージ `CPF`→`PMF`/`H-NNN`/
> スキル `plan`・`ingest`・`chabudai` 等）で書かれ、現オントロジー（`P`/`C`/`ACT`/`REF`/`DEC`・
> Effectuation 5原則・ステージ廃止）と乖離していた。実装済みだった改善（SSoT一本化・lint強化・
> 証拠タグ一元化・ビュー拡充）は既に本体へ取り込まれ、コードと `tests/` が現時点の正本である。
> そのため本ファイルは**現オントロジーで今も有効な、まだ着手していない項目のみ**を残す。

## 現状評価（サマリ）

土台（`ontology.yaml` を SSoT に、`ontology.py` がローダ、`hwlint`/`gen_views` が駆動、`relations`
ビュー、証拠の非対称性の機械強制）は敷けている。以下は「導入した仕組みをさらに効かせる／
表現力を広げる」ための残件で、いずれも A〜D（＝土台の完遂）が済んだ後の層にあたる。

### 既に本体へ取り込み済み（再提案しないための備忘）

- **SSoT一本化**: 語彙(enum)・関係・状態機械を `ontology.yaml` に集約、`ontology.py` 経由で射影。
  証拠タグ・架空マーカー語彙も `ontology.yaml` に一元化。
- **lint 強化**（`tools/hwlint.py`）: 証拠の非対称性（`check_evidence_asymmetry`）・status↔confidence
  矛盾（`check_status_confidence`）・証拠の階梯×確信度（`check_evidence_floor`）・fictional-cap 全行走査・
  DEC の based-on 欠落・P→P 関係の循環／自己参照・未検証高確信（`check_untested_focus`）・
  未接地の高確信（`check_grounding_gaps`）。
- **ビュー**（`tools/gen_views.py`）: `relations` ビュー新設、関係が0件でも節見出し＋「該当なし」、
  「次に外界で確かめるべき目的」の ⚠️未着手（試行なし）マーカー、目的↔制約の接地フィット表。

以下 E・F・G を残件として整理する。**E は表現力拡張（新関係・新属性＝SSoT の設計変更）なので人間の
合意を要する。F・G は調査由来のパターン**で、このリポジトリの哲学（決定論・SSoT・証拠強制）に馴染む
範囲だけを採る。H に「あえて採らない」判断を記録する。

---

## E. オントロジーの表現力拡張（要設計合意）

実データのプローズには存在するのに、既存関係では表せない構造。新関係・新属性の導入は SSoT の設計変更なので、
人間の合意を要する。**E3（`affects`）・E4（`supersedes`/`counters`）は合意のうえ実装済み**（関係は現在10種:
`derived-from`/`leads-to`/`grounded-in`/`revises`/`counters`/`purposes`/`reflects-on`/`based-on`/
`affects`/`supersedes`）。残るは E1（cluster）・E2（ACT→P 極性）。

### OI-E1: 目的のクラスタ（グルーピング）

- **対象**: `ontology.yaml`
- **状態**: 未対応（要設計）
- **課題**: 複数の目的仮説を「核心クラスタ」等として束ねたいことがあるのに、表現手段が単一Pの
  `core: true` しか無い。関連する目的群を第一級概念として扱えない。
- **改善案（案）**: `cluster` 属性（名前付きグループ）か、P→P の `sibling`/`part-of` 関係を検討。
  人手のグルーピングで足りる規模なら属性で軽く扱う。
- **根拠**: `ontology.yaml` の `core: true` が唯一の集約手段。

### OI-E2: ACT→P の支持/反証の極性

- **対象**: `ontology.yaml`
- **状態**: 未対応（要設計）
- **課題**: `purposes`（ACT→P）は無極性。支持/反証は ACT の `outcome`（活動単位・1個）にしか無く、
  **1試行が複数の目的仮説を別結果で検証する**場合を目的単位で表せない（例: 1つの打診が
  ある目的は支持・別の目的は反証、という結果を型で持てない）。
- **改善案（案）**: `purposes` 関係に per-link の極性（支持/反証/判断保留）を持たせる、または
  `supports`/`refutes` の2関係に分ける。ビュー（board の判定列）へ射影する。
- **根拠**: `ontology.yaml` relations の `purposes`、ACT frontmatter `outcome`（活動単位で単一）。

### OI-E3: DEC→P 直接参照

- **対象**: `ontology.yaml`
- **状態**: **対応済み**（`affects` 関係）
- **課題**: 意思決定がどの目的仮説を動かしたかが型で表せなかった（`based-on` は DEC→ACT のみ）。
  ピボット・巻き戻し・意図的引き下げが対象目的を frontmatter で指せず、本文プローズ止まりだった。
- **実装**: DEC→P の `affects`（inverse: affected-by「影響した判断」）を追加。config 駆動で
  `relations` ビューのバックリンク索引に自動掲載＝目的側から形成の来歴を辿れる。templates/decision.md・
  CLAUDE.md にも記載。テストは `tests/test_hwlint.py::AffectsTest`。
- **根拠**: `ontology.yaml` relations に DEC→P が無かった（`based-on` は DEC→ACT）。

### OI-E4: DEC→DEC（取り消し/後継）・対抗目的・反証の連鎖

- **対象**: `ontology.yaml`
- **状態**: **対応済み**（DEC→DEC `supersedes`・P→P `counters`）／反証の連鎖は未対応（OI-E2 の極性待ち）
- **課題**:
  - **DEC→DEC**: ある意思決定が過去の意思決定を巻き戻す／上書きする関係が frontmatter に無かった。
  - **対抗目的**: `/lemonade`（レモネード）で生まれる対抗仮説・ピボットの種が、既存目的の「対抗」
    として記録されるが型が無くプローズ止まりだった。
  - **反証の連鎖**（未対応）: ある目的の反証が `leads-to`（因果の型）で下流目的へ伝播する構造は、
    ACT→P の極性（OI-E2・保留中）と `leads-to` の合成が要るため、E2 実装後に再検討する。
- **実装**: DEC→DEC の `supersedes`（inverse: superseded-by・循環禁止）と P→P の `counters`
  （inverse: countered-by・**相互対抗 A↔B は正当なので `acyclic: false`**＝自己参照のみ禁止）を追加。
  `check_relation_cycles` を「domain==range の全関係」に一般化し supersedes を循環検査対象に含めた。
  テストは `tests/test_hwlint.py::SupersedesTest`・`CountersTest`。
- **根拠**: `ontology.yaml` relations（旧7関係）に DEC→DEC・P→P 対抗が無かった。

---

## F. トポロジー駆動の探索域ギャップ検出（調査由来）

**出所**: infranodus/nashsu 系の「ネットワークトポロジーを計算して、孤立ノード・ブリッジ・
構造的知識ギャップを算出し、能動的に探索域を提案する」パターン。

**現状**: 個別の辺の型検証（`check_frontmatter_refs`）と、局所的なギャップ検出（`check_untested_focus`＝
検証活動が紐づかない高確信、`check_grounding_gaps`＝未接地の高確信）は実装済み。残るのは
**グラフ全体の構造指標**を優先度に織り込む層。

### OI-F1: 孤立ノード・ブリッジ・下流依存度の算出

- **対象**: `tools/gen_views.py`
- **状態**: 未対応（要設計）
- **課題**: 系譜（`derived-from`/`leads-to`）と検証（`purposes`）を合成した目的グラフ上で、(a) どの関係も
  持たない**孤立した目的**、(b) 系譜クラスタ間をつなぐ**ブリッジ目的**、(c) `leads-to` の下流被参照数＝
  「崩れると波及が大きい背骨」を機械算出できるのに、`next_to_verify`（`gen_views.py`）は
  確信度×ステータス×検証活動の有無しか見ておらず、グラフ上の位置を優先度に織り込んでいない。
- **改善案（案）**: これらをトポロジー指標として `relations` ビュー末尾に要約表で出す。
  `relation_edges` は辺を持つので、そこから次数・被参照数を算出する（中心性まではこの規模では不要）。
  優先度は E より低い（表現力より運用実感が先）。
- **根拠**: `gen_views.py` の `relation_edges`／`next_to_verify`。

---

## G. 時間軸 ／ 確信度の陳腐化（調査由来）

**出所**: LLM Wiki v2 の「各主張に確証度＋タイムスタンプを持たせ、裏付けの無い主張は時間経過で
可視的に陳腐化させる」パターン（ただし**自動減衰はせず可視化に留める**＝不変ルール準拠）。

**現状の穴**: 確信度履歴テーブルは日付を持つ（`parse_history` → `Project.history`）のに、
**時間軸を lint もビューも見ていない**。半年前に確信度を上げた目的と昨日のそれが同格に扱われ、
再検証が促されない。市場・前提が動くキャリア形成ドメインでは無視できない盲点。

### OI-G1: 高確信・立ち上がった目的の staleness 検出（低リスク・先行推奨）

- **対象**: `tools/hwlint.py`、`ontology.yaml`
- **状態**: **対応済み**（`hwlint.check_staleness`）
- **課題**: `status: 立ち上がった` かつ高確信度の目的で、確信度履歴の**最終行の日付が古い**ものを
  「陳腐化の疑い＝再検証を検討」として出せるのに出していなかった。
- **実装**:
  1. `ontology.yaml` の confidence 節に `staleness-days: 180` を追加（マジックナンバーをコードに置かない・
     `ontology.STALENESS_DAYS` に射影・`ontology.md` にも記載）。
  2. `hwlint.check_staleness` が基準日（`--today` 引数 or `datetime.date.today()`＝`Project.today`）を使い、
     `立ち上がった` 目的の確信度履歴最終行が閾値超のものを **warning**（error にしない）で報告。
  3. **数値は自動で下げない**（不変ルール厳守）。再検証を促す可視化のみ。下げたい場合は必ず ACT/DEC
     （例: `self-reflection` や再検証の試行）に紐づけて人が動かす。テストは `tests/test_hwlint.py::StalenessTest`。
- **根拠**: `parse_history`（履歴日付は取得済み）、CLAUDE.md「長期放置は `/lint`（LLM）が担う」記述、
  不変ルール（確信度・ステータスの変更は必ず ACT/DEC に紐づける）。

### OI-G2: Supersession（旧目的のアーカイブ）の型表現

- **対象**: `ontology.yaml`
- **状態**: 部分対応（DEC→DEC `supersedes` は追加済み）／P の明示 stale/superseded 状態は未対応
- **課題**: 「この目的は新目的に置き換えられ古い（stale/superseded）」という明示状態が無い。
  `derived-from`（系譜）＋`revises`（書き換え）＋履歴テーブルで部分的に実現しているが、
  「旧版を消さずアーカイブ状態にする」型が無い。
- **達成/残り**: 意思決定の後継は OI-E4 の `supersedes`（DEC→DEC）で表現できるようになった。
  残るのは「P 自体の superseded 状態」だが、新 status の追加は状態機械を膨らませるため保留。
  当面は `棚上げ` ＋ `revises`/`derived-from` ＋ `supersedes` の合成で表す。必要性が実データで
  裏づけられたら再検討する。
- **根拠**: `ontology.yaml` relations（`derived-from`/`revises`/`supersedes`）、OI-E4。

---

## H. あえて採らない（調査パターンのうち現規模で過剰なもの）

将来の再検討時に「検討済みで見送った」と分かるよう、却下判断も記録する。

- **ベクトル検索／ハイブリッド検索（LanceDB・BM25・埋め込み・2ホップ拡張）** — 1案件十数〜数十
  レコードの規模では、Claude が `wiki/` を直接読む現方式より精度・保守性ともに劣化する。導入コスト過大。
- **確証度付き BFS 検索ツール（MAX_DEPTH/MIN_CONFIDENCE/MAX_NODES）** — 同上。この規模でグラフ探索の
  ランタイムを持つ必要が無い。関係の可視化は `relations` ビューで足りる。
- **デスクトップ GUI（Tauri/React/Rust）** — 可視化要件は Obsidian＋mermaid ビューで充足。
- **多シグナル関連度モデル＋コミュニティ検出（Louvain・Adamic-Adar の類似度行列）** — 規模的に過剰。
  クラスタ（OI-E1）は人手のグルーピングで扱う。

> 注: 調査の出典は Karpathy gist に集約されており、個別リポジトリ名・数式は裏取りが弱い。
> F・G は具体実装ではなく**設計パターン**として採用している。

---

## 着手順の目安

1. ~~**G1（staleness 可視化）**~~ — **対応済み**（`hwlint.check_staleness`・`staleness-days: 180`）。
2. ~~**E3+E4（DEC→P `affects`・DEC→DEC `supersedes`・P→P `counters`）**~~ — **対応済み**
   （G2 の DEC→DEC 部分も合流）。config 駆動で lint/relations ビュー/ontology.md に自動追従。
3. **F1（トポロジー指標）** — `relations` ビューへの要約表追加。実データが増えて運用実感が出てから。
4. **E1（cluster）・E2（ACT→P 極性）** — 残りの表現力拡張。E1 は属性 vs 関係の設計分岐、E2 は ACT
   `outcome` との役割重複の整理が要る。`/reflect`・`/decide` の実データが溜まり「型が無くて困った」
   場面を根拠に判断する（それまで保留）。反証の連鎖（OI-E4）は E2 の極性が入ってから再検討。
