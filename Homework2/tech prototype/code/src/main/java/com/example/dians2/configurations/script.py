import requests
from bs4 import BeautifulSoup
import pandas as pd
from datetime import datetime, timedelta
import os
import time

start_time = time.time()

def format_date(date_str):
    date_obj = datetime.strptime(date_str, '%m/%d/%Y')
    return date_obj.strftime('%d.%m.%Y')

def fetch_issuer_codes():
    url = "https://www.mse.mk/en/stats/symbolhistory/kmb"
    with requests.Session() as session:
        response = session.get(url)
    soup = BeautifulSoup(response.content, "html.parser")
    dropdown = soup.find("select", id="Code")

    if not dropdown:
        print("No issuer codes found.")
        return []

    return [
        option.text.strip()
        for option in dropdown.find_all("option")
        if not any(char.isdigit() for char in option.text)
    ]

def check_last_date(issuer_code):
    file_path = f"csv/{issuer_code}.csv"
    try:
        df = pd.read_csv(file_path)
        return pd.to_datetime(df['Date'], format='%d.%m.%Y').max()
    except (FileNotFoundError, pd.errors.EmptyDataError):
        return None

def fetch_data(issuer_code, start_date, end_date):
    url = (
        f"https://www.mse.mk/en/stats/symbolhistory/{issuer_code}"
        f"?FromDate={start_date.strftime('%m/%d/%Y')}"
        f"&ToDate={end_date.strftime('%m/%d/%Y')}"
    )
    with requests.Session() as session:
        response = session.get(url)
    soup = BeautifulSoup(response.content, 'html.parser')
    tbody = soup.select_one('tbody')

    if not tbody:
        print(f"No data found for {issuer_code} from {start_date} to {end_date}.")
        return []

    return [
        [cell.get_text(strip=True) for cell in row.find_all('td')]
        for row in tbody.find_all('tr')
    ]

def save_to_csv(issuer_code, data):
    columns = ['Date', 'Last trade price', 'Max', 'Min', 'Avg. Price', '%chg.', 'Volume', 'Turnover in BEST', 'Total turnover']
    df = pd.DataFrame(data, columns=columns)
    df['Date'] = df['Date'].apply(format_date)

    file_path = f"csv/{issuer_code}.csv"
    os.makedirs(os.path.dirname(file_path), exist_ok=True)
    df.to_csv(file_path, mode='a', header=not os.path.exists(file_path), index=False)
    print(f"Data saved to {file_path}")

def update_data(issuer_code, last_date):
    current_date = datetime.now()
    start_date = last_date + timedelta(days=1) if last_date else current_date - timedelta(days=3650)

    while start_date <= current_date:
        end_date = min(datetime(start_date.year, 12, 31), current_date) if (current_date.year - start_date.year) >= 1 else current_date
        data = fetch_data(issuer_code, start_date, end_date)
        if data:
            save_to_csv(issuer_code, data)
        start_date = end_date + timedelta(days=1)
        if end_date == current_date:
            break

def main():
    issuer_codes = fetch_issuer_codes()
    for code in issuer_codes:
        last_date = check_last_date(code)
        update_data(code, last_date)
    print("Data retrieval and storage complete.")
    print(f"Execution Time: {(time.time() - start_time) / 60:.2f} minutes")

if __name__ == "__main__":
    main()