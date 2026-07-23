# waiwa-wiki — キャリア目的形成Wiki

試行錯誤のループを通じて、**キャリアの目的・制約・使命が本人の中に事後的に立ち上がること**を支援する個人向け LLM-wiki。日々の壁打ち・試行を沈殿させて**確信を育て**、停滞したら**意図的に確信を揺らして探索域を開き直す**。目的が立ち上がったら目的達成型エージェントへ接続する。

`haru01/hypothesis-wiki`（スタートアップの仮説検証 CPF→PMF）を写像元に、キャリア目的形成ドメインへフォークしたもの。

## コアの考え方

- **目的は事前に設定や見つけるものではなく、試行錯誤で事後的に立ち上がる。** 最初の確信度は低くてよい。
- **二つの温度**: 確信度（目的の硬さ）と当事者性温度（関わりの深さ）は別軸（当事者性はフェーズ1では未実装・予約のみ）。
- **証拠の非対称性**: 確信度を上げてよいのは**外界に触れた証拠**（〈試行〉〈他者反応〉〈継続〉）に紐づくときだけ。壁打ち（エージェントとの対話）単体では上げない（壁打ち沼の防止）。
- **Effectuation（効果的思考の5原則）**: 予測でなく行動で未来を作る。①手中の鳥（手の内の資源＝制約Cから始める）／②許容可能な損失／③クレイジーキルト（パートナーの事前コミット）／④レモネード（想定外を逆手に）／⑤飛行機のパイロット（行動で制御）。理論は [playbooks/effectuation.md](playbooks/effectuation.md)。

## レコード種別（型）

`P` 目的仮説 ／ `C` 制約・手中の鳥 ／ `ACT` 試行 ／ `REF` 内省 ／ `DEC` 意思決定。型・関係・状態機械の正本は [ontology.yaml](ontology.yaml)（人間可読は [ontology.md](ontology.md)）。

## 使い方（フェーズ1・手動ループ）

ループの骨格は**エフェクチュエーション5原則**（理論: [playbooks/effectuation.md](playbooks/effectuation.md)）。

```
①手中の鳥 /hand（制約Cを数える）
  → ②許容損失 /afford・③パートナー /quilt で試行を設計
  → 人が試す → /reflect（trial/third-party で確信度を上げる。壁打ちdialogueでは上げない）
  → ④レモネード /lemonade（驚き・偶然を逆手に新しい種・ピボット）
  ↕ ⑤パイロット /pilot（予測への逃避・根拠なき確信を突き、行動へ引き戻す＝深さ方向の引き下げ）
形成: /surface（種を出す）→ /formulate-purpose（反証可能化）
```

主要スキル: `/new-person` `/surface` `/formulate-purpose` `/hand`① `/afford`② `/quilt`③ `/reflect` `/lemonade`④ `/pilot`⑤ ＋支援 `/decide` `/view` `/lint`。

## ツール

```bash
python3 tools/hwlint.py                # 決定論 lint（証拠非対称ルール含む）
python3 tools/gen_views.py list|board|relations   # ビュー生成
python3 tools/gen_ontology_doc.py      # ontology.yaml → ontology.md 再生成
python3 -m pytest tests/test_hwlint.py # テスト
```

Claude Code では Stop フックが自動で lint とビュー再生成を行う。初回に `git config core.hooksPath .githooks`。

## ロードマップ

- **フェーズ1（現在）**: 手動ループ＋日次沈殿。停滞検知は手動。
- **フェーズ2**: `/stall-check` で停滞検知を自動化（当事者性温度を本実装。確信度は自動で下げず本人承認を挟む）。
- **フェーズ3**: `/handoff` で立ち上がった目的を目的達成型エージェントへ接続。
- **フェーズ4**: 多人数運用への一般化。
