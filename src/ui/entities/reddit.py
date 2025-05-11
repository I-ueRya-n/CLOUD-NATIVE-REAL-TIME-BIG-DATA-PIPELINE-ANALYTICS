from typing import Dict
from elasticsearch8 import Elasticsearch


def reddit_words(client: Elasticsearch, date: str) -> Dict:
    return {
        "labor": 7,
        "liberal": 13,
        "housing": 7,
    }
