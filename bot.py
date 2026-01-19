import requests
from bs4 import BeautifulSoup
import os
import base64
import hashlib
from datetime import datetime
from urllib.parse import urljoin
import re

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
        send_telegram_msg("❌ Error: GH_PAT is missing.")
        return

    file_url = f"https://api.github.com/repos/{REPO_NAME}/contents/{TICKER_FILE}"
    headers = {
        "Authorization": f"Bearer {GITHUB_TOKEN}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28"
    }
    
    res = requests.get(file_url, headers=headers)
    if res.status_code != 200:
        send_telegram_msg(f"❌ Error {res.status_code}: Couldn't reach GitHub.")
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
    
    requests.put(file_url, headers=headers, json=payload)
    send_telegram_msg(f"✅ Added <b>{ticker}</b>.")

def remove_ticker_from_github(ticker_to_remove):
    file_url = f"https://api.github.com/repos/{REPO_NAME}/contents/{TICKER_FILE}"
    headers = {"Authorization": f"Bearer {GITHUB_TOKEN}"}
    
    res = requests.get(file_url, headers=headers)
    if res.status_code != 200: return

    data = res.json()
    sha = data.get('sha')
    current_tickers = base64.b64decode(data['content']).decode('utf-8').splitlines()
    
    updated_tickers = [t.strip().upper() for t in current_tickers if t.strip().upper() != ticker_to_remove]
    
    if len(updated_tickers) == len(current_tickers):
        send_telegram_msg(f"ℹ️ {ticker_to_remove} not found.")
        return

    payload = {
        "message": f"Remove {ticker_to_remove} via Telegram",
        "content": base64.b64encode("\n".join(updated_tickers).encode('utf-8')).decode('utf-8'),
        "sha": sha
    }
    requests.put(file_url, headers=headers, json=payload)
    send_telegram_msg(f"✅ Removed <b>{ticker_to_remove}</b>.")

def sync_commands():
    url = f"https://api.telegram.org/bot{TOKEN}/getUpdates"
    try:
        response = requests.get(url, params={"limit": 10, "timeout": 1}).json()
        updates = response.get("result", [])
        last_id = 0
        for update in updates:
            last_id = update.get("update_id")
            msg_data = update.get("message") or update.get("channel_post")
            if msg_data:
                text = msg_data.get("text", "")
                if text.startswith("/add "):
                    add_ticker_to_github(text.replace("/add ", "").strip().upper())
                elif text.startswith("/remove "):
                    remove_ticker_from_github(text.replace("/remove ", "").strip().upper())
                elif text == "/list":
                    tickers = load_tickers()
                    msg = "📋 <b>Watchlist:</b>\n" + "\n".join([f"• {t}" for t in tickers])
                    send_telegram_msg(msg)
        if last_id > 0:
            requests.get(url, params={"offset": last_id + 1})
    except Exception as e:
        print(f"Sync Error: {e}")

# --- RNS SCRAPER ---
def check_rns():
    tickers = load_tickers()
    if not tickers: return

    base_url = "https://www.investegate.co.uk"
    today_url = urljoin(base_url, "today-announcements/?perPage=300")
    headers = {'User-Agent': 'Mozilla/5.0'}

    if os.path.exists(FILE_NAME):
        with open(FILE_NAME, "r") as f:
            last_seen = set(f.read().splitlines())
    else:
        last_seen = set()

    try:
        response = requests.get(today_url, headers=headers, timeout=15)
        soup = BeautifulSoup(response.text, 'html.parser')
        table = soup.find('table')
        if not table: return
        
        rows = table.find_all('tr')
        news_found = 0

        for row in rows:
            cols = row.find_all('td')
            if len(cols) < 4: continue
            
            company_text = cols[2].get_text().upper()
            announcement_cell = cols[3]
            
            for ticker in tickers:
                # regex word boundary fix
                if re.search(rf'\b{re.escape(ticker)}\b', company_text):
                    link_tag = announcement_cell.find('a', href=True)
                    if not link_tag: continue
                        
                    title = link_tag.get_text().strip()
                    full_link = urljoin(base_url, link_tag['href'])
                    rns_id = hashlib.md5(f"{ticker}{title}".encode()).hexdigest()

                    if rns_id not in last_seen:
                        msg = f"🔔 <b>New RNS: {ticker}</b>\n{title}\n\n🔗 <a href='{full_link}'>Read Full Release</a>"
                        send_telegram_msg(msg)
                        with open(FILE_NAME, "a") as f:
                            f.write(rns_id + "\n")
                        last_seen.add(rns_id)
                        news_found += 1
        
        print(f"Scan complete. Found {news_found} new items.")
    except Exception as e:
        print(f"Scraper Error: {e}")

if __name__ == "__main__":
    sync_commands() 
    check_rns()
