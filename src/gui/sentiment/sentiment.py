from flask import request, current_app
from typing import Dict, Any, Tuple
import requests
import traceback
from datetime import datetime
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


def bluesky_query(keyword: str, date: str) -> Dict:
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


def bluesky_sentiment_from(client: Elasticsearch, data: Dict, date: str, f: int, size: int) -> int:
    query = bluesky_query("auspol", date)
    response = client.search(index="bluesky", query=query, from_=f, size=size)
    bluesky_posts = response.get("hits").get("hits")

    # get sentiment for bluesky posts
    sentiment_query = [p.get("_id") for p in bluesky_posts]
    addr = config("FISSION_HOSTNAME") + "/analysis/sentiment/v2/index/bluesky/field/text"
    response = requests.post(addr, json=sentiment_query)
    print("requesting", len(sentiment_query), "posts")

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

    return len(bluesky_posts)


def bluesky_sentiment(client: Elasticsearch, date: str) -> Dict:
    # get bluesky posts in range which match keyword
    data = {}
    start = 0
    size = 1000
    more_data = True

    while more_data:
        prev_count = bluesky_sentiment_from(client, data, date, start, size)
        start += prev_count
        more_data = prev_count == size

    return data


def main() -> Tuple[Any, int]:
    """
    """

    status = {}
    code = 200

    try:
        client = Elasticsearch(
            config("ES_HOSTNAME"),
            verify_certs=False,
            ssl_show_warn=False,
            basic_auth=(config("ES_USERNAME"), config("ES_PASSWORD"))
        )

        date = request.headers.get('X-Fission-Params-Date')
        status["results"] = bluesky_sentiment(client, date)
    except Exception as e:
        print(traceback.format_exc())
        status = {"error": str(e)}
        code = 500

    return status, code
