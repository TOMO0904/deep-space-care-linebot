import base64
import hashlib
import hmac
import json
import os
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI, Header, HTTPException, Request
import httpx

load_dotenv()

APP_NAME = "Deep Space Care"
DB_PATH = Path(os.getenv("DB_PATH", "carebot.db"))
LINE_CHANNEL_SECRET = os.getenv("LINE_CHANNEL_SECRET", "")
LINE_CHANNEL_ACCESS_TOKEN = os.getenv("LINE_CHANNEL_ACCESS_TOKEN", "")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-3.5-flash")
GEMINI_TIMEOUT_MS = int(os.getenv("GEMINI_TIMEOUT_MS", "10000"))
MISSION_NAME = os.getenv("MISSION_NAME", "Deep Space Habitat-1")
COMM_DELAY_MINUTES = os.getenv("COMM_DELAY_MINUTES", "").strip()
MEDICAL_ROLE = os.getenv("MEDICAL_ROLE", "船内医療担当クルー")
SAFE_MODULE = os.getenv("SAFE_MODULE", "共用モジュール")
HABITAT_MODULES = ("個室モジュール", "共用モジュール", "観測窓", "運動エリア", "医療ラック")

CRISIS_TERMS = ("死にたい", "消えたい", "自殺", "自傷", "殺したい", "もう生きられない")
SYSTEM_PROMPT = """あなたは深宇宙居住者を支える日本語の一次的メンタルケアAIです。
役割は診断・治療ではなく、孤立した利用者の話を短く受け止め、感情の言語化と安全なセルフケアを支援することです。
返答は原則180字以内。順序は 1) 共感的な要約 2) 今できる小さな行動を1つ 3) 答えやすい質問を1つ。
文化や価値観を決めつけず、俯瞰効果・孤立・閉鎖環境・通信遅延を背景として尊重してください。
医療診断、服薬指示、断定、過度な依存を促す表現は禁止です。緊急性が疑われる場合はAIだけで抱えず、船内クルー・医療担当・緊急手順へつなげます。
"""

app = FastAPI(title=APP_NAME, version="0.1.0")


def init_db() -> None:
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute("""CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT NOT NULL,
            role TEXT NOT NULL,
            content TEXT NOT NULL,
            created_at TEXT NOT NULL
        )""")
        conn.execute("""CREATE TABLE IF NOT EXISTS ground_queue (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT NOT NULL,
            summary TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'queued',
            created_at TEXT NOT NULL
        )""")


def save_message(user_id: str, role: str, content: str) -> None:
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute(
            "INSERT INTO messages(user_id, role, content, created_at) VALUES (?, ?, ?, ?)",
            (user_id, role, content, datetime.now(timezone.utc).isoformat()),
        )


def recent_context(user_id: str, limit: int = 6) -> list[dict[str, str]]:
    with sqlite3.connect(DB_PATH) as conn:
        rows = conn.execute(
            "SELECT role, content FROM messages WHERE user_id=? ORDER BY id DESC LIMIT ?",
            (user_id, limit),
        ).fetchall()
    return [{"role": role, "content": content} for role, content in reversed(rows)]


def verify_line_signature(body: bytes, signature: str) -> bool:
    if not LINE_CHANNEL_SECRET:
        return False
    digest = hmac.new(LINE_CHANNEL_SECRET.encode(), body, hashlib.sha256).digest()
    expected = base64.b64encode(digest).decode()
    return hmac.compare_digest(expected, signature)


def delay_label() -> str:
    return f"片道約{COMM_DELAY_MINUTES}分" if COMM_DELAY_MINUTES else "ミッション位置に応じた通信遅延"


def menu_reply() -> str:
    return (
        f"🚀 {MISSION_NAME} 船内メンタルケア端末\n"
        "使えるコマンド：\n"
        "・ミッション：現在の船内モード\n"
        "・状態確認：つらさ/睡眠/孤立感チェック\n"
        "・船内ログ：地上送信用の短い記録\n"
        "・地球を見たい：俯瞰効果ケア\n"
        "・睡眠：深宇宙の睡眠リセット\n"
        "・船内支援：クルーへ助けを求める文面\n"
        "・地上へ送る：会話要約を送信待ちキューへ保存"
    )


def mission_briefing() -> str:
    return (
        f"🛰️ Mission Briefing\n"
        f"船名：{MISSION_NAME}\n"
        f"通信：{delay_label()}。地上返信を待たず船内一次支援を優先。\n"
        f"安全集合：{SAFE_MODULE}\n"
        f"引継ぎ：{MEDICAL_ROLE}\n"
        "今日の方針：感情を数値化→小さな行動→必要時はバディ対応。"
    )


