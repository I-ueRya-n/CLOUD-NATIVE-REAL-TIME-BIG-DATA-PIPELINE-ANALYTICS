from elasticsearch8 import Elasticsearch
from typing import Dict
from enum import Enum
import requests
from datetime import datetime, timedelta

class OA_types(Enum):
    """maps types (in the oa_relations field) to the field with text content
    for analysis """
    debate = "transcript"
    debate_topic =  "debate_topic_title"
    debate_comment = "comment"

def config(k: str) -> str:
    """Reads configuration from file."""
    with open(f'/configs/default/shared-data/{k}', 'r') as f:
        return f.read()

def openaus_query(keyword: str, datefrom: str, dateto: str, data_type: OA_types) -> Dict:
    matchType = {
        "bool": {
            "should": [
                {
                    "match_phrase": {
                        "oa_relations": str(data_type.name),
                        # data_type.value: keyword,
                    }
                }
            ],
            "minimum_should_match": 1
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
                matchType,
                matchRange
            ]
        }
    }

    return query


def array_to_dict(array: [Dict], key: str) -> Dict[str, Dict]:
    d = {}
    for item in array:
        d[item[key]] = item.get("_source")

    return d


def oa_sentiment_date_range(client: Elasticsearch, data: Dict,
                           datefrom: str, dateto: str, search_after: int, size: int) -> Dict:
    
    datatype = OA_types.debate
    query = openaus_query("", datefrom, dateto, datatype)
    print("query:", query)

    search_response = client.search(
        index="oa_debates_comments", 
        query=query, 
        size=size,
        search_after=search_after,
        sort=[{"date": "asc"}, {"id": "asc"}],
      )
    # print("response: ", search_response)
    found_debates = search_response.get("hits").get("hits")

    # get sentiment for debates by sending the sentiment function ids
    sentiment_query = [p.get("_id") + "?routing=" + p.get("_routing") for p in found_debates]

    # had to add alias to the index get this to work with underscores
    addr = config("FISSION_HOSTNAME") + f"/analysis/sentiment/v2/index/oadebatescomments/field/{datatype.value}"
    print("requesting sentiment of", len(sentiment_query), "debates")
    print(addr)
    print("sentiment query", sentiment_query[:10])
    # just doing the first 10 for testing
    sentiment_response = requests.post(addr, json=sentiment_query[:10])
    
    if sentiment_response.status_code >= 400:
        print("error making request:", sentiment_response.text)
        return None


    # aggregate sentiment across time
    post_map = array_to_dict(found_debates, "_id")
    print(sentiment_response.json())
    for s in sentiment_response.json():
        cid = s.get("id")

        if cid not in post_map:
            print(f"missing {cid} from posts")
            continue

        post_date = post_map[cid].get("createdAt").split("T")[0]

        if post_date not in data:
            data[post_date] = {
                "neg": 0.0,
                "neu": 0.0,
                "pos": 0.0,
                "compound": 0.0
            }

        for field in ["neg", "neu", "pos", "compound"]:
            data[post_date][field] += s.get(field)

    # return the sort value of the last post
    if len(found_debates) == 0:
        return None

    return found_debates[-1].get("sort")



def open_aus_sentiment(client: Elasticsearch, date: str) -> Dict:
    data = {}
    search_after = None
    more_data = True


    # gets 1 month of data from the given date
    print("date", date)
    dateto = (datetime.strptime(date, "%Y-%m-%d").date() + timedelta(days=30)).strftime("%Y-%m-%d")
    print("dateto", dateto)

    while more_data:
        search_after = oa_sentiment_date_range(client, data, date, dateto, search_after, 1000)
        more_data = search_after is not None


    return data

