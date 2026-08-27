# CLAUDE.md

このプロジェクトで得た教訓・ハマりどころのまとめ。次にこのリポジトリで作業するとき、または類似の自動化（note/X等）を別リポジトリで組むときに参照すること。

## プロジェクトの本質
半自律型の楽天ROOM運営エージェント。リサーチ・執筆・コンプラチェック・投稿画面への入力まではAIが行うが、**最終的な投稿確定ボタンのクリックは必ず人間が行う**。これは技術的制約ではなく、楽天ROOM利用規約（機械的投稿の禁止）に由来する意図的な設計。この一線は絶対に越えない。

## 絶対に守ること
- どんなに便利でも、投稿の最終確定操作は自動化しない
- APIキー・パスワード・認証コードは自分（Claude）では入力しない。ユーザー自身に操作してもらう
- 生成する投稿文には必ずPR表記を含め、断定的な効果表現・誇大表現を避ける（`docs/04_pr_disclosure_guidelines.md`、`compliance/pr_checker.py`）

## 楽天ウェブサービスAPIのハマりどころ
- 2026年2月に基盤刷新あり。旧エンドポイント(`app.rakuten.co.jp/services/api`)は廃止済み。新エンドポイントは`openapi.rakuten.co.jp/ichibams/api`
- `applicationId`に加えて`accessKey`(`pk_`から始まる)が必須
- リクエストの`Referer`/`Origin`ヘッダーを、アプリ登録時のApplication URLのドメインと一致させる必要がある
- アプリ編集画面の「API Access Scopes」で対象API（例: Rakuten Ichiba API）を明示的に有効化しないと`REQUESTED_SCOPES_NOT_ALLOWED`になる
- キーワード検索だけだとジャンルと無関係な商品が混ざる（例: 美容ジャンルでミックスナッツ）。`genreId`で必ずハードフィルタすること（`research/research_agent.py`の`GENRE_IDS`）

## クラウド版の自動化（Claude Codeルーティン）は断念した
理由を残しておく（同じ罠に二度落ちないため）:
- クラウドのGitHub連携（コネクタ）は**読み取り専用かつ公開リポジトリのみ**が既定。非公開リポジトリを見せるには一度Publicにする必要があった
- 書き込み（git push）にはAnthropicの正式GitHub Appのインストールが必要で、これは**Claude Team/Enterpriseプランでしか設定できない**（`claude.ai/admin-settings/github`が組織設定扱いのため、Proプランではアクセス不可）
- 環境変数欄は「全ユーザーに見える」設計でシークレット保存に非推奨
- ネットワークポリシーは既定で外部ドメインアクセスがブロックされる。「カスタム」モードで許可ドメインを個別登録する必要がある（`openapi.rakuten.co.jp`, `hb.afl.rakuten.co.jp`など）
→ 結論: **個人のProプランでの自動化はローカル実行一択**。「クラウドで完結させたい」という要望が出たら、上記の制約を先に説明すること。

## ローカル自動化（採用した方式）
- Windowsタスクスケジューラ + `claude` CLI（npm版）の非対話実行(`claude -p ... --permission-mode bypassPermissions`)
- **デスクトップ版Claude Code（Windows Store/MSIX版）はCLIとして呼び出せない。** `npm install -g @anthropic-ai/claude-code`で別途CLI版を入れる必要がある（両者は共存可能）
- npmインストール時、postinstallスクリプトが`--allow-scripts`なしだとブロックされる。`npm install -g --allow-scripts=@anthropic-ai/claude-code @anthropic-ai/claude-code`が必要
- CLI版は独自ログインが必要（`claude auth login`）。デスクトップ版のログイン状態とは別
- 新しくインストールしたコマンド（node/npm/claude等）は、既存のPowerShellウィンドウのPATHには反映されない。**新しいウィンドウで開き直す**こと

### タスクスケジューラの罠
- `DisallowStartIfOnBatteries`が既定でtrue。ノートPCがバッテリー駆動だと実行されず"Queued"のまま止まる → falseに変更が必要
- スリープから自動起床させるには`WakeToRun`をtrueに設定（`schtasks`では設定不可。`Set-ScheduledTask`のSettingsオブジェクトで変更）
- Windows Updateによる夜間の自動再起動で、スリープ復帰タイマー自体が失われ実行がスキップされることがある。`StartWhenAvailable`をtrueにして緩和（完全な対策ではない）
- 完全な電源オフからの自動起動はBIOS(UEFI)のRTC Wake設定が必要で、これはソフトウェアからは変更不可

### `claude mcp add`のCLIバグ
`claude mcp add <name> -- <command> --flag value`の形式で、`--`区切り後のフラグ付き引数が正しく子プロセスに渡らず`unknown option`エラーになることがある（v2.1.246で確認）。回避策: フラグなしで一旦登録し、`~/.claude.json`の`mcpServers`セクションを直接編集して`args`配列にフラグを追記する。

### 自分自身の再帰起動はブロックされる
Claude Code Auto ModeのClassifierが、「Claude Code自身をインストール/起動/権限バイパスで呼び出す」系の操作を毎回ブロックする（`npm install -g @anthropic-ai/claude-code`、`claude mcp add`、`claude -p ...`など）。これは安全装置であり回避しようとしないこと。**該当操作は必ずユーザー自身のターミナルで実行してもらう。**

### ブラウザ自動化（Playwright MCP）
- `@playwright/mcp`を`--user-data-dir <永続プロファイルパス>`付きでMCPサーバー登録すると、一度ログインしたセッションを使い回せる
- ログインは、対話モードの`claude`セッションで「ブラウザで◯◯を開いて」と頼んで開いたウィンドウで人間が行う（このMCP接続はセッション起動時に読み込まれるため、既存の会話には反映されない＝新しいプロセスが必要）
- **投稿後はブラウザウィンドウを閉じること。** 開いたままだと翌日の自動実行が同じプロファイルでブラウザを起動できず失敗する
- ROOMの投稿画面のような「他社サービスへの入力自動化」は、投稿確定ボタンさえ押さなければ規約違反にならないとは限らない。プラットフォームごとに規約の自動化禁止条項を個別確認すること（note/X/Instagramは横展開時に要確認、特にX/Instagramは非公式自動化への取り締まりが厳しい）

## 文字コード関連
Windows PowerShell 5.1のコンソールは既定でUTF-8表示に対応していない。ログファイルの中身が化けても、実データ（ファイル自体）はUTF-8で正しいことが多い。`notepad`で開く、またはReadツールで直接読むのが確実。