def onboard_log_prompt() -> str:
    return (
        "📓 船内ログ記録フォーマット\n"
        "次の形で送ってください：\n"
        "1) いまの気分：\n"
        "2) つらさ0〜10：\n"
        "3) 身体状態：睡眠/食欲/頭痛など\n"
        "4) ほしい支援：\n"
        "書けたら『地上へ送る』で送信待ちキューに保存できます。"
    )


def overview_care_reply() -> str:
    return (
        "🌏 俯瞰効果ケア\n"
        "地球が遠く感じる時は、畏怖・孤独・責任感が同時に強くなることがあります。"
        "30秒だけ観測窓か写真を見て、見えた色を3つ言葉にしてください。"
        "今の感情は『寂しさ』『美しさ』『怖さ』のどれに近いですか？"
    )


def sleep_protocol_reply() -> str:
    return (
        "🌙 深宇宙睡眠リセット\n"
        "1) 照明を少し落とす\n"
        "2) 端末を目線より下へ\n"
        "3) 4秒吸って、6秒吐く×5回\n"
        "4) 明日の最初の作業を1つだけメモ\n"
        "眠れない強さは0〜10でいくつですか？"
    )


def confinement_care_reply() -> str:
    return (
        "🧭 閉鎖環境ケア\n"
        f"今いる場所を {', '.join(HABITAT_MODULES[:3])} のどれかとして意識してみましょう。"
        "閉鎖感が強い時は、場所を1つ移動するだけでも脳が『状況が変わった』と受け取りやすいです。"
        f"可能なら{SAFE_MODULE}へ移動して、水を一口飲んでください。"
    )


def crisis_reply() -> str:
    return (f"今は船内で直ちに安全を確保します。AIだけで抱えず、{MEDICAL_ROLE}へ『心理安全プロトコル』を要請してください。"
            f"ひとりにならず、危険物から離れて{SAFE_MODULE}へ移動してください。地上返信を待たずに船内手順を優先します。近くに呼べるクルーはいますか？")


def safe_fallback_reply() -> str:
    return ("いまAI生成応答が不安定なので、船内一次支援モードで返します。まず30秒、息を長く吐いてください。"
            f"つらさが7以上なら{MEDICAL_ROLE}へ共有し、{SAFE_MODULE}で誰かと合流してください。今のつらさは0〜10でいくつですか？")


def queue_ground_report(user_id: str) -> str:
    context = recent_context(user_id, limit=8)
    summary = " / ".join(item["content"][:120] for item in context[-4:]) or "会話記録なし"
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute(
            "INSERT INTO ground_queue(user_id, summary, created_at) VALUES (?, ?, ?)",
            (user_id, summary, datetime.now(timezone.utc).isoformat()),
        )
    return (f"地上支援チーム向けの要約を送信待ちキューへ保存しました。現在は{delay_label()}を想定しています。"
            "緊急時は地上返信を待たず、船内クルーへ連絡してください。")


def mission_command(user_id: str, text: str) -> str | None:
    normalized = text.strip().lower()
    if normalized in {"メニュー", "menu", "help", "ヘルプ", "宇宙船モード"}:
        return menu_reply()
    if normalized in {"ミッション", "通信状況", "ミッション状況", "status", "briefing"}:
        return mission_briefing()
    if normalized in {"状態確認", "チェックイン", "check-in", "checkin"}:
        return (
            "🩺 船内チェックイン\n"
            "①つらさ0〜10\n"
            "②睡眠時間\n"
            "③食欲\n"
            "④孤立感0〜10\n"
            "⑤今すぐ必要な支援\n"
            "この順に教えてください。地上返信を待たず船内で一次対応します。"
        )
    if normalized in {"船内ログ", "ログ", "log"}:
        return onboard_log_prompt()
    if normalized in {"地球を見たい", "地球", "俯瞰効果", "overview"}:
        return overview_care_reply()
    if normalized in {"睡眠", "眠れない", "sleep"}:
        return sleep_protocol_reply()
    if normalized in {"閉鎖感", "息苦しい", "狭い", "confinement"}:
        return confinement_care_reply()
    if normalized in {"地上へ送る", "地上報告", "ground"}:
        return queue_ground_report(user_id)
    if normalized in {"船内支援", "助けを呼ぶ", "crew"}:
        return f"{MEDICAL_ROLE}へ連絡し、{SAFE_MODULE}でバディ対応を開始してください。伝える言葉は『心理安全プロトコルを要請します』です。"
    return None


