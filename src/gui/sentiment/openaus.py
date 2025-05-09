from elasticsearch8 import Elasticsearch
from typing import Dict


def open_aus_sentiment(client: Elasticsearch, date: str) -> Dict:
    example = {
        date: {
            "neg": 1,
            "neu": 5,
            "pos": 2,
            "compound": 3,
        }
    }

    return example
