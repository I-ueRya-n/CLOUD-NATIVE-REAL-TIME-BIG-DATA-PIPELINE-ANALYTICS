import os
 import json
 from elasticsearch import Elasticsearch
 from util import dequeue_data
 

 def main():
  """
  Consumes formatted Reddit data from Redis and indexes it into Elasticsearch.
  """
  es = Elasticsearch(
  [os.environ.get("ES_HOST", "http://elasticsearch:9200")],
  http_auth=(os.environ.get("ES_USERNAME"), os.environ.get("ES_PASSWORD"))
  )
 

  indexed_count = 0
  try:
  while True:
  post = dequeue_data('reddit_posts_formatted_queue') # Dequeue from formatted queue
  if post is None:
  break
  es.index(index='reddit_posts', id=post['post_id'], body=post)
  indexed_count += 1
  except redis.exceptions.ConnectionError as e:
  print(f"Redis error: {e}")
  return 'Failed to connect to Redis'
  except Exception as e:  # Catch any other exceptions
  print(f"An unexpected error occurred: {e}")
  return 'An unexpected error occurred'
 

  return f'Indexed {indexed_count} posts.'