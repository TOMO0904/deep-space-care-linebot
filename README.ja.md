[English](README.md) | **日本語**

# Deep Space Care — LINE Bot プロトタイプ

LINEで使う、一次的なメンタルケアのチャットボットです。深宇宙ミッションのように、地上との通信に大きな遅延がある閉鎖・隔離環境のクルーを想定しています。これは**プロトタイプ（デモ）**であり、医療製品ではなく、診断や治療の代わりにもなりません。

## 課題

地上の支援と常につながれない状況では、気持ちの面での一次対応を船内で完結させる必要があります。また、そうした場面のボットは安全でなければなりません。誰かが危機的な状態を訴えたときに、生成AIに即興で答えさせてはいけません。

## 解決方法

- 通常のメッセージには、Google Geminiで **共感 → 小さなセルフケア → 次の質問** という流れの返信を作ります。
- 危機を示す表現は、文章が生成AIに渡る**前に**検出し、船内の有人サポートへ案内します。
- ミッション向けの「船内モード」コマンド: 状態チェック、通信状況、船内の相談先、地上への送信キュー（SQLiteに保存し、通信が戻ったら同期）。
- Geminiの応答が遅い・使えない場合は、固定の安全な返信に切り替えます（タイムアウトは設定可能）。
- APIキーなしのデモモード（固定返信）で、キーがなくても試せます。

## 主な機能

- LINE Messaging APIのWebhookで、リクエスト本文そのものに対する **HMAC-SHA256署名検証**
- 危機表現の事前フィルターと、有人サポートへの引き継ぎ
- SQLiteへの会話履歴の保存
- ミッションの設定値（`MISSION_NAME`、`COMM_DELAY_MINUTES`、`MEDICAL_ROLE`、`SAFE_MODULE`、`GEMINI_TIMEOUT_MS`）を環境変数で指定
- LINEなしで試せる `/demo` HTTPエンドポイント
- 自動テスト（`pytest`）、デプロイ用の Dockerfile と `render.yaml`

## 技術スタック

Python · FastAPI · Uvicorn · httpx · LINE Messaging API · Google Gemini API · SQLite · pytest · Docker / Render

## セットアップ

```bash
python -m venv .venv
source .venv/bin/activate        # Windows: .\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
cp .env.example .env             # キーを記入。デモモードなら GEMINI_API_KEY は空のまま
uvicorn app:app --reload --port 8000
```

デモ用エンドポイントを試す:

```bash
curl -X POST http://localhost:8000/demo -H "Content-Type: application/json" \
  -d '{"text":"眠れなくて、地球がとても遠く感じる"}'
```

LINEにつなぐ場合は、Messaging APIのチャネルを作成し、チャネルシークレットとアクセストークンを `.env` に設定します。アプリをHTTPSで公開し、Webhook URLを `https://<your-host>/callback` に設定してください。トークンやAPIキーは絶対にコミットしないでください。

テストは `pytest -q` で実行します。

## 対応範囲と安全性

- 行うこと: 話を聴く、気持ちを言葉にする手助け、短い呼吸法・グラウンディングの提案、有人サポートへのエスカレーション。
- 行わないこと: 診断、治療、服薬の助言、緊急サービスの代わり。
- 実際に運用するには、研究への同意取得、ログの匿名化、保存期間のルール、専門家によるレビューが必要です。

## ステータス

コンセプトデモとして作ったプロトタイプです。船内モードの詳しい説明、セットアップ手順、5分間の発表用台本は [docs/DETAILS.ja.md](docs/DETAILS.ja.md) にあります。
