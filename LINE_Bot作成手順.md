# Deep Space Care LINE Bot 作成手順

この順番で進めれば、LINEでメッセージを送り、AIから返答を受け取れる状態になります。秘密鍵はこのチャットやGitHubへ貼らず、`.env`またはデプロイ先の環境変数へ設定してください。

## 全体の順番

1. ローカルでBotを起動する
2. Gemini APIキーを作る
3. LINE公式アカウントとMessaging APIチャネルを作る
4. Channel secretとChannel access tokenを取得する
5. BotをHTTPSで公開する
6. LINEのWebhook URLを接続する
7. 友だち追加して動作確認する

---

## 1. プロジェクトを開く

PowerShellで以下を実行します。

```powershell
cd "C:\Users\tomo0\OneDrive - 学校法人立命館\三回生春\01_授業\超領域リベラルアーツ\deep-space-care-linebot"
Copy-Item .env.example .env
```

`.venv`とライブラリは作成済みです。

## 2. キーなしでローカル動作を確認する

ターミナル1で起動します。

```powershell
.\.venv\Scripts\Activate.ps1
uvicorn app:app --reload --port 8000
```

ターミナル2で確認します。

```powershell
Invoke-RestMethod http://localhost:8000/health

Invoke-RestMethod -Method Post http://localhost:8000/demo `
  -ContentType "application/json" `
  -Body '{"text":"地球が遠く感じて眠れない"}'
```

`status`が`ok`になり、固定のデモ返答が返れば成功です。

## 3. Gemini APIキーを作成する

