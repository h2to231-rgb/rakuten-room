# 楽天ROOM 自律運営プロジェクト

AIエージェントを活用して楽天ROOMの運営を半自律化するプロジェクト。
投稿の最終実行は規約上、必ず人間（依頼者本人）が行う。AIは調査・企画・文章生成・分析までを担当する。

## ステータス
- フェーズ: 1. リサーチAgentプロトタイプ稼働（`research/research_agent.py`）
- ROOMアカウント: 作成済み
- 楽天アフィリエイトID / RWS APIキー: 取得・`.env`設定済み
- 投稿頻度目標: 毎日1本
- 投稿実行担当: 依頼者本人

## ディレクトリ構成
- `docs/` — セットアップ手順・計画ドキュメント
  - `01_account_setup_checklist.md` — ROOMアカウント作成〜API申請の手順（人間が実施、トラブルシュート記録あり）
  - `02_genre_test_plan.md` — 複数ジャンル横断テストの計画
  - `03_kpi_framework.md` — KPI設計と目標値（仮説ベース、走らせながら補正）
  - `04_pr_disclosure_guidelines.md` — PR表記・優良誤認/有利誤認防止ガイドライン
  - `05_daily_operations_manual.md` — **毎日の運用手順書（まずはこれを見る）**
- `research/` — リサーチAgent（`research_agent.py`）と収集した商品データ
- `compliance/` — 投稿下書きのPR表記・誇大表現チェッカー（`pr_checker.py`）
- `content_drafts/` — ライティングAgent（`writing_agent.py`）と生成された投稿案（人間の承認待ち）
- `reports/` — `run_daily.py`が生成する日次の投稿候補レポート、`analyze.py`が生成する分析レポート
- `analytics/` — 分析Agent（`analyze.py`）と実績記録（`metrics_log.csv`）
- `run_daily.py` — 毎日実行するメインスクリプト（リサーチ→ドラフト→コンプラチェック→レポート）

## 実績記録・分析の使い方
投稿したら、ROOM管理画面・楽天アフィリエイト管理画面を見て以下を記録する:
```bash
python analytics/analyze.py log --date 2026-08-24 --genre beauty \
    --followers 12 --posts 1 --likes 3 --clicks 0 --conversions 0 --revenue 0
```
たまってきたら集計・KPI比較・ローテーション調整の提案を見る:
```bash
python analytics/analyze.py report
```

## 進め方（ロードマップ）
1. ✅ ジャンル選定方針・KPI設計
2. ✅ 楽天ウェブサービス(RWS) APIキー取得 → リサーチAgentのプロトタイプ作成（`research/research_agent.py`）
3. ✅ コンプラチェック用PR表記テンプレート作成（[docs/04_pr_disclosure_guidelines.md](docs/04_pr_disclosure_guidelines.md) + `compliance/pr_checker.py`）
4. ✅ ライティングAgent（テンプレートベース、`content_drafts/writing_agent.py`）
5. ✅ 投稿案を日次で束ねるレポート（`run_daily.py` → `reports/YYYY-MM-DD.md`）
6. ✅ 分析Agent（`analytics/analyze.py`。ROOM/アフィリエイト管理画面の実績を人間が記録→週次・ジャンル別に自動集計しKPIと比較）

これで一連の半自律運用フローが揃いました。あとは実際に投稿を開始し、`analytics/analyze.py log` で実績を記録していく運用フェーズです。

## 毎日の運用方法
```bash
python run_daily.py
```
これ1コマンドで「リサーチ→ドラフト生成→コンプラチェック→レポート作成」が走る。
`reports/YYYY-MM-DD.md` を開いて候補を確認し、気に入ったものを選んでROOMアプリ/サイトから**手動で**投稿する。

## 解決済みの課題
- ~~リサーチAgentのキーワード検索は、ジャンルと無関係な商品（例: 美容ジャンルの検索でミックスナッツが混入）を拾うことがある~~
  → キーワードに加えて`genreId`（楽天市場ジャンルID）で必ず絞り込むように修正済み（`research/research_agent.py`の`GENRE_IDS`）。美容ジャンルで再検証し、無関係商品の混入がなくなったことを確認済み。

## リサーチAgentの使い方
```bash
python research/research_agent.py                # 今日の曜日に対応するジャンルで実行
python research/research_agent.py --genre beauty  # ジャンルを指定
```
`research/YYYY-MM-DD_<genre>.json` に候補商品（商品名・価格・レビュー数・アフィリエイトリンク等）が保存される。

## 重要な制約
- 楽天ROOM利用規約第11条により、スクリプト等による機械的投稿・自動投稿は禁止。**投稿ボタンを押す操作は必ず人間が行う。**
- 景品表示法のステルスマーケティング規制（2023年10月施行）により、AI生成の紹介文にはPR表記・アフィリエイトリンクである旨の明示が必要。
