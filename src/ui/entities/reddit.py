from typing import Dict, List
from elasticsearch8 import Elasticsearch

from iterator import AnalysisIterator, config


def reddit_query(keywords: List[str]) -> Dict:
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

    query = {
        "bool": {
            "filter": [
                matchKeyword,
            ]
        }
    }

    return query


def reddit_words(client: Elasticsearch, label: str) -> Dict:
    # extract entities matching "label" for reddit posts which match keywords
    # no range, no date, no count, we die like men
    # (Need to implment a date range and count for reddit posts oops)
    data = {}
    query = reddit_query(["greens"])
    redditIter = AnalysisIterator(client, "/analysis/ner/v2", query, 500)
    redditIter.elastic_fields("reddit", "post_id", "content", "timestamp")

    for s, _ in redditIter:
        entity = s.get("entities")

        if entity is None:
            print("no entities:", s)
            continue

        if entity.get(label) is None:
            continue

        for w in entity.get(label):
            word = w.replace("\n", " ").lower()

            if word not in data:
                data[word] = 0

            data[word] += 1

    return data

