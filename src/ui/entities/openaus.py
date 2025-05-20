from elasticsearch8 import Elasticsearch
from typing import List, Dict
from datetime import datetime
from iterator import AnalysisIterator


def get_date_range(date_from: str = None, date_to: str = None) -> Dict:
    """
    Returns a date range query to use for Elasticsearch.
    until now is the default date_to.
    """
    if date_from is None:
        date_from = "2000-01-01"
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


def oa_query(keywords: List[str], date_from: str, date_to: str = None) -> Dict:
    match_range = get_date_range(date_from, date_to)

    match = [{"match_phrase": {"transcript": word}} for word in keywords]

    match_keywords = {
        "bool": {
            "must": match,
        }
    }

    query = {
        "bool": {
            "filter": [
                match_range,
                match_keywords 
            ] if keywords 
            else [match_range]

        }
    }
    return query


def open_aus_words(client: Elasticsearch, label: str, keywords: List[str] = [], 
                   date_from: str = None, date_to: str = None) -> Dict:
    data = {}
    query = oa_query(keywords, date_from, date_to)

    openausIter = AnalysisIterator(client, "/analysis/ner/v2", query, 2000)
    openausIter.elastic_fields("oa-debates", "id", "transcript", "date")
    LIMIT = 15000
    done = 0

    for s, _ in openausIter:
        done += 1
        if done > LIMIT:
            print("[open aus] limit reached")
            break
        
        entity = s.get("entities")
        # print(entity)

        if entity is None:
            print("[open aus] no entities:", s)
            continue

        if entity.get(label) is None:
            continue

        for w in entity.get(label):
            word = w.replace("\n", " ").lower()

            if word not in data:
                data[word] = 0

            data[word] += 1
    print("[open aus] limit finished: ", done)
    print("[open aus] gathered count of", len(data), "entities of type", label)
    return data

