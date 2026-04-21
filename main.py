import os
import json
import asyncio
from pathlib import Path
from datetime import datetime, timezone

import requests
import instaloader
from TikTokLive import TikTokLiveClient

# ================= 配置區域 =================
TG_TOKEN = os.getenv("TG_TOKEN")
CHAT_ID = os.getenv("TG_CHAT_ID")

IG_USER = os.getenv("IG_USERNAME")
IG_SESSION_FILE = os.getenv("IG_SESSION_FILE", "ig_session")

TIKTOK_TARGETS = ["user1", "user2", "user3"]
IG_TARGETS = ["ig_user1", "ig_user2"]

STATE_FILE = Path("monitor_state.json")
# ===========================================


def load_state():
    if STATE_FILE.exists():
        try:
            return json.loads(STATE_FILE.read_text(encoding="utf-8"))
        except Exception as e:
            print(f"讀取 state 失敗，改用新 state: {e}")

    return {
        "tiktok_live": {},
        "ig_story_latest": {}
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


def init_instaloader():
    if not IG_USER:
        raise RuntimeError("未設定 IG_USERNAME")

    session_path = Path(IG_SESSION_FILE)

    L = instaloader.Instaloader(
        download_pictures=False,
        download_videos=False,
        download_video_thumbnails=False,
        save_metadata=False,
        compress_json=False,
        quiet=True,
    )

    if not session_path.exists():
        raise RuntimeError(
            f"IG session file 不存在: {session_path}. "
            "請先在 GitHub Actions workflow 還原 session file。"
        )

    L.load_session_from_file(IG_USER, filename=str(session_path))

    logged_in_user = L.test_login()
    if not logged_in_user:
        raise RuntimeError("IG session 無效或已過期，請重新匯出 session file")

    print(f"[IG] 已登入 session，用戶: {logged_in_user}")
    return L


def check_ig_stories(L, target):
    try:
        profile = instaloader.Profile.from_username(L.context, target)
        latest_ts = None

        stories = L.get_stories(userids=[profile.userid])
        for story in stories:
            for item in story.get_items():
                ts = int(item.date_utc.replace(tzinfo=timezone.utc).timestamp())
                if latest_ts is None or ts > latest_ts:
                    latest_ts = ts

        return {
            "ok": True,
            "latest_ts": latest_ts
        }

    except Exception as e:
        return {
            "ok": False,
            "latest_ts": None,
            "error": str(e)
        }


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


def run_ig_logic(state):
    print(f"正在巡邏 IG 名單: {IG_TARGETS}")

    if not IG_TARGETS:
        print("IG 名單為空，跳過")
        return

    try:
        L = init_instaloader()
    except Exception as e:
        send_tg(f"❌ IG 初始化失敗：{str(e)[:200]}")
        return

    for target in IG_TARGETS:
        result = check_ig_stories(L, target)

        if not result["ok"]:
            err = result.get("error", "")
            print(f"[IG] {target} 檢查失敗: {err}")
            send_tg(f"⚠️ IG 檢查 {target} 出錯：{err[:150]}")
            continue

        latest_ts = result["latest_ts"]
        prev_ts = state["ig_story_latest"].get(target)

        print(f"[IG] {target} prev_ts={prev_ts} latest_ts={latest_ts}")

        if latest_ts is None:
            print(f"[IG] {target} 目前冇 story")
            continue

        if prev_ts is not None and latest_ts > prev_ts:
            dt = datetime.fromtimestamp(
                latest_ts, tz=timezone.utc
            ).strftime("%Y-%m-%d %H:%M:%S UTC")

            send_tg(
                f"📸 報告！IG 帳號 {target} 有新 Story！\n"
                f"最新時間: {dt}\n"
                f"傳送門: https://www.instagram.com/{target}/"
            )

        state["ig_story_latest"][target] = latest_ts


def main():
    print("--- 啟動自動化巡邏 ---")

    state = load_state()

    run_tiktok_logic(state)
    run_ig_logic(state)

    save_state(state)

    print("--- 巡邏結束 ---")


if __name__ == "__main__":
    main()
