import os

import requests
import feedparser

def download_nasa_rss(force_download=False):
    data_path = os.path.join(os.path.dirname(__file__), 'data')
    path = os.path.join(data_path, 'nasa_space_station_feed.xml')
    if not(os.path.exists(data_path)):
        os.mkdir(data_path)
    if not os.path.exists(path) or force_download:
        r = requests.get('https://blogs.nasa.gov/stationreport/feed/')
        with open(path, 'w') as f:
            f.write(r.text)
    return path

def parse_feed(feed_file):
    feed = feedparser.parse(feed_file)
    if 'title' in feed.entries[0]:
        for entry in feed.entries:
            print(entry.published + " - " + entry.title + ": " + entry.description[:100])

if __name__ == '__main__':
    path = download_nasa_rss(force_download=False)
    parse_feed(path)
