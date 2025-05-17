from typing import Dict, List
from elasticsearch8 import Elasticsearch
from iterator import AnalysisIterator


def config(k: str) -> str:
    """Reads configuration from file."""
    with open(f'/configs/default/shared-data/{k}', 'r') as f:
        return f.read()


def bluesky_query(keywords: List[str]) -> Dict:
    match = [{"match_phrase": {"text": word}} for word in keywords]

    matchKeyword = {
        "bool": {
            "must": match,
        }
    }

    query = {
        "bool": {
            "filter": [
                matchKeyword,
            ]
        }
    }

    return query


def bluesky_words(client: Elasticsearch, count: str, label: str) -> Dict:
    # get bluesky posts in range which match keyword
    data = {}
    query = bluesky_query(["auspol"])
    blueskyIter = AnalysisIterator(client, "/analysis/ner/v2", query)
    blueskyIter.elastic_fields("bluesky", "cid", "text", "createdAt")

    for s, _ in blueskyIter:
        entity = s.get("entities")

        if entity is None:
            print("no entities:", s)
            continue

        if entity.get(label) is None:
            continue

        for w in entity.get(label):
            word = w.replace("\n", " ").lower()

            if word not in data:
                data[word] = 0

            data[word] += 1

    return data
