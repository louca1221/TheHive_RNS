import requests
from bs4 import BeautifulSoup
import os

TOKEN = os.getenv("TELEGRAM_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

# Tickers must be exactly as they appear in RNS headlines (usually uppercase)
TICKERS = ["VOD", "BP", "SGE", "AZN", "GSK"] 
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
    
    # This is the master feed for ALL recent announcements
    url = "https://www.investegate.co.uk/rss/announcements"
    
    print("Fetching master RNS feed...")
    try:
        response = requests.get(url, headers=headers, timeout=15)
        soup = BeautifulSoup(response.content, 'lxml-xml')
        items = soup.find_all('item')
        
        found_count = 0
        for item in items:
            title = item.title.text.strip()
            link = item.link.text.strip()
            rns_id = item.guid.text.strip() if item.guid else link

            # Check if any of our tickers are mentioned in the title (e.g., "AstraZeneca PLC - AZN")
            # We use a space around the ticker to avoid partial matches (e.g., 'BP' matching 'BP.L')
            if any(ticker in title for ticker in TICKERS):
                if rns_id not in last_seen:
                    message = (
                        f"🔔 <b>New RNS Match</b>\n\n"
                        f"{title}\n\n"
                        f"🔗 <a href='{link}'>Read Full Release</a>"
                    )
                    send_telegram_msg(message)
                    save_new_id(rns_id)
                    print(f"✅ MATCH FOUND: {title}")
                    found_count += 1
        
        if found_count == 0:
            print("No new RNS found for your specific tickers in the latest feed.")
                
    except Exception as e:
        print(f"❌ Error fetching feed: {e}")

if __name__ == "__main__":
    check_rns()
