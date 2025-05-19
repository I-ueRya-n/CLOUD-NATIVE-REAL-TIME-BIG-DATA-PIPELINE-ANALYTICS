import os
import json
from typing import Any, Dict, List
from elasticsearch8 import Elasticsearch
from flask import current_app, request
from util import config


REDDIT_ES_INDEX = "reddit"
def main() -> Any:

    es_client: Elasticsearch = Elasticsearch(
        config("ES_HOSTNAME"),
        verify_certs=False,
        ssl_show_warn=False,
        basic_auth=(config("ES_USERNAME"), config("ES_PASSWORD"))
    )



    # GET THE NEXT INCOMING FROM THE REDIS "reddit_post_data" QUEUE
    request_data: List[Dict[str, Any]] = request.get_json(force=True)
    current_app.logger.info(f'Processing {len(request_data)} posts')



    for post in request_data:
        current_app.logger.info(f'Processing post {post.get("post_id")}')
        #check if the post has already been added to avoid duplicates
        if es_client.exists(index=REDDIT_ES_INDEX, id=post.get('post_id')):
            current_app.logger.info(f"post {post.get('post_id', '')} already exists, skipping")

        else:
            try:
                index_response: Dict[str, Any] = es_client.index(
                    index=REDDIT_ES_INDEX,
                    id=post.get("post_id"),
                    body=post,
                )
                current_app.logger.info(
                    f'Indexed reddit post {post.get("post_id")} - \
                    Version: {index_response["_version"]}'
                )

            except Exception as e:
                current_app.logger.error(f"Error indexing post: {e}")
                continue


    return f'added {len(request_data)} posts to the index {REDDIT_ES_INDEX}, yay!'

