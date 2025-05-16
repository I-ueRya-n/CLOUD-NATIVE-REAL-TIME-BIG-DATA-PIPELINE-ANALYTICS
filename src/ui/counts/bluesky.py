from typing import Dict
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


def bluesky_query(keywords: [str], dateFrom: str, dateTo) -> Dict:
    match = [format_keyword(word) for word in keywords]

    matchKeyword = {
        "bool": {
            "must": match,
        }
    }

    matchRange = {
        "range": {
            "createdAt": {
                "gte": dateFrom,
                "lte": dateTo
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


def bluesky_counts_from(client: Elasticsearch, data: Dict,
                           dateFrom: str, dateTo: str, search_after, keywords: [str]) -> int:
    query = bluesky_query(keywords, dateFrom, dateTo)

    response = client.search(
        index="bluesky",
        query=query,
        search_after=search_after,
        aggs={
            "posts_per_day": {
                "date_histogram": {
                    "field": "createdAt",
                    "calendar_interval": "day"
                }
            }
        },
        size=0 # we don't need the hits here
    )
    bluesky_posts = response.get("aggregations").get("posts_per_day").get("buckets")

    return bluesky_posts
