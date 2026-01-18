import requests
import os
import base64
from datetime import datetime

# --- CONFIGURATION ---
TOKEN = os.getenv("TELEGRAM_TOKEN")
CHAT_ID_STR = os.getenv("TELEGRAM_CHAT_ID", "")
GITHUB_TOKEN = os.getenv("GH_PAT")
REPO_NAME = "louca1221/TheHive_RNS"
FILE_NAME = "last_rns_ids.txt"
TICKER_FILE = "tickers.txt"

def load_tickers():
    if os.path.exists(TICKER_FILE):
        with open(TICKER_FILE, "r") as f:
            return [line.strip().upper() for line in f if line.strip()]
    return []

def send_telegram_msg(text):
    chat_ids = CHAT_ID_STR.split(",") if CHAT_ID_STR else []
    for chat_id in chat_ids:
        url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
        params = {"chat_id": chat_id.strip(), "text": text, "parse_mode": "HTML"}
        requests.post(url, params=params)

# --- GITHUB API SYNC ---
def add_ticker_to_github(ticker):
    file_url = f"https://api.github.com/repos/{REPO_NAME}/contents/{TICKER_FILE}"
    headers = {"Authorization": f"token {GITHUB_TOKEN}"}
    
    res = requests.get(file_url, headers=headers).json()
    sha = res.get('sha')
    current_content = base64.b64decode(res['content']).decode('utf-8') if sha else ""
    
    if ticker not in current_content.split():
        new_content = current_content.strip() + f"\n{ticker}"
        payload = {
            "message": f"Add {ticker} via Telegram",
            "content": base64.b64encode(new_content.encode('utf-8')).decode('utf-8'),
            "sha": sha
        }
        requests.put(file_url, headers=headers, json=payload)
        send_telegram_msg(f"✅ Added <b>{ticker}</b> to watchlist.")

def sync_commands():
    url = f"https://api.telegram.org/bot{TOKEN}/getUpdates"
    try:
        updates = requests.get(url).json().get("result", [])
        for update in updates:
            text = update.get("message", {}).get("text", "")
            if text.startswith("/add "):
                ticker = text.replace("/add ", "").strip().upper()
                add_ticker_to_github(ticker)
    except Exception as e:
        print(f"Sync Error: {e}")

# --- MAIN RNS LOGIC ---
def check_rns():
    tickers = load_tickers()
    if not tickers:
        print("No tickers found.")
        return

    headers = {'User-Agent': 'Mozilla/5.0', 'Accept': 'application/json'}
    url = "https://api.londonstockexchange.com/api/v1/pages?path=news&parameters=categories%3Drns"
    
    if os.path.exists(FILE_NAME):
        with open(FILE_NAME, "r") as f:
            last_seen = set(f.read().splitlines())
    else:
        last_seen = set()

    try:
        response = requests.get(url, headers=headers, timeout=15)
        data = response.json()
        components = data.get('components', [])
        news_items = next((c.get('content', []) for c in components if c.get('type') == 'news-list'), [])

        for item in news_items:
            tidm = item.get('tidm', '').upper()
            rns_id = item.get('newsId', '')
            title = item.get('title', '')
            link = f"https://www.londonstockexchange.com/news-article/RNS/{item.get('path', '')}"

            if tidm in tickers and rns_id not in last_seen:
                msg = f"🔔 <b>New RNS: {tidm}</b>\n{title}\n\n🔗 <a href='{link}'>Read Full Release</a>"
                send_telegram_msg(msg)
                with open(FILE_NAME, "a") as f:
                    f.write(rns_id + "\n")
                last_seen.add(rns_id)
    except Exception as e:
        print(f"RNS Error: {e}")

if __name__ == "__main__":
    sync_commands() # Update tickers first
    check_rns()     # Then scan for news
