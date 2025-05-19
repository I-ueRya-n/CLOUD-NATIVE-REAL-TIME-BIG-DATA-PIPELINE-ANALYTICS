from typing import Dict
from elasticsearch8 import Elasticsearch
from iterator import AnalysisIterator


def format_keyword(keyword: str):
    if keyword == "*":
        return {"exists": {"field": "text"}}

    return {"match_phrase": {"text": keyword}}


def bluesky_query(keywords: [str], start: str, end: str) -> Dict:
    match = [format_keyword(word) for word in keywords]

    matchKeyword = {
        "bool": {
            "must": match,
        }
    }

    matchRange = {
        "range": {
            "createdAt": {
                "gte": start,
                "lte": end
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


def bluesky_sentiment(client: Elasticsearch, start: str, end: str, keyword: str) -> int:
    data = {}
    query = bluesky_query([keyword, "auspol"], start, end)

    blueskyIter = AnalysisIterator(client, "/analysis/sentiment/v2", query, size=5000)
    blueskyIter.elastic_fields("bluesky", "cid", "text", "createdAt")

    for res, post in blueskyIter:
        if post is None:
            continue

        post_date = post.get("createdAt").split("T")[0]

        if post_date not in data:
            data[post_date] = {
                "neg": 0.0,
                "neu": 0.0,
                "pos": 0.0,
                "compound": 0.0
            }

        for field in ["neg", "neu", "pos", "compound"]:
            data[post_date][field] += res.get(field)

    return data
