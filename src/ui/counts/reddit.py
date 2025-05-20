from typing import Dict, List
from elasticsearch8 import Elasticsearch


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

def reddit_query(keywords: List[str], datefrom: str) -> Dict:
    """Constructs a query for reddit posts based on a list of keywords.
    The query matches posts that contain any of the keywords in the content
    or in the title, but only if the title is not the parent post's title.
    """
    # match title only if it does not include the word "PARENT"
    # (meaning it is a comment)
    match = []
    for word in keywords:
        if word == "*":
            match.append({"exists": {"field": "content"}})
        else:
            match.append({
                "bool": {
                    "should": [
                        {"match_phrase": {"content": word}},
                        {
                            "bool": {
                                "must": {"match_phrase": {"title": word}},
                                "must_not": {"match_phrase": {"title": "PARENT"}}
                            }
                        }
                    ],
                    "minimum_should_match": 1
                }
            })

    matchKeyword = {
        "bool": {
            "must": match,
        }
    }

    matchRange = {
        "range": {
            "timestamp": {
                "gte": datefrom
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


def reddit_counts_from(client: Elasticsearch,
                           dateFrom: str,  keywords: [str]) -> int:
    query = reddit_query(keywords, dateFrom)

    response = client.search(
        index="reddit",
        query=query,
        aggs={
            "posts_per_day": {
                "date_histogram": {
                    "field": "timestamp",
                    "calendar_interval": "day"
                }
            }
        },
        size=0 # we don't need the hits here
    )
    reddit_posts = response.get("aggregations").get("posts_per_day").get("buckets")

    print("[reddit]", "query:", query)
    print("[reddit]", "posts count sum:", sum([bucket["doc_count"] for bucket in reddit_posts]))

    return reddit_posts

