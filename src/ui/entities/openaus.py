from elasticsearch8 import Elasticsearch
from typing import Dict
from datetime import datetime
import requests


def config(k: str) -> str:
    """Reads configuration from file."""
    with open(f'/configs/default/shared-data/{k}', 'r') as f:
        return f.read()

def get_date_range(date_from: str=None, date_to: str = None) -> Dict:
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
def oa_query(keywords: list[str], date_from: str, date_to:str = None) -> Dict:
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




def oa_words_from(client: Elasticsearch, search_after, data:Dict, count: str, label: str, keywords: list[str], date_from :str,
                   date_to: str=None):
    index = "oa-debates"
    query = oa_query(keywords, date_from, date_to)
    response = client.search(
        index=index,
        size=1000,
        search_after=search_after,
        query=query,
        sort=[{"date": "asc"}, {"id": "asc"}],
    )
    debates = response.get("hits").get("hits")


    # get named entities for debates
    entitiy_query = [p.get("_id") for p in debates]
    addr = config("FISSION_HOSTNAME") + f"/analysis/ner/v2/index/{index}/field/transcript"
    print("[open aus] requesting entities from", len(entitiy_query), "debates")
    response = requests.post(addr, json=entitiy_query)

    if response.status_code >= 400:
        print("[open aus] error making request:", response.text)
        return None

    # aggregate sentiment across time
    for s in response.json():
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

    # return the sort value of the last post for pagination
    if len(debates) == 0:
        return None
    # print(data)
    return debates[-1].get("sort")





def open_aus_words(client: Elasticsearch, count: str, label: str, keywords: list[str]=[], date_from :str=None,
                   date_to:str=None) -> Dict:
    """ 
        Gets the posts matching a list of keywords
        Queries the ner function to get the entities
        Then gets the count of each mentioned entity of that type

        REALLY needs a "from" date or a list of keywords. like REALLY.
        Because theres soooo much data this would take forever to do everything.

        not really using "count" at the moment? just returning all?
        following other implementations
    """

    data = {}
    search_after = None
    more_data = True

    while more_data:
        search_after = oa_words_from(client, search_after, data, count, label, keywords, date_from, date_to)
        more_data = search_after is not None
    print("[open aus] gathered count of",len(data), "entities of type", label)
    return data



# if __name__ == "__main__":
#     client: Elasticsearch = None
#     count = 10
    # data = open_aus_words(client, count, "PERSON", ["dirt"]) 

    # data = open_aus_words(client, count, "ORG", [], "2024-01-01", "2024-03-01")
