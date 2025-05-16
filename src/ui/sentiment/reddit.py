from typing import Dict
from elasticsearch8 import Elasticsearch


def reddit_sentiment(client: Elasticsearch, start: str, end: str, keyword: str) -> Dict:
    example = {
        "2025-03-22": {
            "neg": 1,
            "neu": 5,
            "pos": 2,
            "compound": 3,
        }
    }

    return example
