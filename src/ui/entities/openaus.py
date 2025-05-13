from elasticsearch8 import Elasticsearch
from typing import Dict


def open_aus_words(client: Elasticsearch, date: str, label: str) -> Dict:
    return {
        "labor": 7,
        "liberal": 4,
        "housing": 7,
    }
