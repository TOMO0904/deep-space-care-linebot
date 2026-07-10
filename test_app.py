import base64
import hashlib
import hmac

import app


def test_signature(monkeypatch):
    monkeypatch.setattr(app, "LINE_CHANNEL_SECRET", "secret")
    body = b'{"events":[]}'
    sig = base64.b64encode(hmac.new(b"secret", body, hashlib.sha256).digest()).decode()
    assert app.verify_line_signature(body, sig)
    assert not app.verify_line_signature(body, "wrong")


def test_crisis_route():
    reply = app.generate_reply("u", "消えたい")
    assert "AIだけで抱えず" in reply
    assert "クルー" in reply


def test_spacecraft_commands(tmp_path, monkeypatch):
    monkeypatch.setattr(app, "DB_PATH", tmp_path / "test.db")
    app.init_db()
    assert "船内メンタルケア端末" in app.generate_reply("u", "メニュー")
    assert "Mission Briefing" in app.generate_reply("u", "ミッション")
    assert "船内チェックイン" in app.generate_reply("u", "状態確認")
    assert "通信" in app.generate_reply("u", "通信状況")
    assert "俯瞰効果ケア" in app.generate_reply("u", "地球を見たい")
    assert "深宇宙睡眠リセット" in app.generate_reply("u", "睡眠")
    assert "船内ログ記録" in app.generate_reply("u", "船内ログ")
    assert "送信待ちキュー" in app.generate_reply("u", "地上へ送る")
