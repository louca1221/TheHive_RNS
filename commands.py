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
AUTHORIZED_IDS = [id.strip() for id in os.getenv("COMMAND_CHAT_ID", "").split(",") if id.strip()]

def send_telegram_msg(chat_id, text):
    """Sends a message to a specific chat_id."""
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    params = {"chat_id": chat_id, "text": text, "parse_mode": "HTML"}
    try:
        res = requests.post(url, params=params, timeout=10)
        if res.status_code != 200:
            print(f"Error sending to {chat_id}: {res.text}")
    except Exception as e:
        print(f"Connection error: {e}")

def update_github_file(new_content_str, message):
    file_url = f"https://api.github.com/repos/{REPO_NAME}/contents/{TICKER_FILE}"
    headers = {
        "Authorization": f"Bearer {GITHUB_TOKEN}",
        "Accept": "application/vnd.github+json"
    }
    
    # Get the current file to get the SHA
    res = requests.get(file_url, headers=headers)
    sha = res.json().get('sha') if res.status_code == 200 else None

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
            
            # Identify who sent the message
            current_chat_id = str(msg_data.get("chat", {}).get("id"))
            
            # SECURITY CHECK: Is this sender in the AUTHORIZED_IDS list?
            if current_chat_id not in AUTHORIZED_IDS:
                print(f"Unauthorized access attempt from: {current_chat_id}")
                continue

            text = msg_data.get("text", "").strip()
            
            # Load current tickers
            if os.path.exists(TICKER_FILE):
                with open(TICKER_FILE, "r") as f:
                    current_tickers = [t.strip().upper() for t in f.read().splitlines() if t.strip()]
            else:
                current_tickers = []

            # Command: /ADD
            if text.upper().startswith("/ADD "):
                raw_input = text[5:].strip().upper()
                new_tickers = [t.strip() for t in raw_input.split(",") if t.strip()]
                added = [t for t in new_tickers if t not in current_tickers]
                
                if added:
                    current_tickers.extend(added)
                    status = update_github_file("\n".join(current_tickers), f"Add {added}")
                    if status in [200, 201]:
                        send_telegram_msg(current_chat_id, f"✅ Added: <b>{', '.join(added)}</b>")
                else:
                    send_telegram_msg(current_chat_id, "ℹ️ No new tickers added.")

            # Command: /REMOVE
            elif text.upper().startswith("/REMOVE "):
                ticker = text[8:].strip().upper()
                if ticker in current_tickers:
                    current_tickers.remove(ticker)
                    update_github_file("\n".join(current_tickers), f"Remove {ticker}")
                    send_telegram_msg(current_chat_id, f"✅ Removed: <b>{ticker}</b>")
                else:
                    send_telegram_msg(current_chat_id, f"ℹ️ {ticker} not found.")

            # Command: /LIST
            elif text.upper() == "/LIST":
                msg = "📋 <b>Watchlist:</b>\n" + "\n".join([f"• {t}" for t in sorted(current_tickers)])
                send_telegram_msg(current_chat_id, msg)

        if last_id > 0:
            requests.get(url, params={"offset": last_id + 1})

    except Exception as e:
        print(f"Command Error: {e}")

if __name__ == "__main__":
    handle_commands()
