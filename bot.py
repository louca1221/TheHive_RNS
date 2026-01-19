import requests
from bs4 import BeautifulSoup
import os
import hashlib
import re
from urllib.parse import urljoin

# --- CONFIGURATION ---
TOKEN = os.getenv("TELEGRAM_TOKEN")
CHAT_ID_STR = os.getenv("TELEGRAM_CHAT_ID", "")
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

def check_rns():
    tickers = load_tickers()
    if not tickers:
        print("No tickers in watchlist.")
        return

    base_url = "https://www.investegate.co.uk"
    today_url = urljoin(base_url, "/today-announcements/?perPage=300")
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
            if len(cols) < 4:
                continue
            
            company_raw = cols[2].get_text()
            announcement_cell = cols[3]
            
            for ticker in tickers:
                # Precise matching for (TICKER)
                if re.search(rf'\({re.escape(ticker)}\)', company_raw.upper()):
                    link_tag = announcement_cell.find('a', href=True)
                    if not link_tag:
                        continue
                        
                    title = link_tag.get_text().strip()
                    full_link = urljoin(base_url, link_tag['href'])
                    rns_id = hashlib.md5(f"{ticker}{title}".encode()).hexdigest()

                    if rns_id not in last_seen:
                        clean_ticker = ticker.strip()
                        # Clean company name: remove newlines and everything after the bracket
                        clean_company = company_raw.split('(')[0].replace('\n', ' ').strip()
                        clean_company = re.sub(' +', ' ', clean_company)
                        
                        msg = (f"📰 <b>#{clean_ticker} - {clean_company}</b>\n"
                               f"{title}\n\n"
                               f"🔗 <a href='{full_link}'>Read Full Release</a>")
                        
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
