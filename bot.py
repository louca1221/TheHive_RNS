import requests
from bs4 import BeautifulSoup
import os

TOKEN = os.getenv("TELEGRAM_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
TICKERS = ["VOD", "BP", "SGE", "AZN"] 
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
    r = requests.post(url, params=params)
    print(f"Telegram status: {r.status_code}")

def check_rns():
    headers = {'User-Agent': 'Mozilla/5.0'}
    last_seen = get_last_seen_ids()
    
    for ticker in TICKERS:
        print(f"Checking RSS for {ticker}...")
        url = f"https://www.investegate.co.uk/rss/company/{ticker}"
        
        try:
            response = requests.get(url, headers=headers, timeout=15)
            # Using lxml-xml to parse the RSS feed correctly
            soup = BeautifulSoup(response.content, 'lxml-xml')
            items = soup.find_all('item')
            
            if items:
                latest = items[0]
                title = latest.title.text.strip()
                link = latest.link.text.strip()
                rns_id = latest.guid.text.strip() if latest.guid else link

                if rns_id not in last_seen:
                    message = (
                        f"🔔 <b>New RNS: {ticker}</b>\n\n"
                        f"{title}\n\n"
                        f"🔗 <a href='{link}'>Read Full Release</a>"
                    )
                    send_telegram_msg(message)
                    save_new_id(rns_id)
                    print(f"✅ ALERT SENT: {ticker} - {title}")
                else:
                    print(f"ℹ️ Already seen {ticker}.")
            else:
                print(f"⚠️ No RSS items found for {ticker}.")
                
        except Exception as e:
            print(f"❌ Error checking {ticker}: {e}")

if __name__ == "__main__":
    check_rns()
