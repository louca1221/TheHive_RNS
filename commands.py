import requests
import os
import base64
import re

# --- CONFIGURATION ---
TOKEN = os.getenv("TELEGRAM_TOKEN")
GITHUB_TOKEN = os.getenv("GH_PAT")
REPO_NAME = "louca1221/TheHive_RNS"
TICKER_FILE = "tickers.txt"

# Pull secret and split by comma to handle multiple IDs (e.g. "123,456")
AUTHORIZED_IDS = os.getenv("COMMAND_CHAT_ID", "").split(",")

def send_telegram_msg(chat_id, text):
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    params = {"chat_id": chat_id, "text": text, "parse_mode": "HTML"}
    try:
        requests.post(url, params=params, timeout=10)
    except Exception as e:
        print(f"Telegram error: {e}")

def update_github_file(new_content_str, message):
    file_url = f"https://api.github.com/repos/{REPO_NAME}/contents/{TICKER_FILE}"
    headers = {
        "Authorization": f"Bearer {GITHUB_TOKEN}",
        "Accept": "application/vnd.github+json"
    }
    
    # 1. Get the current file to get the SHA (required for updates)
    res = requests.get(file_url, headers=headers)
    sha = res.json().get('sha') if res.status_code == 200 else None

    # 2. Prepare the update
    payload = {
        "message": message,
        "content": base64.b64encode(new_content_str.encode('utf-8')).decode('utf-8'),
        "sha": sha
    }
    
    put_res = requests.put(file_url, headers=headers, json=payload)
    return put_res.status_code

def handle_commands():
    if not TOKEN:
        print("Error: TELEGRAM_TOKEN not found.")
        return

    url = f"https://api.telegram.org/bot{TOKEN}/getUpdates"
    try:
        response = requests.get(url, params={"limit": 10, "timeout": 1}).json()
        updates = response.get("result", [])
        
        last_id = 0
        for update in updates:
            last_id = update.get("update_id")
            msg_data = update.get("message") or update.get("channel_post")
            if not msg_data: continue
            
            # Security Check
            current_chat_id = str(msg_data.get("chat", {}).get("id"))
            if current_chat_id not in AUTHORIZED_IDS:
                print(f"Ignored message from unauthorized ID: {current_chat_id}")
                continue

            text = msg_data.get("text", "").strip()
            
            # Load current tickers from GitHub/Local
            if os.path.exists(TICKER_FILE):
                with open(TICKER_FILE, "r") as f:
                    current_tickers = [t.strip().upper() for t in f.read().splitlines() if t.strip()]
            else:
                current_tickers = []

            # Command: /ADD TICKER
            if text.upper().startswith("/ADD "):
                ticker = text[5:].strip().upper()
                if ticker and ticker not in current_tickers:
                    current_tickers.append(ticker)
                    status = update_github_file("\n".join(current_tickers), f"Add {ticker} via Telegram")
                    if status in [200, 201]:
                        send_telegram_msg(current_chat_id, f"✅ Added <b>{ticker}</b> to watchlist.")
                    else:
                        send_telegram_msg(current_chat_id, f"❌ GitHub Error: {status}")
                else:
                    send_telegram_msg(current_chat_id, f"ℹ️ {ticker} is already in list or invalid.")

            # Command: /REMOVE TICKER
            elif text.upper().startswith("/REMOVE "):
                ticker = text[8:].strip().upper()
                if ticker in current_tickers:
                    current_tickers.remove(ticker)
                    status = update_github_file("\n".join(current_tickers), f"Remove {ticker} via Telegram")
                    if status in [200, 201]:
                        send_telegram_msg(current_chat_id, f"✅ Removed <b>{ticker}</b> from watchlist.")
                else:
                    send_telegram_msg(current_chat_id, f"ℹ️ {ticker} not found in list.")

            # Command: /LIST
            elif text.upper() == "/LIST":
                if current_tickers:
                    msg = "📋 <b>Current Watchlist:</b>\n\n" + "\n".join([f"• {t}" for t in sorted(current_tickers)])
                else:
                    msg = "📋 Watchlist is empty."
                send_telegram_msg(current_chat_id, msg)

        # Confirm we have seen these messages so they don't repeat
        if last_id > 0:
            requests.get(url, params={"offset": last_id + 1})

    except Exception as e:
        print(f"Command Error: {e}")

if __name__ == "__main__":
    handle_commands()
