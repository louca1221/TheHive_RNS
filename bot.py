import requests
from bs4 import BeautifulSoup
import os

TOKEN = os.getenv("TELEGRAM_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
# Update this list with your tickers
TICKERS = ["VOD", "BP", "GSK", "AZN"] 
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
    params = {"chat_id": CHAT_ID, "text": text, "parse_mode": "HTML", "disable_web_page_preview": False}
    requests.post(url, params=params)

def check_rns():
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    }
    last_seen = get_last_seen_ids()
    
    for ticker in TICKERS:
        print(f"Checking {ticker}...")
        url = f"https://www.londonstockexchange.com/stock/{ticker}/company-page"
        
        try:
            response = requests.get(url, headers=headers, timeout=15)
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # LSE news items are typically wrapped in 'news-price-component' 
            # or 'news-item' tags. We look for the first link in the news section.
            news_items = soup.find_all('news-item')
            
            if not news_items:
                print(f"No news items found for {ticker}. Check if CSS selectors need updating.")
                continue

            # Get the most recent one
            latest = news_items[0]
            link_tag = latest.find('a')
            
            if link_tag:
                title = link_tag.get_text(strip=True)
                relative_url = link_tag.get('href')
                full_url = f"https://www.londonstockexchange.com{relative_url}"
                
                # Use the URL path as a unique ID
                rns_id = relative_url.split('/')[-2] if '/' in relative_url else relative_url

                if rns_id not in last_seen:
                    message = (
                        f"🔔 <b>New RNS Alert</b>\n\n"
                        f"<b>Company:</b> {ticker}\n"
                        f"<b>Headline:</b> {title}\n\n"
                        f"🔗 <a href='{full_url}'>View Full Release</a>"
                    )
                    send_telegram_msg(message)
                    save_new_id(rns_id)
                    print(f"New alert sent for {ticker}")
                else:
                    print(f"Already seen {ticker} alert.")
                    
        except Exception as e:
            print(f"Error scraping {ticker}: {e}")

if __name__ == "__main__":
    check_rns()
