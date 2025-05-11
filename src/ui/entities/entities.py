from flask import request
from typing import Dict, Any, Tuple
import traceback
import bluesky
import openaus
import reddit
from elasticsearch8 import Elasticsearch


def config(k: str) -> str:
    """Reads configuration from file."""
    with open(f'/configs/default/shared-data/{k}', 'r') as f:
        return f.read()


def main() -> Tuple[Dict[str, Any], int]:
    """

    Handles:
    - Collecting the relevant posts from each data
      source in elastic search
    - Querying /analysis/named-entities/v2 for the
      named entities of each post
    - Aggregating results per day

    Returns JSON containing the frequency for the
    top n named entities in:
        - bluesky,
        - reddit,
        - openaus,
    """
    status = {}
    code = 200

    try:
        client = Elasticsearch(
            config("ES_HOSTNAME"),
            verify_certs=False,
            ssl_show_warn=False,
            basic_auth=(config("ES_USERNAME"), config("ES_PASSWORD"))
        )

        count = request.headers.get('X-Fission-Params-Count')
        status["bluesky"] = bluesky.bluesky_words(client, count)
        status["openaus"] = openaus.open_aus_words(client, count)
        status["reddit"] = reddit.reddit_words(client, count)
    except Exception as e:
        print(traceback.format_exc())
        status = {"error": str(e)}
        code = 500

    return status, code
