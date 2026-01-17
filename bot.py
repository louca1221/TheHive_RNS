import requests
from bs4 import BeautifulSoup
import os

TOKEN = os.getenv("TELEGRAM_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
TICKERS = ["VOD", "BP", "GSK"] 
FILE_NAME = "last_rns_ids.txt"

def get_last_seen_ids():
    if os.path.exists(FILE_NAME):
        with open(FILE_NAME, "r") as f:
            return set(f.read().splitlines())
    return set()

def save_new_id(rns_id):
    with open(FILE_NAME, "a") as f:
        f.write(rns_id + "\n")

def send_telegram_msg(text):
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    params = {"chat_id": CHAT_ID, "text": text, "parse_mode": "HTML"}
    try:
        requests.post(url, params=params, timeout=10)
    except Exception as e:
        print(f"Telegram error: {e}")

def check_rns():
    headers = {'User-Agent': 'Mozilla/5.0'}
    last_seen = get_last_seen_ids()
    
    for ticker in TICKERS:
        print(f"Checking {ticker}...")
        # Using Investegate as it's more scraper-friendly
        url = f"https://www.investegate.co.uk/search-results?q={ticker}"
        
        try:
            response = requests.get(url, headers=headers, timeout=15)
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Find the first news link
            # Note: Selectors may need adjustment based on site layout
            news_link = soup.select_one('.search-result-title a')
            
            if news_link:
                title = news_link.get_text(strip=True)
                link = "https://www.investegate.co.uk" + news_link['href']
                # Unique ID from the URL path
                rns_id = news_link['href'].split('/')[-1]

                if rns_id not in last_seen:
                    message = f"🔔 <b>New RNS: {ticker}</b>\n{title}\n\n<a href='{link}'>Read Full Release</a>"
                    send_telegram_msg(message)
                    save_new_id(rns_id)
                    print(f"Alert sent for {ticker}")
            else:
                print(f"No news found for {ticker}")
                
        except Exception as e:
            print(f"Error processing {ticker}: {e}")

if __name__ == "__main__":
    check_rns()
