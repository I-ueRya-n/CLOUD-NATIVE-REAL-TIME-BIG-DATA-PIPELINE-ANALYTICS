
from datetime import date
import json
from typing import Optional
from flask import Request, request
import praw
import requests
from util import enqueue_data, config
from datetime import datetime, timedelta, timezone


def parse_args(request_json):
  """Parses the arguments from the request JSON."""
  limit = request_json.get('limit', 10)
  subreddits = request_json.get('subreddits', [])
  keywords = request_json.get('keywords', [])
  scrape_from = request_json.get('scrape_from', "2000-01-01")
  scrape_until = request_json.get('scrape_until', None)
  sort = request_json.get('sort', None)

  try:
    scrape_from = datetime.strptime(scrape_from, '%Y-%m-%d').date()
  except ValueError:
    raise ValueError(f"Invalid date format: {scrape_from}")
  
  try:
    scrape_until = datetime.strptime(scrape_until, '%Y-%m-%d').date() if scrape_until else date.today()
  except ValueError:
    raise ValueError(f"Invalid date format: {scrape_until}")
  
  if not subreddits or not isinstance(subreddits, list):
    raise ValueError("Invalid subreddits provided" + str(subreddits))
  if not keywords or not isinstance(keywords, list):
    raise ValueError("Invalid keywords provided" + str(keywords))
  
  if not isinstance(limit, int) or limit <= 0:
    raise ValueError("Invalid limit provided" + str(limit))
  if sort not in ["top", "new", "relevance", "comments"]:
    raise ValueError("Invalid sort provided" + str(sort)) 

  return limit, subreddits, keywords, scrape_from, scrape_until, sort



def get_post_comments(reddit_client, post, limit=10):
  """Gets the top-level comments on a post.
  Just going to format them the same as a post for now."""

  post.comments.replace_more(limit=0)
  curr_date = datetime.now(timezone.utc).isoformat()
  parsed_comments = []
  for comment in post.comments.list():

    timestamp_utc = getattr(comment, 'created_utc', None)
    if timestamp_utc is not None:
      timestamp_str = datetime.fromtimestamp(timestamp_utc, tz=timezone.utc).strftime('%Y-%m-%d')
    else:
      timestamp_str = None

    if comment.parent_id == comment.link_id:
      parsed_comments.append ({
        'post_id': getattr(comment, 'id', None),
        'title': "Parent: " + getattr(post, 'title', ""),  ## putting as parent post title for now
        'author': str(getattr(comment, 'author', None)),
        'content': getattr(comment, 'body', None),
        'timestamp': timestamp_str,
        'harvested_at': curr_date,
        'url': getattr(comment, 'permalink', None),
        'subreddit': getattr(getattr(post, 'subreddit', None), 'display_name', None),
        'upvotes': getattr(comment, 'score', None),
        'flair': "comment"
      })

  enqueue_data('reddit-posts-queue', json.dumps(parsed_comments))
  print(f"Enqueud {len(parsed_comments)} comments on the post {getattr(post, 'id', None)} to the redis queue")  
  return len(parsed_comments)




def main():
    """reads from redis queue "reddit-keys" containing the following keys:
    - subreddits: list of subreddits to scrape
    - keywords: list of keywords to filter posts by
    - limit: number of posts to scrape from each subreddit (optional, default is 10)
    - scrape_from: date to scrape posts AFTER (YYYY-MM-DD) (optional, defaults to 01-01-2000)
    - scrape_until: date to scrape posts UNTIL (optional, defaults to today)
    - sort: "top" or "new" or "relevance" or "comments".(optional, defaults to "top")
    
    and enqueues the raw post data into the redis queue "reddit_post_data"
    to be added to the elasticsearch index "reddit-posts"
    
    """
  
    req: Request = request
    request_data = req.get_json(force=True)

    # example_date = { "limit": 10,
    #   "subreddits": ["melbourne", "australia", "auspol"],
    #   "keywords": ["election", "vote", "politics"],
    #   "scrape_from": "2025-05-10",
    #   "scrape_until": "2025-05-18",
    #   "sort": "new" 
    # }

    try:
      limit, subreddits, keywords, scrape_from, scrape_until, sort = parse_args(request_data)
    except ValueError as e:
      print(f"Error parsing arguments: {e}")
      return json.dumps({"error": "Invalid arguments"}), 400
    

    reddit_client = praw.Reddit(
        client_id="ZFZjHYS9Inkn8Eg9Z_QoKQ",
        client_secret="oStU1IMaW9b3mvQucsEZNcyoqjeX1w",
        username="Traditional_Rock_556",
        password="04U@nimelb25624426",
        user_agent="COMP90024_team57 Harvester by /u/Traditional_Rock_556"
    )

    # reddit_client = praw.Reddit(
    #     client_id=config("REDDIT_CLIENT_ID"),
    #     client_secret=config("REDDIT_CLIENT_SECRET"),
    #     username=config("REDDIT_USERNAME"),
    #     password=config("REDDIT_PASSWORD"),
    #     user_agent=config("REDDIT_USER_AGENT")
    # )
    curr_date = datetime.now(timezone.utc).isoformat()
    posts = []
    enqueued = 0
    for subreddit in subreddits:
      print(f"Scraping subreddit: {subreddit}")
      
      for keyword in keywords:
        print(f"Scraping keyword: {keyword}")

        # search for posts with the keyword in the title
        query = f'title:"{keyword}"'
        found_posts = reddit_client.subreddit(subreddit).search(
          query=query,
          sort=sort if sort else 'new',
          time_filter='all',
          limit=limit,
        )
        print(f"Found posts for keyword {keyword} in subreddit {subreddit}")
        for found_post in found_posts:
          created = datetime.fromtimestamp(found_post.created_utc, tz=timezone.utc)
          # check if the post is within the date range
          if scrape_from <= created.date() < scrape_until:
            timestamp_utc = getattr(found_post, 'created_utc', None)
            if timestamp_utc is not None:
              timestamp_str = datetime.fromtimestamp(timestamp_utc, tz=timezone.utc).strftime('%Y-%m-%d')
            else:
              timestamp_str = None

            post = {
              'post_id': getattr(found_post, 'id', None),
              'title': getattr(found_post, 'title', None),
              'content': getattr(found_post, 'selftext', None),
              'author': str(getattr(found_post, 'author', None)),
              'timestamp': timestamp_str,
              'upvotes': getattr(found_post, 'score', None),
              'comments_count': getattr(found_post, 'num_comments', None),
              'subreddit': subreddit,
              'url': getattr(found_post, 'url', None),
              'keyword': keyword,
              'harvested_at': curr_date,
              'flair': "post",
            }
            posts.append(post)
            print(f"found post: {getattr(found_post, 'title', None)}")

            # get top-level comments for the post
            get_post_comments(reddit_client, found_post, limit=limit)
              
            if len(posts) >= limit:
              enqueued += len(posts)
              enqueue_data('reddit-posts-queue', json.dumps(posts))
              print(f"Enqueued {len(posts)} posts to the redis queue for subreddit {subreddit} and keyword {keyword}")
              posts = []
              break

        if len(posts) >= limit:
          break

    enqueue_data('reddit-posts-queue', json.dumps(posts))
    print(f"Final: Enqueued {len(posts)}")

    return json.dumps({'message': f'Enqueued {enqueued} posts.'}), 200
