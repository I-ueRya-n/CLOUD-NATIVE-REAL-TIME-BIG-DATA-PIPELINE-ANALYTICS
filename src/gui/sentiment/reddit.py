from typing import Dict
from elasticsearch8 import Elasticsearch


def reddit_sentiment(client: Elasticsearch, date: str) -> Dict:
    example = {
        "2025-03-22": {
            "neg": 1,
            "neu": 5,
            "pos": 2,
            "compound": 3,
        }
    }

    return example
