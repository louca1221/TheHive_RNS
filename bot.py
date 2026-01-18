import requests
import os
import base64

GITHUB_TOKEN = os.getenv("GH_PAT")
REPO_NAME = "louca1221/TheHive_RNS"

def sync_tickers_from_telegram():
    url = f"https://api.telegram.org/bot{TOKEN}/getUpdates"
    updates = requests.get(url).json()
    
    for update in updates.get("result", []):
        text = update.get("message", {}).get("text", "")
        if text.startswith("/add "):
            new_ticker = text.replace("/add ", "").strip().upper()
            add_ticker_to_github(new_ticker)

def add_ticker_to_github(ticker):
    file_url = f"https://api.github.com/repos/{REPO_NAME}/contents/tickers.txt"
    headers = {"Authorization": f"token {GITHUB_TOKEN}"}
    
    # 1. Get the current file content and its 'sha' (ID)
    res = requests.get(file_url, headers=headers).json()
    sha = res['sha']
    current_content = base64.b64decode(res['content']).decode('utf-8')
    
    if ticker not in current_content:
        new_content = current_content + f"\n{ticker}"
        payload = {
            "message": f"Add {ticker} via Telegram",
            "content": base64.b64encode(new_content.encode('utf-8')).decode('utf-8'),
            "sha": sha
        }
        # 2. Push the update back to GitHub
        requests.put(file_url, headers=headers, json=payload)
        send_telegram_msg(f"✅ Added {ticker} to watchlist.")

TOKEN = os.getenv("TELEGRAM_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
def load_tickers():
    file_path = "tickers.txt"
    if os.path.exists(file_path):
        with open(file_path, "r") as f:
            # .strip() removes spaces/newlines
            # .upper() ensures "vod" becomes "VOD"
            # 'if line.strip()' skips empty lines
            return [line.strip().upper() for line in f if line.strip()]
    return []

# Now your TICKERS list is dynamic
TICKERS = load_tickers()
print("--- DEBUG WATCHLIST ---")
for ticker in TICKERS:
    print(f"Tracking: [{ticker}]")
print(f"Total: {len(TICKERS)}")
print("-----------------------")
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
    # Get the string from environment and split it into a list
    chat_ids_str = os.getenv("TELEGRAM_CHAT_ID", "")
    chat_ids = chat_ids_str.split(",") if chat_ids_str else []

    if not chat_ids:
        print("Error: No Chat IDs found!")
        return

    for chat_id in chat_ids:
        chat_id = chat_id.strip() # Remove any accidental spaces
        url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
        params = {"chat_id": chat_id, "text": text, "parse_mode": "HTML"}
        try:
            r = requests.post(url, params=params, timeout=10)
            print(f"Sent to {chat_id}: {r.status_code}")
        except Exception as e:
            print(f"Failed to send to {chat_id}: {e}")

def check_rns():
    # Modern headers to look like a real browser
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
        'Accept': 'application/json'
    }
    
    # LSE News Explorer JSON Endpoint
    url = "https://api.londonstockexchange.com/api/v1/pages?path=news&parameters=categories%3Drns"
    
    print("Requesting JSON feed from LSE...")
    last_seen = get_last_seen_ids()

    try:
        response = requests.get(url, headers=headers, timeout=15)
        data = response.json()
        
        # In the LSE JSON structure, the news items are usually inside components
        # We find the 'news-list' or similar key
        components = data.get('components', [])
        news_items = []
        
        for comp in components:
            if comp.get('type') == 'news-list' or 'content' in comp:
                news_items = comp.get('content', [])
                break

        found_new = 0
        for item in news_items:
            # Extract fields from JSON
            title = item.get('title', '')
            ticker_found = item.get('tidm', '')
            rns_id = item.get('newsId', '')
            # Build the link using the newsId or path
            link = f"https://www.londonstockexchange.com/news-article/RNS/{item.get('path', '')}"

            # Match logic
            if ticker_found in TICKERS:
                if rns_id not in last_seen:
                    message = (
                        f"🔔 <b>New RNS Alert: {ticker_found}</b>\n\n"
                        f"{title}\n\n"
                        f"🔗 <a href='{link}'>Read Full Release</a>"
                    )
                    send_telegram_msg(message)
                    save_new_id(rns_id)
                    print(f"✅ Match: {ticker_found}")
                    found_new += 1
        
        if found_new == 0:
            print("No new announcements for watched tickers.")

    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    check_rns()
