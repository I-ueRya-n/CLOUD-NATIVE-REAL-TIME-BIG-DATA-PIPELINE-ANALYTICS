from typing import Dict, List
from elasticsearch8 import Elasticsearch

from iterator import AnalysisIterator
    
def reddit_query(keyword: str) -> Dict:
    matchKeyword = {"match_phrase": {"content": keyword}} if keyword != "*" else {"exists": {"field": "content"}}
    matchBool = {"bool": {"must": matchKeyword}}
    query = {"bool": {"filter": [matchBool]}}

    return query


def reddit_keyword_sentiment(client: Elasticsearch, keyword: str) -> Dict:
    data = {
        'count': 0,
        'sentiment': {
            'neg': 0.0,
            'neu': 0.0,
            'pos': 0.0,
            'compound': 0.0
        }
    }

    query = reddit_query(keyword)
    redditIter = AnalysisIterator(client, "/analysis/sentiment/v2", query)
    redditIter.elastic_fields("reddit", "post_id", "content", "timestamp")

    # aggregate sentiment across time
    for s, _ in redditIter:
        for field in ["neg", "neu", "pos", "compound"]:
            data['sentiment'][field] += s.get(field)

        data['count'] += 1

    if data['count'] > 0:
        for field in ["neg", "neu", "pos", "compound"]:
            data['sentiment'][field] /= data['count']

    return data


def reddit_keywords_sentiment(client: Elasticsearch, keyword_list: List[str], 
                              keyword_type: str) -> Dict:
    results = {}

    for word in keyword_list:
        results[word] = reddit_keyword_sentiment(client, word)

    return results

# if __name__ == "__main__":
#     es_client = Elasticsearch(
#         "https://localhost:9200",
#         verify_certs=False,
#         ssl_show_warn=False,
#         basic_auth=("elastic", "Mi0zu6yaiz1oThithoh3Di8kohphu9pi")
#     )
#     keyword = "greens"
#     sentiment_data = reddit_keyword_sentiment(es_client, keyword)
#     print(sentiment_data)