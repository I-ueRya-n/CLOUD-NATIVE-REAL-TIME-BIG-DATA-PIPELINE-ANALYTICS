from typing import Dict
from elasticsearch8 import Elasticsearch

from iterator import AnalysisIterator

def format_keyword(keyword: str):
    if keyword == "*" or not keyword:
        return {"exists": {"field": "content"}}

    return {"match_phrase": {"content": keyword}}


def reddit_query(keywords: [str], start: str, end: str) -> Dict:
    
    matchRange = {
        "range": {
            "timestamp": {
                "gte": start,
                "lte": end
            }
        }
    }


    match = [format_keyword(word) for word in keywords]

    matchKeyword = {
        "bool": {
            "must": match,
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


def reddit_sentiment(client: Elasticsearch, start: str, end: str, keyword: str) -> Dict:
    data = {}
    query = reddit_query([keyword], start, end)


    redditIter = AnalysisIterator(client, "/analysis/sentiment/v2", query, size=5000)
    # ignoring title for now, but may be important
    redditIter.elastic_fields("reddit", "post_id", "content", "timestamp")
    print("[reddit] set up iterator")
    
    for res, post in redditIter:
        if post is None:
            continue

        post_date = post.get("timestamp")

        if post_date not in data:
            data[post_date] = {
                "neg": 0.0,
                "neu": 0.0,
                "pos": 0.0,
                "compound": 0.0
            }

        for field in ["neg", "neu", "pos", "compound"]:
            data[post_date][field] += res.get(field)
    print("[reddit] finished iterating, returning data of length: " + str(len(data))) 

    # if no posts were found, return empty data
    if len(data) == 0:
        data[start] = {
            "neg": 0.0,
            "neu": 0.0,
            "pos": 0.0,
            "compound": 0.0
        }
    return data

