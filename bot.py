import requests
import os

TOKEN = os.getenv("TELEGRAM_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
# Tickers you want to watch
TICKERS = ["QHE",	"SYME",	"VLRM",	"MARU",	"AMGO",	"QBT",	"AMP",	"FCM",	"MET1",	"PHE",	"ECR",	"ZIOC",	"MAST",	"WCAP",	"COBR",	"SEE",	"HE1",	"AMG",	"KEFI",	"PXC",	"ALRT",	"AVCT",	"TRP",	"ECO",	"SKA",	"HAYD",	"HEX",	"CPX",	"CIZ",	"CIZ",	"BIRD",	"INSG",	"HVO",	"WSBN",	"SVNS",	"88E",	"MILA",	"CRCL",	"EOG",	"WCAP",	"EUA",	"EUA",	"JAN",	"APTA",	"BZT",	"CMET",	"CHP",	"DEC",	"TOM",	"BOR",	"NEO",	"ONDO",	"HUI",	"GEO",	"GUN",	"TERN",	"LND",	"IRON",	"PPP",	"TM1",	"VAST",	"ALGW",
]
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