def generate_reply(user_id: str, text: str) -> str:
    command_reply = mission_command(user_id, text)
    if command_reply:
        return command_reply
    if any(term in text for term in CRISIS_TERMS):
        return crisis_reply()
    if not GEMINI_API_KEY:
        return "話してくれてありがとう。今の気持ちを0〜10で表すと、つらさはいくつくらいですか？まず30秒、ゆっくり息を吐いてみましょう。"

    history = recent_context(user_id)
    conversation = "\n".join(f"{item['role']}: {item['content']}" for item in history)
    try:
        system_instruction = (SYSTEM_PROMPT + f"\n現在地は宇宙船 {MISSION_NAME}。地上との通信条件は{delay_label()}。"
                              f"船内引継ぎ先は{MEDICAL_ROLE}、安全集合場所は{SAFE_MODULE}。地上返信を前提にせず、船内で実行可能な提案を優先する。")
        response = httpx.post(
            "https://generativelanguage.googleapis.com/v1beta/interactions",
            headers={"x-goog-api-key": GEMINI_API_KEY, "Content-Type": "application/json"},
            json={
                "model": GEMINI_MODEL,
                "system_instruction": system_instruction,
                "input": f"直近の会話:\n{conversation}\n\n今回の利用者入力:\n{text}",
                "generation_config": {"thinking_level": "low"},
            },
            timeout=GEMINI_TIMEOUT_MS / 1000,
        )
        response.raise_for_status()
        data = response.json()
        if data.get("output_text"):
            return data["output_text"].strip()[:1000]
        for step in data.get("steps", []):
            if step.get("type") != "model_output":
                continue
            text_blocks = [block.get("text", "") for block in step.get("content", []) if block.get("type") == "text"]
            if text_blocks:
                return "".join(text_blocks).strip()[:1000]
        return safe_fallback_reply()
    except Exception:
        return safe_fallback_reply()


def quick_reply_items() -> list[dict[str, object]]:
    labels = ["メニュー", "ミッション", "状態確認", "地球を見たい", "睡眠", "地上へ送る"]
    return [
        {"type": "action", "action": {"type": "message", "label": label[:20], "text": label}}
        for label in labels
    ]


async def line_reply(reply_token: str, text: str, with_quick_reply: bool = True) -> None:
    if not LINE_CHANNEL_ACCESS_TOKEN:
        return
    message: dict[str, object] = {"type": "text", "text": text}
    if with_quick_reply:
        message["quickReply"] = {"items": quick_reply_items()}
    async with httpx.AsyncClient(timeout=15) as client:
        response = await client.post(
            "https://api.line.me/v2/bot/message/reply",
            headers={"Authorization": f"Bearer {LINE_CHANNEL_ACCESS_TOKEN}"},
            json={"replyToken": reply_token, "messages": [message]},
        )
        response.raise_for_status()


@app.on_event("startup")
def startup() -> None:
    init_db()


@app.get("/health")
def health() -> dict[str, object]:
    return {"status": "ok", "mission": MISSION_NAME, "communication_condition": delay_label(),
            "medical_role": MEDICAL_ROLE, "safe_module": SAFE_MODULE,
            "line_configured": bool(LINE_CHANNEL_ACCESS_TOKEN), "gemini_configured": bool(GEMINI_API_KEY),
            "gemini_timeout_ms": GEMINI_TIMEOUT_MS}


@app.get("/mission")
def mission() -> dict[str, object]:
    with sqlite3.connect(DB_PATH) as conn:
        queued = conn.execute("SELECT COUNT(*) FROM ground_queue WHERE status='queued'").fetchone()[0]
    return {"mission": MISSION_NAME, "onboard_care": True, "communication_condition": delay_label(),
            "ground_reports_queued": queued, "handoff": MEDICAL_ROLE, "safe_module": SAFE_MODULE}


@app.post("/demo")
def demo(payload: dict[str, str]) -> dict[str, str]:
    text = payload.get("text", "").strip()
    if not text:
        raise HTTPException(400, "text is required")
    user_id = payload.get("user_id", "demo-user")
    save_message(user_id, "user", text)
    reply = generate_reply(user_id, text)
    save_message(user_id, "assistant", reply)
    return {"reply": reply}


@app.post("/callback")
async def callback(request: Request, x_line_signature: str = Header(default="")) -> dict[str, str]:
    body = await request.body()
    if not verify_line_signature(body, x_line_signature):
        raise HTTPException(400, "invalid LINE signature")
    payload = json.loads(body)
    for event in payload.get("events", []):
        if event.get("type") == "follow":
            user_id = event.get("source", {}).get("userId", "unknown")
            welcome = "搭乗を確認しました。\n" + menu_reply()
            save_message(user_id, "assistant", welcome)
            await line_reply(event["replyToken"], welcome)
            continue
        if event.get("type") != "message" or event.get("message", {}).get("type") != "text":
            continue
        user_id = event.get("source", {}).get("userId", "unknown")
        text = event["message"]["text"].strip()
        save_message(user_id, "user", text)
        reply = generate_reply(user_id, text)
        save_message(user_id, "assistant", reply)
        await line_reply(event["replyToken"], reply)
    return {"status": "ok"}
