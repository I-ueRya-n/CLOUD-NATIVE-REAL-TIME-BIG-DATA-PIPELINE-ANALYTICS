from elasticsearch8 import Elasticsearch
from typing import Dict, List
from datetime import datetime
import requests

def config(k: str) -> str:
  """Reads configuration from file."""
  with open(f'/configs/default/shared-data/{k}', 'r') as f:
      return f.read().strip()

def get_date_range(date_from: str = "2000-01-01", date_to: str = None) -> Dict:
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

def build_keyword_query(keyword: str, keyword_type: str) -> Dict:
  """Builds a keyword query for the given keyword and type.
  atm just all time"""
  matchRange = get_date_range()

  if keyword_type == "people":
      # Split the keyword into parts (assume first and last name)
      # maybe i should fin dperson id  instead ugh
      name_parts = keyword.strip().split()
      if len(name_parts) == 2:
          first_name, last_name = name_parts
          matchKeyword = {
          "bool": {
          "must": [
              {"match": {"speaker.first_name": first_name}},
              {"match": {"speaker.last_name": last_name}}
            ]
          }}
      else:
          # couldnt split oh no its not gonna work sorry
          matchKeyword = {
          "bool": {
          "should": [
              {"match": {"speaker.first_name": keyword}},
              {"match": {"speaker.last_name": keyword}}
          ]
          }
          }

  elif keyword_type == "parties":
      matchKeyword = { "match": {
                  "speaker.party": keyword
              }}

  elif keyword_type == "topics":
      matchKeyword = { "match": {
          "transcript": keyword.lower()  
          }}
  else:
      raise ValueError("keyword_type must be one of 'people', 'parties', or 'topics'")
  query = {
      "bool": {
          "filter": [
              matchKeyword,
              matchRange
          ],
      }
  }
  return query



def open_aus_keyword(client: Elasticsearch, index: str, keyword: str, 
                     keyword_type: str, limit_count: int = 5000) -> Dict:
        """ searches for the keyword in the index,
           gets the sentiment for each matching document, 
         then averages the sentiment. Yay!

        returns:
             {"sentiment": the averaged sentiment json from before, "count": num of docs}}
            
        e.g. open_aus_keyword_sentiment(es_client, ["Anthony Albanese"], "people")
        open_aus_keyword_sentiment(es_client, ["Australian Greens"], "parties")
        open_aus_keyword_sentiment(es_client, ["climate change"], "topics")

        must use whole proper words for people and parties as stored
        """

        # Build the query
        query = build_keyword_query(keyword, keyword_type)

        response = client.search(
            index=index,
            size=limit_count,
            query=query,
            _source=["id", "date", "transcript", "speaker.first_name", 
                     "speaker.last_name", "speaker.party"],
        )

        debates = response.get("hits", {}).get("hits", [])
        print(f"[Open Aus] Found {len(debates)} hits for keyword '{keyword}' of type '{keyword_type}'")

        doc_ids = [d["_id"] for d in debates]
        if not doc_ids:
            return {"sentiment": None, "count": 0}
        
        # Get sentiment for found debates
        # print("[Open Aus] first debate checking", debates[0])
        print("[Open Aus]", "example doc_ids:", doc_ids[:5])
        addr = config("FISSION_HOSTNAME") + f"/analysis/sentiment/v2/index/{index}/field/transcript"
        sentiment_response = requests.post(addr, json=doc_ids)
        if sentiment_response.status_code >= 400:
            print("[Open Aus]", "Error making request:", sentiment_response.text)
            return {"sentiment": None, "count": 0}

        sentiments = sentiment_response.json()
        count = len(sentiments)

        # Average sentiment fields
        avg_sentiment = {"neg": 0.0, "neu": 0.0, "pos": 0.0, "compound": 0.0}
        for s in sentiments:
            for field in avg_sentiment:
                avg_sentiment[field] += s.get(field, 0.0)
        if count > 0:
            for field in avg_sentiment:
                avg_sentiment[field] /= count

        return {"sentiment": avg_sentiment, "count": count}


def open_aus_keywords_sentiment(client: Elasticsearch, keyword_list: List[str], keyword_type: str) -> Dict:
    """
    takes list of keywords and a keyword_type 
    for each keyword in keyword_list, searches the "oa-debates" index for the keyword in the given field,
    gets the sentiment for each matching document, and averages the sentiment for each keyword.
    returns dict of 
      {keyword: {"sentiment": sentiment json "count": N}}
    """
    results = {}
    index = "oa-debates"
    if keyword_type not in ["people", "parties", "topics"]:
        raise ValueError("keyword_type must be one of 'people', 'parties', or 'topics'")


    for keyword in keyword_list:
        keyword_sentiment = open_aus_keyword(client, index, keyword, keyword_type)
        if keyword_sentiment:
            results[keyword] = keyword_sentiment
        else:
            results[keyword] = {"sentiment": None, "count": 0}

    return results

# if __name__ == "__main__":
#    es_client: Elasticsearch = None
    # result = open_aus_keyword_sentiment(es_client, ["Climate Change"], "topics")
    # result =open_aus_keyword_sentiment(es_client, ["Australian Greens"], "parties")
    # result =open_aus_keyword_sentiment(es_client, ["Anthony Albanese", "Pauline Hanson"], "people")

    # print(result)