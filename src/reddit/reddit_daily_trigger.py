import datetime
import requests

def main():
    # Calculate the date for two days ago
    date_str = (datetime.datetime.utcnow() - datetime.timedelta(days=2)).strftime('%Y-%m-%d')

    # Trigger the Reddit scraper function
    response = requests.get(f'http://router.fission/reddit/scrape?date={date_str}')
    return response.text