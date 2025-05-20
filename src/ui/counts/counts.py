from flask import request
from typing import Dict, Any, Tuple
import traceback
import bluesky
import openaus
import reddit
from datetime import datetime, timedelta
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

        status["openaus"] = openaus.oa_counts_date_range(client, datefrom=date, query=keyword, index="oa-debates")
        # Returns array of 
        # {
		# 			"key_as_string": "2025-05-05T00:00:00.000Z",
		# 			"key": 1746403200000,
		# 			"doc_count": 1176
		# },
  
        first_debate = status["openaus"][0]["key_as_string"]
        
        first_debate_minus_1_month = datetime.strptime(first_debate, "%Y-%m-%dT%H:%M:%S.%fZ") - timedelta(days=60)

        # Convert back to YYYY-MM-DD format
        first_debate_minus_1_month = first_debate_minus_1_month.strftime("%Y-%m-%d")

        status["bluesky"] = bluesky.bluesky_counts_from(client, dateFrom=first_debate_minus_1_month, keywords=[keyword])


        status["reddit"] = reddit.reddit_counts_from(client, dateFrom=first_debate_minus_1_month, keywords=[keyword])
    except Exception as e:
        print(traceback.format_exc())
        status = {"error": str(e)}
        code = 500

    return status, code
