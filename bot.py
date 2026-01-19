import requests
from bs4 import BeautifulSoup
import os
import base64
import hashlib
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
        try:
            requests.post(url, params=params, timeout=10)
        except Exception as e:
            print(f"Telegram error: {e}")

# --- GITHUB API SYNC ---
def add_ticker_to_github(ticker):
    if not GITHUB_TOKEN:
        send_telegram_msg("❌ Error: GH_PAT is missing. Check your YAML!")
        return

    file_url = f"https://api.github.com/repos/{REPO_NAME}/contents/{TICKER_FILE}"
    headers = {
        "Authorization": f"Bearer {GITHUB_TOKEN}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28"
    }
    
    res = requests.get(file_url, headers=headers)
    if res.status_code != 200:
        send_telegram_msg(f"❌ Error {res.status_code}: Couldn't reach GitHub repo.")
        return

    data = res.json()
    sha = data.get('sha')
    current_content = base64.b64decode(data['content']).decode('utf-8')
    
    if ticker in current_content.split():
        send_telegram_msg(f"ℹ️ {ticker} is already in your watchlist.")
        return

    new_content = current_content.strip() + f"\n{ticker}"
    payload = {
        "message": f"Add {ticker} via Telegram",
        "content": base64.b64encode(new_content.encode('utf-8')).decode('utf-8'),
        "sha": sha
    }
    
    put_res = requests.put(file_url, headers=headers, json=payload)
    if put_res.status_code in [200, 201]:
        send_telegram_msg(f"✅ Successfully added <b>{ticker}</b> to watchlist.")
    else:
        send_telegram_msg(f"❌ GitHub Error: {put_res.status_code}")

def sync_commands():
    url = f"https://api.telegram.org/bot{TOKEN}/getUpdates"
    params = {"limit": 10, "timeout": 1, "allowed_updates": ["message", "channel_post"]}
    
    try:
        response = requests.get(url, params=params).json()
        updates = response.get("result", [])
        
        last_id = 0
        for update in updates:
            last_id = update.get("update_id")
            msg_data = update.get("message") or update.get("channel_post")
            
            if msg_data:
                text = msg_data.get("text", "")
                if text.startswith("/add "):
                    ticker = text.replace("/add ", "").strip().upper()
                    add_ticker_to_github(ticker)
                elif text == "/list":
                    tickers = load_tickers()
                    msg = "📋 <b>Watchlist:</b>\n" + "\n".join([f"• {t}" for t in tickers])
                    send_telegram_msg(msg)

        if last_id > 0:
            # This 'offset' clears the Telegram queue so commands don't loop
            requests.get(url, params={"offset": last_id + 1})
            
    except Exception as e:
        print(f"Sync Error: {e}")

# --- RNS SCRAPER ---
def check_rns():
    tickers = load_tickers()
    if not tickers:
        print("No tickers found.")
        return

    # Using the 'Today' URL as requested
    url = "https://www.investegate.co.uk/today-announcements/"
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    }

    if os.path.exists(FILE_NAME):
        with open(FILE_NAME, "r") as f:
            last_seen = set(f.read().splitlines())
    else:
        last_seen = set()

    try:
        response = requests.get(url, headers=headers, timeout=15)
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # In the 'Today' table, each announcement is a row (tr)
        rows = soup.find_all('tr')
        news_found = 0

        for row in rows:
            row_text = row.get_text().upper()
            
            for ticker in tickers:
                # We search for the ticker anywhere in the row text
                # Investegate often shows tickers as 'VOD' or 'VOD.'
                if ticker in row_text:
                    link_tag = row.find('a', href=True)
                    if not link_tag:
                        continue
                        
                    title = link_tag.get_text().strip()
                    path = link_tag['href']
                    full_link = f"https://www.investegate.co.uk{path}"
                    
                    # Create unique ID based on ticker and title
                    rns_id = hashlib.md5(f"{ticker}{title}".encode()).hexdigest()

                    if rns_id not in last_seen:
                        msg = (f"🔔 <b>Today's RNS: {ticker}</b>\n"
                               f"{title}\n\n"
                               f"🔗 <a href='{full_link}'>Read Full Release</a>")
                        send_telegram_msg(msg)
                        
                        with open(FILE_NAME, "a") as f:
                            f.write(rns_id + "\n")
                        last_seen.add(rns_id)
                        news_found += 1
        
        print(f"Scan complete. Found {news_found} new items on Today's page.")

    except Exception as e:
        print(f"Scraper Error: {e}")

if __name__ == "__main__":
    print(f"DEBUG: Token length is {len(GITHUB_TOKEN) if GITHUB_TOKEN else 0}")
    sync_commands() 
    check_rns()
