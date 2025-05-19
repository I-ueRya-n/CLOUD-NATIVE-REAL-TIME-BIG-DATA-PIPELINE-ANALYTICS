from datetime import date
import json
from typing import Optional
from flask import Request, request
import praw
import requests
from util import enqueue_data, config
from datetime import datetime, timedelta, timezone

SUBREDDITS = ["melbourne", "australian", "auspol", "auslegal", "ausfinance", 
              "ausnews", "australia", "australianpolitics", "australiannews"]
KEYWORDS = ["politics", "greens", "liberals", "labor", "vote", "election", "government", 
            "senate", "house", "parliament", "law", "policy", "politician", "political", 
            "referendum", "democracy"]

def main():
  """ queues a series of subreddits and keywords to scrape 
  Adds to queue "reddit-keys" 
  Scrapes the posts from up to 24 hours before this post
  to be run every 24 hours
  """
  scrape_until = datetime.now(timezone.utc).date()
  scrape_from = scrape_until - timedelta(days=1)

  scrape_from = scrape_from.strftime('%Y-%m-%d')
  scrape_until = scrape_until.strftime('%Y-%m-%d')
  
  for subreddit in SUBREDDITS:
    for keyword in KEYWORDS:
      enqueue_data("reddit-keys", {
        "subreddits": [subreddit],
        "keywords": [keyword],
        "scrape_from": scrape_from,
        "scrape_until": scrape_until,
        "limit": 100,
        "sort": "new"
      })
