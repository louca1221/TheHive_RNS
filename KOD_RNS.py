import requests
from bs4 import BeautifulSoup
import os
import sys

# Configuration from GitHub Secrets
TOKEN = os.getenv("KOD_TOKEN")
CHAT_ID = os.getenv("KOD_CHAT_ID")
ID_FILE = "kod_last_rns_id.txt"

def send_telegram(message):
    """Sends a message using HTML parse mode to avoid Markdown errors."""
    if len(message) > 4000:
        message = message[:3997] + "..."
        
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    payload = {
        "chat_id": CHAT_ID, 
        "text": message, 
        "parse_mode": "HTML",
        "disable_web_page_preview": False
    }
    try:
        r = requests.post(url, data=payload)
        r.raise_for_status()
        print("DEBUG: Message sent successfully.")
    except Exception as e:
        print(f"ERROR: Telegram failed: {e}")
        if hasattr(e, 'response') and e.response:
            print(f"DEBUG: Telegram Error Details: {e.response.text}")

def get_ai_summary(detail_url):
    """Visits the specific RNS page to extract the AI Summary text and cleans it."""
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
    try:
        resp = requests.get(detail_url, headers=headers, timeout=10)
        soup = BeautifulSoup(resp.text, 'html.parser')
        
        summary_div = soup.find('div', class_='ai-summary-content')
        if not summary_div:
            summary_div = soup.find('div', id='ai-summary')
            
        if summary_div:
            text = summary_div.get_text(strip=True)
            
            # REMOVE THE UNWANTED TEXT
            # We use replace to swap that specific phrase with nothing
            text = text.replace("Summary by AIBETAClose X", "")
            
            # Clean up any leading/trailing whitespace left over
            return text.strip()
            
        return "<i>AI Summary not available for this release.</i>"
    except Exception as e:
        return f"<i>Error loading summary: {str(e)}</i>"

def get_latest_rns():
    """Checks the Kodal Minerals (KOD) page for the latest headline."""
    print("DEBUG: Checking Investegate for KOD news...")
    url = "https://www.investegate.co.uk/company/KOD"
    headers = {'User-Agent': 'Mozilla/5.0'}
    
    try:
        response = requests.get(url, headers=headers, timeout=15)
        soup = BeautifulSoup(response.text, 'html.parser')
        
        table = soup.find('table')
        if not table: return None
        
        rows = table.find_all('tr')
        if len(rows) < 2: return None
            
        first_row = rows[1]
        cols = first_row.find_all('td')
        
        company = cols[2].text.strip()
        headline_tag = cols[3].find('a')
        headline_text = headline_tag.text.strip()
        
        # FIXED: Ensure the link is absolute
        raw_href = headline_tag['href']
        full_link = f"{raw_href}"
        
        return {
            "id": full_link,
            "company": company,
            "headline": headline_text,
            "link": full_link
        }
    except Exception as e:
        print(f"ERROR: Scraper failed: {e}")
        return None

def main():
    if not TOKEN or not CHAT_ID:
        print("ERROR: Missing Secrets!")
        sys.exit(1)

    data = get_latest_rns()
    if not data:
        return

    # Check local file to see if we've already sent this link
    last_id = ""
    if os.path.exists(ID_FILE):
        with open(ID_FILE, "r") as f:
            last_id = f.read().strip()
    
    if data["id"] != last_id:
        print(f"DEBUG: NEW RNS! Sending messages...")
        
        # MESSAGE 1: The Main Alert
        alert_msg = (
            f"🔔 <b>New RNS Alert</b>\n\n"
            f"<b>Company:</b> {data['company']}\n"
            f"<b>Headline:</b> {data['headline']}\n\n"
            f'🔗 <a href="{data["link"]}">Read Full Announcement</a>'
        )
        send_telegram(alert_msg)

        # MESSAGE 2: The AI Summary
        summary_text = get_ai_summary(data["id"])
        summary_msg = f"🤖 <b>AI Summary:</b>\n\n{summary_text}"
        send_telegram(summary_msg)
        
        # Save ID to stop duplicates
        with open(ID_FILE, "w") as f:
            f.write(data["id"])
    else:
        print("DEBUG: No new RNS detected.")

if __name__ == "__main__":
    main()
