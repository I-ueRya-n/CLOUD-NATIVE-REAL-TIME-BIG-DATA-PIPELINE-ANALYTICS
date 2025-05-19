import os
 import json
 import redis
 from util import enqueue_data, dequeue_data
 from datetime import datetime
 

 def format_reddit_post(post):
  """
  Formats the Reddit post data for Elasticsearch.
  """
  formatted_post = {
  'post_id': post.get('post_id'),
  'title': post.get('title'),
  'content': post.get('content'),
  'author': post.get('author'),
  'created_at': datetime.fromtimestamp(post.get('created_at')).isoformat(),
  'upvotes': post.get('upvotes'),
  'comments_count': post.get('comments_count'),
  'subreddit': post.get('subreddit'),
  'url': post.get('url')
  }
  return formatted_post
 

 def main():
  """
  Consumes raw Reddit data from Redis, formats it, and enqueues it
  into a new queue for Elasticsearch indexing.
  """
  formatted_posts = []
  try:
  while True:  # Keep processing until queue is empty
  post = dequeue_data('reddit_posts_queue')
  if post is None:
  break  # Exit loop when queue is empty
  formatted_post = format_reddit_post(post)
  formatted_posts.append(formatted_post)
  enqueue_data('reddit_posts_formatted_queue', json.dumps(formatted_post))
  except redis.exceptions.ConnectionError as e:
  print(f"Redis error: {e}")
  return 'Failed to connect to Redis'
  except Exception as e:  # Catch any other exceptions
  print(f"An unexpected error occurred: {e}")
  return 'An unexpected error occurred'
 

  return f'Formatted {len(formatted_posts)} posts.'