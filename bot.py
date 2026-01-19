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
    if not tickers: return

    url = "https://www.investegate.co.uk/announcements/rns/latest/"
    # Use a more "human" user-agent to avoid being blocked
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept-Language': 'en-GB,en;q=0.9'
    }

    try:
        response = requests.get(url, headers=headers, timeout=15)
        
        # DEBUG: If this prints 403 or 404, you are being blocked
        print(f"Status Code: {response.status_code}")
        
        soup = BeautifulSoup(response.text, 'html.parser')
        print(f"DEBUG: Found {len(soup.find_all('a'))} links on page.")
        
        # 1. NEW STRATEGY: Find all links first
        # News on Investegate is almost always inside an <a> tag
        links = soup.find_all('a', href=True)
        news_found = 0

        for link in links:
            text = link.get_text().upper()
            
            for ticker in tickers:
                # Check if the ticker (VOD) or (VOD.) is in the link text
                if f"({ticker}" in text:
                    title = text.strip()
                    path = link['href']
                    full_link = f"https://www.investegate.co.uk{path}" if path.startswith('/') else path
                    
                    rns_id = hashlib.md5(f"{ticker}{title}".encode()).hexdigest()

                    # Load/Check history as before...
                    if rns_id not in last_seen:
                        msg = f"🔔 <b>New RNS: {ticker}</b>\n{title}\n\n🔗 <a href='{full_link}'>Read Full Release</a>"
                        send_telegram_msg(msg)
                        # (Save to file logic here)
                        news_found += 1
        
        print(f"Scan complete. Found {news_found} items.")

    except Exception as e:
        print(f"Error: {e}")

# ... (Keep your sync_commands() and add_ticker_to_github() from the previous post) ...

if __name__ == "__main__":
    # sync_commands() # Uncomment if your PAT/Telegram-Add logic is fixed
    check_rns()
