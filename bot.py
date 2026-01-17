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
    requests.post(url, params=params)

def check_rns():
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
    last_seen = get_last_seen_ids()
    
    for ticker in TICKERS:
        print(f"Checking {ticker} at investegate.co.uk/company/{ticker}...")
        url = f"https://www.investegate.co.uk/company/{ticker}"
        
        try:
            response = requests.get(url, headers=headers, timeout=15)
            if response.status_code != 200:
                print(f"Failed to reach page for {ticker}. Status: {response.status_code}")
                continue

            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Investegate tables usually have links within 'td' or 'a' tags for announcements
            # We target the first link that looks like an announcement
            links = soup.select('table a[href*="/announcement/"]')
            
            if links:
                latest = links[0]
                title = latest.get_text(strip=True)
                relative_url = latest.get('href')
                full_url = f"https://www.investegate.co.uk{relative_url}"
                
                # The ID is usually the last part of the URL (numeric)
                rns_id = relative_url.rstrip('/').split('/')[-1]

                if rns_id not in last_seen:
                    message = (
                        f"🔔 <b>New RNS: {ticker}</b>\n\n"
                        f"<b>Headline:</b> {title}\n\n"
                        f"🔗 <a href='{full_url}'>Read Full Release</a>"
                    )
                    send_telegram_msg(message)
                    save_new_id(rns_id)
                    print(f"Alert sent for {ticker}")
                else:
                    print(f"No new updates for {ticker}.")
            else:
                print(f"No announcement links found for {ticker}.")
                
        except Exception as e:
            print(f"Error checking {ticker}: {e}")

if __name__ == "__main__":
    check_rns()
