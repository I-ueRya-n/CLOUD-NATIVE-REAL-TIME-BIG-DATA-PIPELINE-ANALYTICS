import os
import json
from elasticsearch import Elasticsearch
from util import get_redis_client

def main():
    es = Elasticsearch(
        [os.environ.get("ES_HOST", "http://elasticsearch:9200")],
        http_auth=(os.environ.get("ES_USERNAME"), os.environ.get("ES_PASSWORD"))
    )
    redis_client = get_redis_client()

    while True:
        _, post_data = redis_client.brpop('reddit_posts_queue')
        post = json.loads(post_data)

        # Index the post into Elasticsearch
        es.index(index='reddit_posts', id=post['post_id'], body=post)