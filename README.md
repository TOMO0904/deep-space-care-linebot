# Deep Space Care — LINE Bot prototype

深宇宙の通信遅延・閉鎖隔離環境を想定した、一次的メンタルケアLINE Botです。診断や治療の代替ではありません。通常時は「共感 → 小さなセルフケア → 質問」を返し、危機表現は生成AIへ渡す前に検出して船内の有人支援へ誘導します。

## 宇宙船内モード

Botは地上との常時接続を前提にせず、船内で一次対応を完結させる設計です。

- `状態確認`: つらさ・睡眠・食欲・孤立感・必要な支援を定型チェック
- `通信状況`: ミッション名、通信条件、船内引継ぎ先、安全集合場所を表示
- `船内支援`: 医療担当クルーへの連絡文とバディ対応を提示
- `地上へ送る`: 会話要約をSQLiteの送信待ちキューへ保存し、通信回復後の同期を想定
- 危機表現: 地上返信を待たず、危険物から離れて共用モジュールへ移動し、船内心理安全プロトコルを開始

`MISSION_NAME`、`COMM_DELAY_MINUTES`、`MEDICAL_ROLE`、`SAFE_MODULE`は宇宙船ごとに`.env`で変更できます。`GEMINI_TIMEOUT_MS`でGemini応答待ち時間を調整できます。実運用ではLINE自体も地上ネットワーク依存となるため、同じAPIを船内LAN用チャット端末へ接続し、LINEは地上実証用UIとして利用する構成を想定します。

## 1. ローカル起動

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env
uvicorn app:app --reload --port 8000
```

`GEMINI_API_KEY`が空でも固定応答のデモモードで動きます。

```powershell
Invoke-RestMethod -Method Post http://localhost:8000/demo `
  -ContentType 'application/json' `
  -Body '{"text":"地球が遠く感じて眠れない"}'
```

## 2. LINE接続

1. LINE DevelopersでMessaging APIチャネルを作成する。
2. Channel secretとChannel access tokenを`.env`へ設定する。
3. HTTPSで公開する（Render、Railway、Cloud Run、またはデモ時はngrok等）。
4. Webhook URLを `https://公開URL/callback` に設定し、Use webhookを有効化する。
5. LINE Developersの「検証」を実行してから公式アカウントを友だち追加する。

Webhookは受信した生の本文に対してHMAC-SHA256署名を検証します。アクセストークンやAPIキーをGitへコミットしないでください。

## プロダクト境界

- できること: 傾聴、感情の言語化、短い呼吸・グラウンディング提案、会話履歴の保持、危機時の有人支援誘導
- しないこと: 診断、治療、服薬指示、緊急対応の代替、完全自律の安全保証
- 実証時: 研究同意、ログの匿名化・保存期間、退出方法、専門家レビューを別途設計する

## 評価案

- 主観指標: 応答前後のストレス0–10、安心感、文化的違和感
- 行動指標: 継続率、提案実行率、有人支援への適切な移行率
- システム指標: 応答時間、通信断時の可用性、誤警報・見逃し率

## テスト

```powershell
pytest -q
```

参考: LINE Messaging APIのWebhookは署名検証が必須で、reply tokenは一度だけ・原則1分以内に使用します。AI応答にはGemini APIを利用し、遅延時は船内一次支援のフェイルセーフ応答へ切り替えます。
