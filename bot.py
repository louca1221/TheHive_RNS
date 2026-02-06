def check_rns():
    tickers = load_tickers()
    if not tickers:
        print("Watchlist is empty. No tickers to scan.")
        return
    
    print(f"Starting scan for tickers: {tickers}")

    base_url = "https://www.investegate.co.uk"
    today_url = urljoin(base_url, "/today-announcements/?perPage=300")
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'}

    if os.path.exists(FILE_NAME):
        with open(FILE_NAME, "r") as f:
            last_seen = set(f.read().splitlines())
    else:
        last_seen = set()

    try:
        response = requests.get(today_url, headers=headers, timeout=15)
        soup = BeautifulSoup(response.text, 'html.parser')
        table = soup.find('table')
        if not table:
            print("Could not find the announcements table on Investegate.")
            return
        
        rows = table.find_all('tr')
        news_found = 0

        for row in rows:
            cols = row.find_all('td')
            # Investegate Table: 0:Time, 1:Type, 2:Company, 3:Description
            if len(cols) < 4:
                continue
            
            rns_time = cols[0].get_text().strip()
            company_raw = cols[2].get_text().upper()
            announcement_cell = cols[3]
            
            for ticker in tickers:
                if re.search(rf'\({re.escape(ticker)}\)', company_raw):
                    link_tag = announcement_cell.find('a', href=True)
                    if not link_tag:
                        continue
                        
                    title = link_tag.get_text().strip()
                    full_link = urljoin(base_url, link_tag['href'])
                    
                    # NEW: Include Time in the hash for 100% uniqueness
                    unique_string = f"{rns_time}_{ticker}_{title}_{full_link}"
                    rns_id = hashlib.md5(unique_string.encode()).hexdigest()

                    if rns_id not in last_seen:
                        clean_company = company_raw.split('(')[0].replace('\n', ' ').strip()
                        clean_company = re.sub(' +', ' ', clean_company)
                        
                        # Visible output in your terminal logs
                        print(f"[{rns_time}] Match: {ticker} | Hash: {rns_id[:10]}...")

                        msg = (f"🕒 <b>{rns_time}</b>\n"
                               f"📰 <b>#{ticker} - {clean_company}</b>\n"
                               f"{title}\n\n"
                               f"🔗 <a href='{full_link}'>Read Full Release</a>")
                        
                        send_telegram_msg(msg)
                        
                        with open(FILE_NAME, "a") as f:
                            f.write(rns_id + "\n")
                        last_seen.add(rns_id)
                        news_found += 1
        
        print(f"Scan complete. Found {news_found} new items.")
    except Exception as e:
        print(f"Scraper Error: {e}")
