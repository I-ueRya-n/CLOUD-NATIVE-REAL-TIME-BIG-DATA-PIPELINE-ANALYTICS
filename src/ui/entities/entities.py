from flask import request
from typing import Dict, Any, Tuple
import traceback
import bluesky
import openaus
import reddit
import openaus_speaker_entity
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

        label = request.headers.get('X-Fission-Params-Label')

        status["bluesky"] = bluesky.bluesky_words(client, label)
        # SETTING THE DATE RANGE TO 2023-01-01 
        # BECAUSE THE DATASET IS TOO BIG
        status["openaus"] = openaus.open_aus_words(client, label, date_from="2024-01-01")
        status["reddit"] = reddit.reddit_words(client, label)

        # optional: get the top speakers and parties
        # will auto filter this out
        if label == "ORG":
            status["openaus-speakers"] = openaus_speaker_entity.open_aus_count_speakers(client, 1000, "speaker.party", date_from="2024-01-01")
        elif label == "PERSON":
            status["openaus-speakers"] = openaus_speaker_entity.open_aus_count_speakers(client, 1000, "speaker", date_from="2024-01-01")
        elif label == "LOC":
            status["openaus-speakers"] = openaus_speaker_entity.open_aus_count_speakers(client, 1000, "speaker.state", date_from="2024-01-01")

    except Exception as e:
        print(traceback.format_exc())
        status = {"error": str(e)}
        code = 500

    return status, code
