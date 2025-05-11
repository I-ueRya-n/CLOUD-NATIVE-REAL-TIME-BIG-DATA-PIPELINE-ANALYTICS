from typing import Dict
import requests
from elasticsearch8 import Elasticsearch


def config(k: str) -> str:
    """Reads configuration from file."""
    with open(f'/configs/default/shared-data/{k}', 'r') as f:
        return f.read()


def bluesky_query(keyword: str) -> Dict:
    matchKeyword = {
        "bool": {
            "should": [
                {
                    "match_phrase": {
                        "text": keyword,
                    }
                }
            ],
            "minimum_should_match": 1
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


def bluesky_words_from(client: Elasticsearch, data: Dict,
                       count: str, f: int, size: int) -> int:
    query = bluesky_query("auspol")
    response = client.search(index="bluesky", query=query, from_=f, size=size)
    bluesky_posts = response.get("hits").get("hits")

    # get named entities for bluesky posts
    entitiy_query = [p.get("_id") for p in bluesky_posts]
    addr = config("FISSION_HOSTNAME") + "/analysis/named-entity/v2/index/bluesky/field/text"
    response = requests.post(addr, json=entitiy_query)
    print("requesting", len(entitiy_query), "posts")

    # aggregate sentiment across time
    for s in response.json():
        for word in s.get("words"):
            if word not in data:
                data[word] = 0

            data[word] += 1

    return len(bluesky_posts)


def bluesky_words(client: Elasticsearch, date: str) -> Dict:
    return {
        "labor": 5,
        "liberal": 3,
        "housing": 4,
    }

    # get bluesky posts in range which match keyword
    data = {}
    start = 0
    size = 1000
    more_data = True

    while more_data:
        prev_count = bluesky_words_from(client, data, date, start, size)
        start += prev_count
        more_data = prev_count == size

    return data
