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
    Calculates the sentiment per day from a given
    start date, across open australia debates,
    reddit and bluesky

    Handles:
    - Collecting the relevant posts from each data
      source in elastic search
    - Querying /analysis/sentiment/v2 for the
      sentiment of each post
    - Aggregating results per day

    Returns JSON containing:
        - bluesky: sentiment per day
        - reddit: sentiment per day
        - openaus: sentiment per day
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

        date = request.headers.get('X-Fission-Params-Date')
        keyword = request.headers.get('X-Fission-Params-Keyword')

        status["bluesky"] = bluesky.bluesky_sentiment(client, date, keyword)
        status["openaus"] = openaus.open_aus_sentiment(client, date, keyword)
        status["reddit"] = reddit.reddit_sentiment(client, date)
    except Exception as e:
        print(traceback.format_exc())
        status = {"error": str(e)}
        code = 500

    return status, code
