from datetime import date
import json
from typing import Any, Dict, Optional
from flask import Request, current_app, request
import praw
import requests
from util import enqueue_data, config
from datetime import datetime, timedelta, timezone



def main():
  """ queues a series of subreddits and keywords to scrape 
  Adds to queue "reddit-keys" 
  just gets the top and most relevant for all time yay
  up to "limit"
  """
  current_app.logger.info("recieved reddit query trigger!")
  req: Request = request
  print(req, req.headers)
  try:
    request_json: Dict[str, Any] = req.get_json(force=True)
  except json.JSONDecodeError as e:
    current_app.logger.error(f"Error decoding JSON: {e}")
    return {"error": "Invalid JSON"}, 400
  print("request_json")
  print(request_json)

  limit = request_json.get('limit', 1000)
  subreddits = request_json.get('subreddits', [])
  keywords = request_json.get('keywords', [])
  
  current_app.logger.info(f'Processing {request_json}')
  enqueued = 0
  for subreddit in subreddits:
    for keyword in keywords:
      for sort in ["top", "relevance"]:
        enqueue_data("reddit-keys", json.dumps({
          "subreddits": [subreddit],
          "keywords": [keyword],
          "limit": limit,
          "sort": sort
        }))
        enqueued += 1
        current_app.logger.info(f"enqueued {subreddit} {keyword} {sort}")

  print(f"enqueued {enqueued} requests to reddit-keys")
  return {"status": "ok"}, 200