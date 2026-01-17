import requests
from bs4 import BeautifulSoup
import os

TOKEN = os.getenv("TELEGRAM_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
# Add your tickers here (use the TIDM/Ticker code)
TICKERS = ["VOD", "BP", "GSK", "AZN", "SGE"] 
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
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
    last_seen = get_last_seen_ids()
    
    for ticker in TICKERS:
        print(f"Searching Investegate for: {ticker}...")
        # Investegate search results for specific tickers
        url = f"https://www.investegate.co.uk/search-results?q={ticker}"
        
        try:
            response = requests.get(url, headers=headers, timeout=15)
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Target the first 'search-result-title' which holds the latest RNS
            result = soup.select_one('.search-result-title a')
            
            if result:
                title = result.get_text(strip=True)
                link = "https://www.investegate.co.uk" + result['href']
                # The ID is the unique number at the end of the URL
                rns_id = result['href'].split('/')[-1]

                if rns_id not in last_seen:
                    message = (
                        f"🔔 <b>New RNS Alert: {ticker}</b>\n\n"
                        f"{title}\n\n"
                        f"🔗 <a href='{link}'>Read Full Release</a>"
                    )
                    send_telegram_msg(message)
                    save_new_id(rns_id)
                    print(f"Successfully sent alert for {ticker}")
                else:
                    print(f"No new RNS for {ticker} (already seen ID: {rns_id})")
            else:
                print(f"Could not find any news results for {ticker}")
                
        except Exception as e:
            print(f"Error checking {ticker}: {e}")

if __name__ == "__main__":
    check_rns()
