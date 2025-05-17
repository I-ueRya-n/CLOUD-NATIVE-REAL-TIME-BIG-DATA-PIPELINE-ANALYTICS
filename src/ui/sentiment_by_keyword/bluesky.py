from typing import Dict, List
import requests
from elasticsearch8 import Elasticsearch


def config(k: str) -> str:
    """Reads configuration from file."""
    with open(f'/configs/default/shared-data/{k}', 'r') as f:
        return f.read()


def array_to_dict(array: [Dict], key: str) -> Dict[str, Dict]:
    d = {}
    for item in array:
        d[item[key]] = item.get("_source")

    return d


def bluesky_query(keyword: str) -> Dict:
    matchKeyword = {"match_phrase": {"text": keyword}}
    matchBool = {"bool": {"must": matchKeyword}}
    query = {"bool": {"filter": [matchBool]}}

    return query


def bluesky_sentiment_from(client: Elasticsearch, data: Dict, search_after, keyword: str) -> int:
    query = bluesky_query(keyword)
    print("[Bluesky]", "query:", query)

    response = client.search(
        index="bluesky",
        query=query,
        search_after=search_after,
        sort=[{"createdAt": "asc"}, {"cid": "asc"}],
        size=1000
    )
    bluesky_posts = response.get("hits").get("hits")

    # get sentiment for bluesky posts
    sentiment_query = [p.get("_id") for p in bluesky_posts]
    addr = config("FISSION_HOSTNAME") + "/analysis/sentiment/v2/index/bluesky/field/text"

    print("[Bluesky]", "requesting", len(sentiment_query), "posts")
    response = requests.post(addr, json=sentiment_query)

    if response.status_code >= 400:
        print("error making request:", response.text)
        return None

    # aggregate sentiment across time
    post_map = array_to_dict(bluesky_posts, "_id")
    for s in response.json():
        cid = s.get("id")

        if cid not in post_map:
            print(f"missing {cid} from posts")
            continue

        for field in ["neg", "neu", "pos", "compound"]:
            data['sentiment'][field] += s.get(field)

        data['count'] += 1

    # return the sort value of the last post
    if len(bluesky_posts) == 0:
        return None

    return bluesky_posts[-1].get("sort")


def bluesky_keyword_sentiment(client: Elasticsearch, keyword: str) -> Dict:
    # get bluesky posts in range which match keyword
    data = {
        'count': 0,
        'sentiment': {
            'neg': 0.0,
            'neu': 0.0,
            'pos': 0.0,
            'compound': 0.0
        }
    }
    search_after = None
    more_data = True

    while more_data:
        search_after = bluesky_sentiment_from(client, data, search_after, keyword)
        more_data = search_after is not None

    if data['count'] != 0:
        for field in ["neg", "neu", "pos", "compound"]:
            data['sentiment'][field] /= data['count']

    return data


def bluesky_keywords_sentiment(client: Elasticsearch, keyword_list: List[str], keyword_type: str) -> Dict:
    results = {}

    for word in keyword_list:
        results[word] = bluesky_keyword_sentiment(client, word)

    return results
