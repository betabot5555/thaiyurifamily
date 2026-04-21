import os
import json
import asyncio
from pathlib import Path

import requests
from TikTokLive import TikTokLiveClient

TG_TOKEN = os.getenv("TG_TOKEN")
CHAT_ID = os.getenv("TG_CHAT_ID")

TIKTOK_TARGETS = [
    "emiamily",
    "beobonny",
    "srchafreen",
    "angelssbecky"
]

STATE_FILE = Path("monitor_state.json")


def load_state():
    if STATE_FILE.exists():
        try:
            return json.loads(STATE_FILE.read_text(encoding="utf-8"))
        except Exception as e:
            print(f"讀取 state 失敗，改用新 state: {e}")

    return {
        "tiktok_live": {}
    }


def save_state(state):
    STATE_FILE.write_text(
        json.dumps(state, ensure_ascii=False, indent=2),
        encoding="utf-8"
    )


def send_tg(msg):
    if not TG_TOKEN or not CHAT_ID:
        print("未設定 TG_TOKEN / TG_CHAT_ID")
        return

    url = f"https://api.telegram.org/bot{TG_TOKEN}/sendMessage"
    payload = {
        "chat_id": CHAT_ID,
        "text": msg
    }

    try:
        r = requests.post(url, json=payload, timeout=15)
        if r.status_code != 200:
            print(f"Telegram 發送失敗: {r.status_code} {r.text[:300]}")
    except Exception as e:
        print(f"Telegram 發送失敗: {e}")


async def check_tiktok_live_async(username):
    try:
        client = TikTokLiveClient(unique_id=username)
        is_live = await client.is_live()
        return {
            "ok": True,
            "is_live": bool(is_live)
        }
    except Exception as e:
        return {
            "ok": False,
            "is_live": False,
            "error": str(e)
        }


def check_tiktok_live(username):
    return asyncio.run(check_tiktok_live_async(username))


def run_tiktok_logic(state):
    print(f"正在巡邏 TikTok 名單: {TIKTOK_TARGETS}")

    for username in TIKTOK_TARGETS:
        result = check_tiktok_live(username)

        if not result["ok"]:
            print(f"[TikTok] {username} 檢查失敗: {result.get('error')}")
            continue

        prev_live = state["tiktok_live"].get(username, False)
        now_live = result["is_live"]

        print(f"[TikTok] {username} prev={prev_live} now={now_live}")

        if now_live and not prev_live:
            send_tg(
                f"🔴 報告！TikTok 帳號 {username} 正在直播！\n"
                f"傳送門: https://www.tiktok.com/@{username}/live"
            )

        state["tiktok_live"][username] = now_live


def main():
    print("--- 啟動自動化巡邏 ---")
    state = load_state()
    run_tiktok_logic(state)
    save_state(state)
    print("--- 巡邏結束 ---")


if __name__ == "__main__":
    main()
