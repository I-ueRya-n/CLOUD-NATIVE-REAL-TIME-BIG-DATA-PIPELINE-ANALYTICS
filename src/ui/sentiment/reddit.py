from typing import Dict
from elasticsearch8 import Elasticsearch

from iterator import AnalysisIterator

def format_keyword(keyword: str):
    if keyword == "*" or not keyword:
        return {"exists": {"field": "content"}}

    return {"match_phrase": {"content": keyword}}


def reddit_query(keywords: [str], start: str, end: str) -> Dict:
    
    # ok this is kind of complicated, sorry
    # match_content = [{"match_phrase": {"content": word}} for word in keywords]
    # match_title = [{"match_phrase": {"title": word}} for word in keywords]

    # # if the flair is "post" then search the title and content
    # flair_post = {
    #     "bool": {
    #         "filter": [
    #             {"term": {"flair": "post"}},
    #             {
    #                 "bool": {
    #                     "should": match_title + match_content,
    #                     "minimum_should_match": 1
    #                 }
    #             }
    #         ]
    #     }
    # }

    # # if its a comment then search the content only
    # flair_comment = {
    #     "bool": {
    #         "filter": [
    #             {"bool": {"must_not": {"term": {"flair": "post"}}}},
    #             {
    #                 "bool": {
    #                     "should": match_content,
    #                     "minimum_should_match": 1
    #                 }
    #             }
    #         ]
    #     }
    # }


    matchRange = {
        "range": {
            "timestamp": {
                "gte": start,
                "lte": end
            }
        }
    }

    # query = {
    #     "bool": {
    #         "filter": [
    #             matchRange
    #         ],
    #         "should": [
    #             flair_post,
    #             flair_comment
    #         ],
    #         "minimum_should_match": 1
    #     }
    # }

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


    redditIter = AnalysisIterator(client, "/analysis/sentiment/v2", query)
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

# if __name__ == "__main__":
#     es_client = Elasticsearch(
#         "https://localhost:9200",
#         verify_certs=False,
#         ssl_show_warn=False,
#         basic_auth=("elastic", "Mi0zu6yaiz1oThithoh3Di8kohphu9pi")
#     )
#     start = "2025-01-11"
#     end = "2025-01-30"
#     keyword = "greens"
#     data = reddit_sentiment(es_client, "2021-08-22", "2021-11-03", None)
#     print(data)
