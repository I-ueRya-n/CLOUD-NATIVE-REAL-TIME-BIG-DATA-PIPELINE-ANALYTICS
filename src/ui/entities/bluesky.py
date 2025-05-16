from typing import Dict
import requests
from elasticsearch8 import Elasticsearch


def config(k: str) -> str:
    """Reads configuration from file."""
    with open(f'/configs/default/shared-data/{k}', 'r') as f:
        return f.read()


def bluesky_query(keywords: list[str]) -> Dict:
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


def bluesky_words_from(client: Elasticsearch, data: Dict, count: str,
                       label: str, search_after, keywords: list[str]) -> int:
    query = bluesky_query(["auspol"])
    response = client.search(
        index="bluesky",
        query=query,
        search_after=search_after,
        sort=[{"createdAt": "asc"}, {"cid": "asc"}],
        size=1000
    )
    bluesky_posts = response.get("hits").get("hits")

    # get named entities for bluesky posts
    entitiy_query = [p.get("_id") for p in bluesky_posts]
    addr = config("FISSION_HOSTNAME") + "/analysis/ner/v2/index/bluesky/field/text"
    print("requesting", len(entitiy_query), "posts")
    response = requests.post(addr, json=entitiy_query)

    if response.status_code >= 400:
        print("error making request:", response.text)
        return None

    # aggregate sentiment across time
    for s in response.json():
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

    # return the sort value of the last post
    if len(bluesky_posts) == 0:
        return None

    return bluesky_posts[-1].get("sort")


def bluesky_words(client: Elasticsearch, count: str, label: str) -> Dict:
    # get bluesky posts in range which match keyword
    data = {}
    search_after = None
    more_data = True

    while more_data:
        search_after = bluesky_words_from(client, data, count, label, search_after)
        more_data = search_after is not None

    return data
