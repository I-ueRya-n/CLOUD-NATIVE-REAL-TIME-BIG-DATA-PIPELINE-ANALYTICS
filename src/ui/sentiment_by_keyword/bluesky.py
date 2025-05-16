from typing import Dict, List
import requests
from elasticsearch8 import Elasticsearch


def bluesky_keywords_sentiment(client: Elasticsearch, 
                             keyword_list: List[str], keyword_type: str) -> Dict:
    return {'Climate Change': 
         {'sentiment': 
          {'neg': 0.051749999999999984, 
           'neu': 0.8324899999999998, 
           'pos': 0.11567000000000002, 
           'compound': 0.7022080000000003
           }, 
        'count': 100}}
    
