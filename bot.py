import requests
import os
import base64
from datetime import datetime

# --- CONFIGURATION ---
TOKEN = os.getenv("TELEGRAM_TOKEN")
CHAT_ID_STR = os.getenv("TELEGRAM_CHAT_ID", "")
GITHUB_TOKEN = os.getenv("GH_PAT")
REPO_NAME = "louca1221/TheHive_RNS"
FILE_NAME = "last_rns_ids.txt"
TICKER_FILE = "tickers.txt"

def load_tickers():
    if os.path.exists(TICKER_FILE):
        with open(TICKER_FILE, "r") as f:
            return [line.strip().upper() for line in f if line.strip()]
    return []

def send_telegram_msg(text):
    chat_ids = CHAT_ID_STR.split(",") if CHAT_ID_STR else []
    for chat_id in chat_ids:
        url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
        params = {"chat_id": chat_id.strip(), "text": text, "parse_mode": "HTML"}
        requests.post(url, params=params)

# TEMPORARY DEBUG LINE
print(f"DEBUG: Token length is {len(GITHUB_TOKEN) if GITHUB_TOKEN else 0} characters.")

# --- GITHUB API SYNC ---
def add_ticker_to_github(ticker):
    # FIRST: Check if the token actually exists in the script's memory
    if not GITHUB_TOKEN:
        send_telegram_msg("❌ Error: GH_PAT is missing from the script environment. Check your YAML file!")
        return

    file_url = f"https://api.github.com/repos/{REPO_NAME}/contents/{TICKER_FILE}"
    
    # Modern GitHub API headers
    headers = {
        "Authorization": f"Bearer {GITHUB_TOKEN}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28"
    }
    
    # 1. Get the file
    res = requests.get(file_url, headers=headers)
    if res.status_code != 200:
        send_telegram_msg(f"❌ Error {res.status_code}: Couldn't reach GitHub. Check REPO_NAME.")
        return

    data = res.json()
    sha = data.get('sha')
    current_content = base64.b64decode(data['content']).decode('utf-8')
    
    if ticker in current_content.split():
        send_telegram_msg(f"ℹ️ {ticker} is already in your watchlist.")
        return

    # 2. Update the file
    new_content = current_content.strip() + f"\n{ticker}"
    payload = {
        "message": f"Add {ticker} via Telegram",
        "content": base64.b64encode(new_content.encode('utf-8')).decode('utf-8'),
        "sha": sha
    }
    
    put_res = requests.put(file_url, headers=headers, json=payload)
    
    if put_res.status_code == 200 or put_res.status_code == 201:
        send_telegram_msg(f"✅ Successfully added <b>{ticker}</b> to watchlist")
    else:
        # This will tell you exactly why it failed (e.g., 401 = Bad Token, 403 = No Permission)
        send_telegram_msg(f"❌ GitHub API Error: {put_res.status_code}\n{put_res.json().get('message')}")
        
def sync_commands():
    url = f"https://api.telegram.org/bot{TOKEN}/getUpdates"
    # We explicitly ask for channel_post updates
    params = {"limit": 10, "timeout": 1, "allowed_updates": ["message", "channel_post"]}
    
    try:
        response = requests.get(url, params=params).json()
        updates = response.get("result", [])
        
        last_id = 0
        for update in updates:
            last_id = update.get("update_id")
            
            # Check both the 'message' bucket AND the 'channel_post' bucket
            msg_data = update.get("message") or update.get("channel_post")
            
            if msg_data:
                text = msg_data.get("text", "")
                if text.startswith("/add "):
                    ticker = text.replace("/add ", "").strip().upper()
                    add_ticker_to_github(ticker)
                elif text == "/list":
                    tickers = load_tickers()
                    msg = "📋 <b>Watchlist:</b>\n" + "\n".join([f"• {t}" for t in tickers])
                    send_telegram_msg(msg)

        if last_id > 0:
            requests.get(url, params={"offset": last_id + 1})
            
    except Exception as e:
        print(f"Sync Error: {e}")

# --- MAIN RNS LOGIC ---
def check_rns():
    tickers = load_tickers()
    if not tickers: return

    url = "https://www.investegate.co.uk/"
    # Use a more "human" user-agent to avoid being blocked
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept-Language': 'en-GB,en;q=0.9'
    }

    try:
        response = requests.get(url, headers=headers, timeout=15)
        
        # DEBUG: If this prints 403 or 404, you are being blocked
        print(f"Status Code: {response.status_code}")
        
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # 1. NEW STRATEGY: Find all links first
        # News on Investegate is almost always inside an <a> tag
        links = soup.find_all('a', href=True)
        news_found = 0

        for link in links:
            text = link.get_text().upper()
            
            for ticker in tickers:
                # Check if the ticker (VOD) or (VOD.) is in the link text
                if f"({ticker}" in text:
                    title = text.strip()
                    path = link['href']
                    full_link = f"https://www.investegate.co.uk{path}" if path.startswith('/') else path
                    
                    rns_id = hashlib.md5(f"{ticker}{title}".encode()).hexdigest()

                    # Load/Check history as before...
                    if rns_id not in last_seen:
                        msg = f"🔔 <b>New RNS: {ticker}</b>\n{title}\n\n🔗 <a href='{full_link}'>Read Full Release</a>"
                        send_telegram_msg(msg)
                        # (Save to file logic here)
                        news_found += 1
        
        print(f"Scan complete. Found {news_found} items.")

    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    sync_commands() # Update tickers first
    check_rns()     # Then scan for news
