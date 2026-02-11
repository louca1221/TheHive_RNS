import requests
from bs4 import BeautifulSoup
import os
import hashlib
import re
from urllib.parse import urljoin
import time
import json

# --- CONFIGURATION ---
TOKEN = os.getenv("TELEGRAM_TOKEN")
NOTIFICATION_CHAT_ID = os.getenv("NOTIFICATION_CHAT_ID")
FILE_NAME = "last_rns_ids.txt"
TICKER_FILE = "tickers.txt"

def load_tickers():
    if os.path.exists(TICKER_FILE):
        with open(TICKER_FILE, "r") as f:
            lines = f.read().splitlines()
            return [line.strip().upper() for line in lines if line.strip()]
    return []

def send_telegram_msg(text, rns_url=None):
    if not NOTIFICATION_CHAT_ID:
        print("Error: NOTIFICATION_CHAT_ID not set.")
        return
    
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"

    # Define options as a dictionary
    preview_options = {
        "url": rns_url,
        "is_disabled": False,
        "prefer_large_media": True
    }

    # Send as JSON body instead of URL params
    payload = {
        "chat_id": NOTIFICATION_CHAT_ID,
        "text": text,
        "parse_mode": "HTML",
        "link_preview_options": preview_options
    }
    
    try:
        # Changed from 'params=payload' to 'json=payload'
        res = requests.post(url, json=payload, timeout=10)
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
    today_url = urljoin(base_url, "/today-announcements/?perPage=300")
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'}

    last_seen_hashes = set()
    if os.path.exists(FILE_NAME):
        with open(FILE_NAME, "r") as f:
            for line in f:
                parts = line.strip().split(" | ")
                if parts:
                    last_seen_hashes.add(parts[-1])

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
            
            rns_time = cols[0].get_text().strip()
            company_raw = cols[2].get_text().upper()
            announcement_cell = cols[3]
            
            for ticker in tickers:
                if re.search(rf'\({re.escape(ticker)}\)', company_raw):
                    link_tag = announcement_cell.find('a', href=True)
                    if not link_tag:
                        continue
                        
                    title = link_tag.get_text().strip()
                    full_link = urljoin(base_url, link_tag['href'])
                    
                    unique_string = f"{rns_time}_{ticker}_{title}_{full_link}"
                    rns_id = hashlib.md5(unique_string.encode()).hexdigest()

                    if rns_id not in last_seen_hashes:
                        clean_company = company_raw.split('(')[0].replace('\n', ' ').strip()
                        clean_company = re.sub(' +', ' ', clean_company)
                        
                        print(f"[{rns_time}] MATCH: {ticker} | Hash: {rns_id[:12]}")
                        
                        msg = (f"🕒 <b>{rns_time}</b>\n"
                               f"📰 <b>#{ticker} - {clean_company}</b>\n"
                               f"{title}\n\n"
                               f"🔗 <a href='{full_link}'>Read Full Release</a>")
                        
                        # Pass the link to the sender function
                        send_telegram_msg(msg, rns_url=full_link)
                        
                        # Anti-Flood Delay
                        time.sleep(1)
                        
                        # LOGGING TO FILE
                        log_entry = f"{rns_time} | {ticker} | {rns_id}"
                        with open(FILE_NAME, "a") as f:
                            f.write(log_entry + "\n")
                        
                        last_seen_hashes.add(rns_id)
                        news_found += 1
                    
                    break 
        
        print(f"Scan complete. Found {news_found} new items.")
    except Exception as e:
        print(f"Scraper Error: {e}")

if __name__ == "__main__":
    check_rns()
