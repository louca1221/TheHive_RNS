import requests
from bs4 import BeautifulSoup
import os

TOKEN = os.getenv("TELEGRAM_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
TICKERS = ["VOD", "BP", "AZN"] # Update with your list
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
    requests.post(url, params=params)

def check_rns():
    headers = {'User-Agent': 'Mozilla/5.0'}
    last_seen = get_last_seen_ids()
    
    for ticker in TICKERS:
        url = f"https://www.londonstockexchange.com/stock/{ticker}/company-page"
        try:
            response = requests.get(url, headers=headers, timeout=15)
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Find the News Section (LSE usually uses 'news-item' or specific ID)
            # This selects the first news headline link
            news_link = soup.select_one('news-item a') 
            
            if news_link:
                title = news_link.text.strip()
                link = "https://www.londonstockexchange.com" + news_link['href']
                rns_id = news_link['href'].split('/')[-1] # Unique ID from URL

                if rns_id not in last_seen:
                    message = f"<b>New RNS: {ticker}</b>\n{title}\n<a href='{link}'>Read Full Release</a>"
                    send_telegram_msg(message)
                    save_new_id(rns_id)
                    print(f"Alert sent for {ticker}")
        except Exception as e:
            print(f"Error scraping {ticker}: {e}")

if __name__ == "__main__":
    check_rns()
