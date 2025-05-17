from elasticsearch8 import Elasticsearch
from typing import Dict



def config(k: str) -> str:
    """Reads configuration from file."""
    with open(f'/configs/default/shared-data/{k}', 'r') as f:
        return f.read()


def format_keyword(keyword: str):
    if keyword == "*":
        return {"exists": {"field": "transcript"}}

    return {"match": {"transcript": keyword}}


def openaus_query(keyword: str, datefrom: str) -> Dict:

    query =  {
        "bool": {
            "must": {
                "match": {
                    "transcript": {
                        "query": keyword,
                        "operator": "and"
                    }
                }
            },
            "filter": {
                "range": {
                    "date": {
                        "gte": datefrom,
                        # "lte": dateTo
                    }
                }
            }
        }   
    }

    return query


def array_to_dict(array: [Dict], key: str) -> Dict[str, Dict]:
    d = {}
    for item in array:
        d[item[key]] = item.get("_source")
    
    return d



def oa_counts_date_range(client: Elasticsearch,
                           datefrom: str, index: str, query: str) -> Dict:
    
    query = openaus_query(query, datefrom)
    print("[Open Aus]", "query:", query)

    search_response = client.search(
        index=index,
        query=query, 
        size=0,
        aggs={
                "entries_per_day": {
                "terms": {
                    "field": "date",
                    "size": 10000,
                    "order": {
                        "_key": "asc"
                    }
                }
                }
            }
    )
    # print("response: ", search_response)
    found_debates = search_response.get("aggregations").get("entries_per_day").get("buckets")
    print("[Open Aus]", "found", len(found_debates), "posts")

    return found_debates