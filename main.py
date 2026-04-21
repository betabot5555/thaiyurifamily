import os
import json
import requests
import instaloader
from pathlib import Path
from datetime import datetime, timezone

IG_USER = os.getenv("IG_USERNAME")
IG_SESSION_FILE = os.getenv("IG_SESSION_FILE", "ig_session")
TG_TOKEN = os.getenv("TG_TOKEN")
CHAT_ID = os.getenv("TG_CHAT_ID")

TIKTOK_TARGETS = ["srchafreen", "angelssbecky", "emiamily", "beobonny"]
IG_TARGETS = ["srchafreen", "angelssbecky", "emiamily", "beonnnie"]
STATE_FILE = Path("monitor_state.json")


def load_state():
    if STATE_FILE.exists():
        try:
            return json.loads(STATE_FILE.read_text(encoding="utf-8"))
        except Exception:
            pass
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
        print("TG_TOKEN / TG_CHAT_ID 未設定")
        return

    url = f"https://api.telegram.org/bot{TG_TOKEN}/sendMessage"
    payload = {"chat_id": CHAT_ID, "text": msg}
    try:
        r = requests.post(url, json=payload, timeout=15)
        if r.status_code != 200:
            print(f"Telegram 發送失敗: {r.status_code} {r.text[:200]}")
    except Exception as e:
        print(f"Telegram 發送失敗: {e}")


def check_tiktok_live(username):
    url = f"https://www.tiktok.com/@{username}/live"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
        "Accept-Language": "en-US,en;q=0.9",
    }

    try:
        r = requests.get(url, headers=headers, timeout=20, allow_redirects=True)
        text = r.text

        print(f"[TikTok] {username} status={r.status_code} final_url={r.url}")

        live_markers = [
            '"is_live":true',
            '"status":2',
            '"liveRoom"',
            '"LIVE"',
        ]

        is_live = any(marker in text for marker in live_markers)

        return {
            "ok": True,
            "is_live": is_live,
            "status_code": r.status_code,
            "final_url": r.url
        }

    except Exception as e:
        print(f"TikTok 檢查 {username} 失敗: {e}")
        return {
            "ok": False,
            "is_live": False,
            "error": str(e)
        }


def init_instaloader():
    L = instaloader.Instaloader(
        download_pictures=False,
        download_videos=False,
        download_video_thumbnails=False,
        save_metadata=False,
        compress_json=False,
        quiet=True,
    )

    if not IG_USER:
        raise RuntimeError("未設定 IG_USERNAME")

    # 建議預先把 session file 放到 repo runner 可讀位置
    L.load_session_from_file(IG_USER, filename=IG_SESSION_FILE)
    return L


def check_ig_stories(L, target):
    try:
        profile = instaloader.Profile.from_username(L.context, target)
        userids = [profile.userid]

        stories = L.get_stories(userids=userids)
        latest_ts = None

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
            "error": str(e)
        }


def run_tiktok_logic(state):
    for username in TIKTOK_TARGETS:
        result = check_tiktok_live(username)

        if not result["ok"]:
            print(f"[TikTok] {username} check failed: {result.get('error')}")
            continue

        prev_live = state["tiktok_live"].get(username, False)
        now_live = result["is_live"]

        if now_live and not prev_live:
            send_tg(f"🔴 TikTok {username} 正在直播！\nhttps://www.tiktok.com/@{username}/live")

        state["tiktok_live"][username] = now_live


def run_ig_logic(state):
    try:
        L = init_instaloader()
    except Exception as e:
        send_tg(f"❌ IG 初始化失敗：{str(e)[:150]}")
        return

    for target in IG_TARGETS:
        result = check_ig_stories(L, target)

        if not result["ok"]:
            err = result.get("error", "")
            if "Checkpoint" in err:
                send_tg("⚠️ IG session 失效，需要重新驗證 / 匯出 session。")
            else:
                print(f"[IG] {target} failed: {err}")
            continue

        latest_ts = result["latest_ts"]
        prev_ts = state["ig_story_latest"].get(target)

        if latest_ts is not None:
            if prev_ts is not None and latest_ts > prev_ts:
                dt = datetime.fromtimestamp(latest_ts, tz=timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
                send_tg(f"📸 IG {target} 有新 Story！最新時間：{dt}\nhttps://www.instagram.com/{target}/")
            state["ig_story_latest"][target] = latest_ts
        else:
            print(f"[IG] {target} 目前冇 story")


def main():
    print("--- 啟動巡邏 ---")
    state = load_state()

    run_tiktok_logic(state)
    run_ig_logic(state)

    save_state(state)
    print("--- 巡邏結束 ---")


if __name__ == "__main__":
    main()
