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

    return {"match": {"text": keyword}}


def bluesky_query(keywords: [str], dateFrom: str) -> Dict:
    # map keywords to a string
    keywords = " ".join(keywords)
    query =  {
        "bool": {
            "must": {
                "match": {
                    "text": {
                        "query": keywords,
                        "operator": "and"
                    }
                }
            },
            "filter": {
                "range": {
                    "createdAt": {
                        "gte": dateFrom
                    }
                }
            }
        }   
    }

    return query


def bluesky_counts_from(client: Elasticsearch,
                           dateFrom: str,  keywords: [str]) -> int:
    query = bluesky_query(keywords, dateFrom)

    response = client.search(
        index="bluesky",
        query=query,
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

    print("[Bluesky]", "query:", query)
    print("[Bluesky]", "posts count sum:", sum([bucket["doc_count"] for bucket in bluesky_posts]))

    return bluesky_posts
