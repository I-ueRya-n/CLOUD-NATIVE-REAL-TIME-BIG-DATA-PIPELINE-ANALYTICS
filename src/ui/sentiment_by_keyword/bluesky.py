from typing import Dict, List
from elasticsearch8 import Elasticsearch
from iterator import AnalysisIterator


def bluesky_query(keyword: str) -> Dict:
    matchKeyword = {"match_phrase": {"text": keyword}}
    matchBool = {"bool": {"must": matchKeyword}}
    query = {"bool": {"filter": [matchBool]}}

    return query


def bluesky_keyword_sentiment(client: Elasticsearch, keyword: str) -> Dict:
    data = {
        'count': 0,
        'sentiment': {
            'neg': 0.0,
            'neu': 0.0,
            'pos': 0.0,
            'compound': 0.0
        }
    }

    query = bluesky_query(keyword)
    blueskyIter = AnalysisIterator(client, "/analysis/sentiment/v2", query, 5000)
    blueskyIter.elastic_fields("bluesky", "cid", "text", "createdAt")

    # aggregate sentiment across time
    for s, _ in blueskyIter:
        for field in ["neg", "neu", "pos", "compound"]:
            data['sentiment'][field] += s.get(field)

        data['count'] += 1

    if data['count'] > 0:
        for field in ["neg", "neu", "pos", "compound"]:
            data['sentiment'][field] /= data['count']

    return data


def bluesky_keywords_sentiment(client: Elasticsearch, keyword_list: List[str], keyword_type: str) -> Dict:
    results = {}

    for word in keyword_list:
        results[word] = bluesky_keyword_sentiment(client, word)

    return results
