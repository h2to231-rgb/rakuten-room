# アカウント・API 準備チェックリスト（人間が実施する作業）

アカウント作成やID登録はAIが代行できない領域のため、以下は依頼者本人が実施してください。
完了したら各項目にチェックを入れて、取得したID/キーを（機密情報なので）`.env`等の非公開ファイルに控えてください。

## 1. 楽天会員・楽天ROOMアカウント
- [x] 楽天会員登録・楽天ROOMアカウント作成済み（プロフィールURL: `room.rakuten.co.jp/room_6e370bb0f4/items`）
- [ ] プロフィール文・アイコンを設定（ジャンル横断でテストするため、最初は「暮らしの気になるもの発掘中」等の汎用トンマナでOK）
- [ ] 投稿ガイドライン・利用規約に一通り目を通す（機械的投稿の禁止事項を再確認）

## 2. 楽天アフィリエイト
- [x] 楽天アフィリエイト登録・アフィリエイトID取得済み

## 3. 楽天ウェブサービス（RWS）API
- [x] デベロッパー登録・アプリ登録（アプリ名: `rakutenroom`）
- [x] Application ID / Access Key 発行済み
- [x] **API Access Scopesで「Rakuten Ichiba API」を有効化**（これを忘れると`REQUESTED_SCOPES_NOT_ALLOWED`エラーになるので注意）
- [x] Expected QPS = 1 で登録 → リサーチAgent側もリクエスト間隔を1.2秒空けて対応済み

## 4. 秘匿情報の保管
- [x] `.env` に保存済み（`RAKUTEN_APP_ID` / `RAKUTEN_AFFILIATE_ID` / `RAKUTEN_ACCESS_KEY` / `RAKUTEN_REFERER`）
- [x] `.gitignore` に `.env` を追加済み

## 補足: 2026年2月の楽天API基盤刷新について
- 旧エンドポイント(`app.rakuten.co.jp/services/api`)は2026-05-14で廃止済み。新エンドポイントは`openapi.rakuten.co.jp/ichibams/api`
- 新形式(UUID)のapplicationIdには`accessKey`(`pk_`から始まる)が追加で必須
- リクエスト時に`Referer`と`Origin`ヘッダーを、アプリ登録時の Application URL のドメインと一致させる必要がある（一致しないと`REQUEST_CONTEXT_BODY_HTTP_REFERRER_MISSING`エラー）
- アプリ編集画面の「API Access Scopes」で対象APIにチェックが入っていないと`REQUESTED_SCOPES_NOT_ALLOWED`エラーになる

## 5. 運用面
- [ ] 投稿を毎日確認・実行できる時間帯を決める（例: 毎朝8時にAI生成の投稿案をチェック→ROOMアプリ/サイトで手動投稿）
- [ ] 通知の受け取り方法を決める（このセッションからの報告をどこで受け取るか：チャット/メール等）

---
完了したら教えてください。次のステップ（RWS APIを使ったリサーチAgentのプロトタイプ）に進みます。
