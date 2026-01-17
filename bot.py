import requests
from bs4 import BeautifulSoup
import os

TOKEN = os.getenv("TELEGRAM_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
TICKERS = ["VOD", "BP"] # Start with 1 or 2 for testing

def send_telegram_msg(text):
    if not TOKEN or not CHAT_ID:
        print("Error: Telegram credentials missing!")
        return
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    params = {"chat_id": CHAT_ID, "text": text, "parse_mode": "HTML"}
    r = requests.post(url, params=params)
    print(f"Telegram response: {r.status_code}")

def check_rns():
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    }
    
    for ticker in TICKERS:
        print(f"Checking {ticker}...")
        # LSE specific search URL
        url = f"https://www.londonstockexchange.com/stock/{ticker}/company-page"
        
        try:
            response = requests.get(url, headers=headers, timeout=10)
            if response.status_code == 200:
                print(f"Successfully reached {ticker} page.")
                # Add your BeautifulSoup parsing logic here
                # For testing, let's just send a confirmation:
                send_telegram_msg(f"Checked RNS for {ticker}. Status: Connected.")
            else:
                print(f"Failed to reach {ticker}. Status: {response.status_code}")
        except Exception as e:
            print(f"Error checking {ticker}: {e}")

if __name__ == "__main__":
    check_rns()
