import os
import requests

# Load Config
TOKEN = os.getenv("HEALTH_CHAT_TOKEN")
NOTIFICATION_CHAT_ID = os.getenv("NOTIFICATION_CHAT_ID")
KOD_CHAT_ID = os.getenv("KOD_CHAT_ID")

def send_health_ping(chat_id, bot_name):
    if not chat_id: return
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    msg = f"🟢 <b>Health Check:</b> {bot_name} is active and scanning."
    requests.post(url, params={"chat_id": chat_id, "text": msg, "parse_mode": "HTML"})

if __name__ == "__main__":
    # Ping both channels
    send_health_ping(NOTIFICATION_CHAT_ID, "Main RNS Bot")
    send_health_ping(KOD_CHAT_ID, "KOD Monitor")
