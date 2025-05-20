from elasticsearch8 import Elasticsearch
from typing import Dict
from enum import Enum
from iterator import AnalysisIterator
from datetime import datetime, timedelta


class OA_types(Enum):
    """maps types (in the oa_relations field) to the field with text content
    for analysis """
    debate = "transcript"
    debate_topic = "debate_topic_title"
    debate_comment = "comment"


def format_keyword(keyword: str):
    if keyword == "*":
        return {"exists": {"field": "transcript"}}

    return {"match_phrase": {"transcript": keyword}}


def openaus_query(keyword: str, datefrom: str, dateto: str, field: str) -> Dict:
    matchKeyword = {
        "bool": {
            "must": [format_keyword(keyword)],
        }
    }

    matchRange = {
        "range": {
            "date": {
                "gte": datefrom,
                "lte": dateto
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


def open_aus_sentiment(client: Elasticsearch, start: str, end: str, keyword: str) -> Dict:
    data = {}
    query = openaus_query(keyword, start, end, "transcript")
    openausIter = AnalysisIterator(client, "/analysis/sentiment/v2", query)
    openausIter.elastic_fields("oa-debates", "id", "transcript", "date")

    # initialise all dates to 0s
    start_date = datetime.strptime(start, "%Y-%m-%d")
    end_date = datetime.strptime(end, "%Y-%m-%d")
    delta = end_date - start_date

    for i in range(delta.days + 1):
        day = (start_date + timedelta(days=i)).strftime("%Y-%m-%d")
        data[day] = {
            "neg": 0.0,
            "neu": 0.0,
            "pos": 0.0,
            "compound": 0.0
        }

    # aggregate sentiment across time
    for s, post in openausIter:
        if post is None:
            continue

        post_date = post.get("date")

        if post_date not in data:
            data[post_date] = {
                "neg": 0.0,
                "neu": 0.0,
                "pos": 0.0,
                "compound": 0.0
            }

        for field in ["neg", "neu", "pos", "compound"]:
            data[post_date][field] += s.get(field)

    return data
    
