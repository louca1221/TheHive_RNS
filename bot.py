import requests
from bs4 import BeautifulSoup
import os

# Configuration
TOKEN = os.getenv("TELEGRAM_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
# Add your specific tickers here
TICKERS = ["UFO", "KOD", "ALK"] 

def check_rns():
    for ticker in TICKERS:
        url = f"https://www.londonstockexchange.com/stock/{ticker}/company-page"
        headers = {'User-Agent': 'Mozilla/5.0'}
        response = requests.get(url, headers=headers)
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # This part requires specific selector tuning based on LSE's current HTML structure
        # Logic: Find the latest news title and link, compare with a 'last_seen.txt'
        # If new, send_telegram_msg(f"New RNS for {ticker}: {title} \n {link}")

def send_telegram_msg(text):
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    params = {"chat_id": CHAT_ID, "text": text, "parse_mode": "Markdown"}
    requests.post(url, params=params)
