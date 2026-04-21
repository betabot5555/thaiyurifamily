import os
import time
import requests
import instaloader

# ================= 配置區域 =================
# 從 GitHub Secrets 讀取敏感資訊
IG_USER = os.getenv('IG_USERNAME')
IG_PW = os.getenv('IG_PASSWORD')
TG_TOKEN = os.getenv('TG_TOKEN')
CHAT_ID = os.getenv('TG_CHAT_ID')

# --- 填入你想監控的名單 ---
TIKTOK_TARGETS = ["srchafreen", "angelssbecky", "emiamily", "beobonny"]  # TikTok 帳號名單
IG_TARGETS = ["srchafreen", "angelssbecky", "emiamily", "beonnnie"]        # IG 帳號名單
# ===========================================

def send_tg(msg):
    """發送訊息到 Telegram"""
    url = f"https://api.telegram.org/bot{TG_TOKEN}/sendMessage"
    payload = {"chat_id": CHAT_ID, "text": msg}
    try:
        requests.post(url, json=payload, timeout=10)
    except Exception as e:
        print(f"Telegram 發送失敗: {e}")

def check_tiktok_live(username):
    """檢查 TikTok 直播狀態"""
    url = f"https://www.tiktok.com/@{username}/live"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    }
    try:
        # allow_redirects=True 是為了追蹤直播間的跳轉
        response = requests.get(url, headers=headers, timeout=15, allow_redirects=True)
        # 檢查頁面源碼中是否包含直播關鍵字
        if 'is_live":true' in response.text or '"status":2' in response.text:
            return True
        return False
    except Exception as e:
        print(f"TikTok 檢查 {username} 失敗: {e}")
        return False

def run_ig_logic():
    """執行 IG 監控邏輯"""
    if not IG_USER or not IG_PW:
        print("未設定 IG 帳密，跳過 IG 檢查。")
        return

    L = instaloader.Instaloader()
    try:
        # 嘗試登入
        L.login(IG_USER, IG_PW)
        
        for target in IG_TARGETS:
            # 這裡目前只是「檢查連線」，之後可以加入下載 Story 的邏輯
            profile = instaloader.Profile.from_username(L.context, target)
            print(f"IG 帳號 {target} 連線成功，UserID: {profile.userid}")
            # send_tg(f"📸 IG 監測中: {target} 連線正常")
            
    except Exception as e:
        # 如果登入失敗（例如 Checkpoint），發送通知但程式不崩潰
        error_msg = str(e)
        if "Checkpoint" in error_msg:
            send_tg(f"⚠️ IG 登入需要驗證 (Checkpoint)。請在手機按「這是我」或改用 Session 方式。")
        else:
            send_tg(f"❌ IG 檢查出錯: {error_msg[:100]}")

def main():
    print("--- 啟動自動化巡邏 ---")
    
    # 1. 檢查 TikTok 列表
    print(f"正在巡邏 TikTok 名單: {TIKTOK_TARGETS}")
    for tt_user in TIKTOK_TARGETS:
        if check_tiktok_live(tt_user):
            send_tg(f"🔴 報告！TikTok 帳號 {tt_user} 正在直播！\n傳送門: https://www.tiktok.com/@{tt_user}/live")
        else:
            print(f"DEBUG: TikTok {tt_user} 沒開台")
        time.sleep(2) # 禮貌休息
    
    # 2. 檢查 IG 列表
    print(f"正在巡邏 IG 名單: {IG_TARGETS}")
    run_ig_logic()

    print("--- 巡邏結束 ---")

if __name__ == "__main__":
    main()
