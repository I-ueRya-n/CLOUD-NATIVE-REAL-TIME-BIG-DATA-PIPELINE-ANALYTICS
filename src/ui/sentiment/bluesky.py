from typing import Dict
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


def format_keyword(keyword: str):
    if keyword == "*":
        return {"exists": {"field": "text"}}

    return {"match_phrase": {"text": keyword}}


def bluesky_query(keywords: [str], date: str) -> Dict:
    match = [format_keyword(word) for word in keywords]

    matchKeyword = {
        "bool": {
            "must": match,
        }
    }

    matchRange = {
        "range": {
            "createdAt": {
                "gte": date,
            }
        }
    }

    query = {
        "bool": {
            "filter": [
                matchKeyword,
                matchRange
            ]
        }
    }

    return query


def bluesky_sentiment_from(client: Elasticsearch, data: Dict,
                           date: str, search_after, keywords: [str]) -> int:
    query = bluesky_query(keywords, date)
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

        post_date = post_map[cid].get("createdAt").split("T")[0]

        if post_date not in data:
            data[post_date] = {
                "neg": 0.0,
                "neu": 0.0,
                "pos": 0.0,
                "compound": 0.0
            }

        for field in ["neg", "neu", "pos", "compound"]:
            data[post_date][field] += s.get(field)

    # return the sort value of the last post
    if len(bluesky_posts) == 0:
        return None

    return bluesky_posts[-1].get("sort")


def bluesky_sentiment(client: Elasticsearch, date: str, keyword: str) -> Dict:
    # get bluesky posts in range which match keyword
    data = {}
    search_after = None
    more_data = True
    keywords = [keyword, "auspol"]

    while more_data:
        search_after = bluesky_sentiment_from(client, data, date, search_after, keywords)
        more_data = search_after is not None

    return data
