import requests
import os
import base64

# --- CONFIGURATION ---
TOKEN = os.getenv("TELEGRAM_TOKEN")
GITHUB_TOKEN = os.getenv("GH_PAT")
REPO_NAME = "louca1221/TheHive_RNS"
TICKER_FILE = "tickers.txt"
# NEW: The specific ID allowed to control the bot
COMMAND_CHAT_ID = os.getenv("COMMAND_CHAT_ID")

def send_telegram_msg(chat_id, text):
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    params = {"chat_id": chat_id, "text": text, "parse_mode": "HTML"}
    requests.post(url, params=params)

def update_github_file(new_content_str, message):
    file_url = f"https://api.github.com/repos/{REPO_NAME}/contents/{TICKER_FILE}"
    headers = {"Authorization": f"Bearer {GITHUB_TOKEN}"}
    res = requests.get(file_url, headers=headers)
    sha = res.json().get('sha') if res.status_code == 200 else None
    payload = {
        "message": message,
        "content": base64.b64encode(new_content_str.encode()).decode(),
        "sha": sha
    }
    requests.put(file_url, headers=headers, json=payload)

def handle_commands():
    url = f"https://api.telegram.org/bot{TOKEN}/getUpdates"
    response = requests.get(url, params={"limit": 10, "timeout": 1}).json()
    updates = response.get("result", [])
    
    last_id = 0
    for update in updates:
        last_id = update.get("update_id")
        msg_data = update.get("message") or update.get("channel_post")
        if not msg_data: continue
        
        # --- THE SECURITY CHECK ---
        current_chat_id = str(msg_data.get("chat", {}).get("id"))
        if current_chat_id != COMMAND_CHAT_ID:
            print(f"Ignored message from unauthorized ID: {current_chat_id}")
            continue

        text = msg_data.get("text", "").upper()
        
        # Load local tickers
        if os.path.exists(TICKER_FILE):
            with open(TICKER_FILE, "r") as f:
                current = [t.strip().upper() for t in f.read().splitlines() if t.strip()]
        else:
            current = []

        if text.startswith("/ADD "):
            ticker = text.replace("/ADD ", "").strip()
            if ticker not in current:
                current.append(ticker)
                update_github_file("\n".join(current), f"Add {ticker}")
                send_telegram_msg(COMMAND_CHAT_ID, f"✅ Added <b>{ticker}</b>")
        
        elif text.startswith("/REMOVE "):
            ticker = text.replace("/REMOVE ", "").strip()
            if ticker in current:
                current.remove(ticker)
                update_github_file("\n".join(current), f"Remove {ticker}")
                send_telegram_msg(COMMAND_CHAT_ID, f"✅ Removed <b>{ticker}</b>")
        
        elif text == "/LIST":
            msg = "📋 <b>Watchlist:</b>\n" + "\n".join([f"• {t}" for t in current])
            send_telegram_msg(COMMAND_CHAT_ID, msg)

    if last_id > 0:
        requests.get(url, params={"offset": last_id + 1})

if __name__ == "__main__":
    handle_commands()
