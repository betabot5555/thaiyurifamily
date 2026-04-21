import os
import instaloader
import requests

IG_USER = os.getenv('IG_USERNAME')
IG_PW = os.getenv('IG_PASSWORD')
TG_TOKEN = os.getenv('TG_TOKEN')
CHAT_ID = os.getenv('TG_CHAT_ID')

def send_tg(msg):
    url = f"https://api.telegram.org/bot{TG_TOKEN}/sendMessage"
    requests.post(url, json={"chat_id": CHAT_ID, "text": msg})

def main():
    L = instaloader.Instaloader()
    try:
        L.login(IG_USER, IG_PW)
        send_tg("✅ 程式夥伴報告：GitHub Actions 與 IG 登入測試成功！")
        print("Login success!")
    except Exception as e:
        send_tg(f"❌ 登入失敗：{str(e)}")
        print(f"Error: {e}")

if __name__ == "__main__":
    main()
