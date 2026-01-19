import requests
from bs4 import BeautifulSoup
import os
import base64
import hashlib

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

def check_rns():
    tickers = load_tickers()
    if not tickers:
        print("No tickers found.")
        return

    # Investegate Latest RNS Page
    url = "https://www.investegate.co.uk/announcements/rns/latest/"
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}

    # Load history
    if os.path.exists(FILE_NAME):
        with open(FILE_NAME, "r") as f:
            last_seen = set(f.read().splitlines())
    else:
        last_seen = set()

    try:
        response = requests.get(url, headers=headers, timeout=15)
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Investegate usually stores news in a table. We search for rows.
        # Note: We look for the ticker string (e.g., "(VOD)") inside the row text
        news_found = 0
        
        # Find all table rows or news containers
        rows = soup.find_all('tr') # Search standard table rows
        
        for row in rows:
            row_text = row.get_text()
            
            for ticker in tickers:
                # Pattern match for Ticker in brackets like (VOD)
                if f"({ticker})" in row_text:
                    link_tag = row.find('a', href=True)
                    if not link_tag: continue
                    
                    title = link_tag.get_text().strip()
                    path = link_tag['href']
                    full_link = f"https://www.investegate.co.uk{path}"
                    
                    # Create a unique ID for this news item
                    rns_id = hashlib.md5(f"{ticker}{title}".encode()).hexdigest()

                    if rns_id not in last_seen:
                        msg = (f"🔔 <b>New RNS: {ticker}</b>\n"
                               f"{title}\n\n"
                               f"🔗 <a href='{full_link}'>Read Full Release</a>")
                        send_telegram_msg(msg)
                        
                        with open(FILE_NAME, "a") as f:
                            f.write(rns_id + "\n")
                        last_seen.add(rns_id)
                        news_found += 1
        
        print(f"Scan complete. Found {news_found} new items.")

    except Exception as e:
        print(f"BeautifulSoup Error: {e}")

# ... (Keep your sync_commands() and add_ticker_to_github() from the previous post) ...

if __name__ == "__main__":
    # sync_commands() # Uncomment if your PAT/Telegram-Add logic is fixed
    check_rns()
