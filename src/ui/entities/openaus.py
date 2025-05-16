from elasticsearch8 import Elasticsearch
from typing import Dict
from datetime import datetime

def get_date_range(date_from: str, date_to: str = None) -> Dict:
    """
    Returns a date range query to use for Elasticsearch.
    until now is the default date_to.
    """
    if date_to is None:
        date_to = datetime.now().strftime("%Y-%m-%d")

    return {
        "range": {
            "date": {
                "gte": date_from,
                "lte": date_to
            }
        }
    }


def get_count_politicians(client: Elasticsearch, count: int,
                date_from: str = "2000-01-01", date_to: str = None) -> Dict:
    """
    Returns the politicians (first and last names) with the most occurences.
    Gets the top person ids, then gets the first and last names for each.
    """
    print("getting count politicians")
    response = client.search(
        index="oa-debates",
        size=0,
        query=get_date_range(date_from, date_to),
        aggs={
            "top_speakers": {
                "terms": {
                    "field": "speaker.person_id",
                    "size": count
                },
                "aggs": {
                    "name": {
                        "top_hits": {
                            "size": 1,
                            "_source": {
                                "includes": [
                                    "speaker.first_name",
                                    "speaker.last_name"
                                ]
                            }
                        }
                    }
                }
            }
        }
    )
    buckets = response["aggregations"]["top_speakers"]["buckets"]

    result = {}
    for bucket in buckets:
        hits = bucket["name"]["hits"]["hits"]
        if hits:
            source = hits[0]["_source"]["speaker"]
            full_name = f"{source.get('first_name', '')} {source.get('last_name', '')}".strip()
        else:
            full_name = "Unknown politician"
        result[full_name] = bucket["doc_count"]

    return result    



def get_count_keywords(client: Elasticsearch, count: int, label: str, 
                       date_from: str = "2000-01-01", date_to: str = None) -> Dict:
    """
    Returns the items with the most occurrences for a given label.
    The label should be a "keyword" in the index.
    example calls:
    - get_count_keywords(client, 10, "speaker.party")
    - get_count_keywords(client, 10, "speaker.state")
    - get_count_keywords(client, 10, "speaker") -> gets politician entities yay!
    """
    response = client.search(
        index="oa-debates",
        size=0,
        query=get_date_range(date_from, date_to),
        aggs={
            "top_counts": {
                "terms": {
                    "field": label,
                    "size": count
                }
            }
        }
    )
    buckets = response["aggregations"]["top_counts"]["buckets"]
    result = {bucket["key"]: bucket["doc_count"] for bucket in buckets}
    return result


def open_aus_words(client: Elasticsearch, count: str, label: str) -> Dict:
    # need this because it combos firstname and lastname
    if label == "speaker":
        data = get_count_politicians(client, count)
    else:
        data = get_count_keywords(client, count, label)

    return data