1. [Google AI Studio API Keys](https://aistudio.google.com/apikey)へGoogleアカウントでログインします。
2. APIキー作成を押し、使用するGoogle Cloudプロジェクトを選びます。
3. 作成されたキーを一度だけコピーします。
4. Google AI Studioで利用上限と対象モデルを確認します。
5. `.env`をメモ帳またはVS Codeで開き、次の行へ設定します。

```env
GEMINI_API_KEY=ここに作成したキー
GEMINI_MODEL=gemini-3.5-flash
GEMINI_TIMEOUT_MS=10000
```

Botを再起動し、もう一度`/demo`を実行します。固定文ではなく、入力内容に沿った短い返答になればAI接続成功です。
10秒以内にGeminiから返らない場合は、Botが固まらないように船内一次支援のフェイルセーフ応答へ切り替わります。発表デモでAI生成を待ちたい場合は`GEMINI_TIMEOUT_MS=20000`などに上げられます。

## 4. LINE公式アカウントを作成する

1. [LINE Official Account Manager](https://manager.line.biz/)へLINEアカウントでログインします。
2. 「アカウントを作成」を選びます。
3. アカウント名を`Deep Space Care`などにします。
4. 業種などの必須項目を入力して作成します。
5. 作成した公式アカウントの設定でMessaging APIを有効化します。

LINE公式アカウントにMessaging APIを有効化すると、LINE Developers側にMessaging APIチャネルが作成されます。

## 5. LINE Developersで認証情報を取得する

1. [LINE Developers Console](https://developers.line.biz/console/)を開きます。
2. 先ほどの公式アカウントに対応するプロバイダーとMessaging APIチャネルを選びます。
3. 「チャネル基本設定」タブにある`チャネルシークレット`をコピーします。
4. 「Messaging API設定」タブでChannel access tokenを発行します。
5. `.env`へ設定します。

```env
LINE_CHANNEL_SECRET=チャネルシークレット
LINE_CHANNEL_ACCESS_TOKEN=チャネルアクセストークン
```

この2値を逆にしないでください。Channel secretはWebhook署名検証、access tokenはLINEへの返信に使います。
Gemini APIキーは`GEMINI_API_KEY`、LINEのChannel access tokenは`LINE_CHANNEL_ACCESS_TOKEN`です。見た目が似ていても用途が違います。

## 6-A. 最速で試す場合：ngrokで一時公開する

### ngrokの準備

1. [ngrok](https://ngrok.com/)でアカウントを作ります。
2. Windows版をインストールします。
3. ngrokの画面に表示される認証コマンドを一度実行します。

```powershell
ngrok config add-authtoken あなたのngrokトークン
```

### 公開

ターミナル1でBotを起動したままにします。

```powershell
uvicorn app:app --host 0.0.0.0 --port 8000
```

ターミナル2で次を実行します。

```powershell
ngrok http 8000
```

表示された`https://xxxxx.ngrok-free.app`をコピーします。Webhook URLは次の形です。

```text
https://xxxxx.ngrok-free.app/callback
```

ngrokを終了するとURLは使えなくなる場合があります。授業デモの直前にも同じ作業が必要です。

## 6-B. 常時公開する場合：Renderへデプロイする

このフォルダには`Dockerfile`と`render.yaml`を用意してあります。

1. このプロジェクトをGitHubの非公開リポジトリへpushします。
2. [Render](https://render.com/)へGitHubでログインします。
3. `New` → `Blueprint`を選び、リポジトリを接続します。
4. `render.yaml`を認識させてサービスを作成します。
5. RenderのEnvironment画面で、次の3つをSecretとして登録します。

```text
LINE_CHANNEL_SECRET
LINE_CHANNEL_ACCESS_TOKEN
GEMINI_API_KEY
```

6. Deploy完了後、次をブラウザで開きます。

```text
https://Renderが発行したURL/health
```

`{"status":"ok", ...}`が表示されれば公開成功です。Webhook URLは以下です。

```text
https://Renderが発行したURL/callback
```

## 7. LINEへWebhook URLを登録する

1. LINE Developers Consoleで対象のMessaging APIチャネルを開きます。
2. 「Messaging API設定」タブを開きます。
3. Webhook URLに`https://公開URL/callback`を入力します。
4. 「検証」を押します。
5. 成功表示を確認します。
6. 「Webhookの利用」をオンにします。
7. 必要ならWebhookの再送もオンにします。

検証時、LINEはイベントが空のWebhookを送ります。このBotは正常に`200 OK`を返します。

## 8. LINE公式側の自動応答を停止する

LINE Official Account Managerで、Messaging APIの返答と二重にならないように設定します。

1. 「設定」または「応答設定」を開きます。
2. あいさつメッセージは必要に応じて編集します。
3. 応答メッセージまたはAI応答メッセージをオフにします。
4. Webhookを利用する設定になっていることを確認します。

## 9. 友だち追加してテストする

LINE Developers Consoleの「Messaging API設定」にあるQRコードをスマートフォンで読み取ります。

次の順に送信してください。

```text
通信状況
状態確認
地球が遠く感じて、少し眠れません
地上へ送る
```

危機対応の確認は、本番ログと混同しないテストアカウントで行ってください。

## 10. うまく動かないとき

### LINEの「検証」が失敗する

- URL末尾が`/callback`か確認する
- `http`ではなく`https`を使う
- uvicornとngrokの両方が起動中か確認する
- `.env`の`LINE_CHANNEL_SECRET`が正しいか確認する

### 既読になるが返信がない

- `LINE_CHANNEL_ACCESS_TOKEN`を確認する
- ターミナルまたはRender Logsのエラーを見る
- LINE公式アカウント側のWebhook利用がオンか確認する
- Gemini APIの利用枠とモデル利用可否を確認する

### 固定文しか返らない

- `GEMINI_API_KEY`が空、またはBot再起動前の可能性がある
- `.env`保存後にuvicornを再起動する

## 完成判定

以下がすべて通れば完成です。

- `/health`が`status: ok`
- LINE DevelopersのWebhook検証が成功
- LINEで「通信状況」に船内モードの返答
- 自由入力にGeminiが短い日本語で返答
- 「状態確認」「船内支援」「地上へ送る」が動作
