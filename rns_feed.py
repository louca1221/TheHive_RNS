import requests
from bs4 import BeautifulSoup
import os
import hashlib
import re
from urllib.parse import urljoin

# --- CONFIGURATION ---
TOKEN = os.getenv("rnsfeedtoken")
NOTIFICATION_CHAT_ID = os.getenv("rnsfeedchatid")
FILE_NAME = "rnsfeedlastrns.txt"
TICKER_FILE = "tickers.txt"

def load_tickers():
    if os.path.exists(TICKER_FILE):
        with open(TICKER_FILE, "r") as f:
            lines = f.read().splitlines()
            return [line.strip().upper() for line in lines if line.strip()]
    return []

def send_telegram_msg(text):
    if not NOTIFICATION_CHAT_ID:
        print("Error: NOTIFICATION_CHAT_ID not set.")
        return
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    params = {"chat_id": NOTIFICATION_CHAT_ID, "text": text, "parse_mode": "HTML"}
    try:
        res = requests.post(url, params=params, timeout=10)
        if res.status_code != 200:
            print(f"Telegram API Error: {res.text}")
    except Exception as e:
        print(f"Telegram connection error: {e}")

def check_rns():
    tickers = load_tickers()
    if not tickers:
        print("Watchlist is empty. No tickers to scan.")
        return
    
    print(f"Starting scan for tickers: {tickers}")

    base_url = "https://www.investegate.co.uk"
    # Added perPage=300 to ensure we see the whole morning's news
    today_url = urljoin(base_url, "sector/basic-resources?perPage=300")
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'}

    if os.path.exists(FILE_NAME):
        with open(FILE_NAME, "r") as f:
            last_seen = set(f.read().splitlines())
    else:
        last_seen = set()

    try:
        response = requests.get(today_url, headers=headers, timeout=15)
        soup = BeautifulSoup(response.text, 'html.parser')
        table = soup.find('table')
        if not table:
            print("Could not find the announcements table on Investegate.")
            return
        
        rows = table.find_all('tr')
        news_found = 0

        for row in rows:
            cols = row.find_all('td')
            if len(cols) < 4:
                continue
            
            # Investegate Table: Col 2 is Company (Ticker), Col 3 is Announcement Title
            company_raw = cols[2].get_text().upper()
            announcement_cell = cols[3]
            
            for ticker in tickers:
                # We search for the ticker inside parentheses, e.g., (VOD)
                if re.search(rf'\({re.escape(ticker)}\)', company_raw):
                    link_tag = announcement_cell.find('a', href=True)
                    if not link_tag:
                        continue
                        
                    title = link_tag.get_text().strip()
                    full_link = urljoin(base_url, link_tag['href'])
                    
                    # Create unique ID for this specific RNS
                    rns_id = hashlib.md5(f"{ticker}{title}".encode()).hexdigest()

                    if rns_id not in last_seen:
                        clean_company = company_raw.split('(')[0].replace('\n', ' ').strip()
                        clean_company = re.sub(' +', ' ', clean_company)
                        
                        msg = (f"📰 <b>#{ticker} - {clean_company}</b>\n"
                               f"{title}\n\n"
                               f"🔗 <a href='{full_link}'>Read Full Release</a>")
                        
                        print(f"Match found! Sending alert for {ticker}")
                        send_telegram_msg(msg)
                        
                        with open(FILE_NAME, "a") as f:
                            f.write(rns_id + "\n")
                        last_seen.add(rns_id)
                        news_found += 1
        
        print(f"Scan complete. Found {news_found} new items.")
    except Exception as e:
        print(f"Scraper Error: {e}")

if __name__ == "__main__":
    check_rns()
