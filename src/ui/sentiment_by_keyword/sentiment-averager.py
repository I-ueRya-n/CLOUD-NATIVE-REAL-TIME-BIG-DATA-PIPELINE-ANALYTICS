from flask import request
from typing import Dict, Any, Tuple
import traceback
import bluesky
import openaus
import reddit
from elasticsearch8 import Elasticsearch


def config(k: str) -> str:
    """Reads configuration from file."""
    with open(f'/configs/default/shared-data/{k}', 'r') as f:
        return f.read()


def main() -> Tuple[Dict[str, Any], int]:
    """
    Pass this a list of entities or topics and it will return the
    average sentiment for each entity or topic 

    Input can be a list of: people, parties, topics (keywords)
    and the type of keyword either (people, parties, topics)


    Handles:
    - Collecting the relevant posts from each data
      source in elastic search
    - Querying /analysis/sentiment/v2 for the sentiment of each post
    - Aggregating results per keyword

    Returns JSON containing the average sentiment for each keyword in:
        - bluesky,
        - reddit,
        - openaus,

    like:
    {
        "bluesky": {
            "keyword1": {sentiment: json, count: 5},
            "keyword2": {sentiment: json, count: 5},
        },
        "reddit": {
            "keyword1":  {sentiment: json, count: 5},
            ...
        },
        "openaus": {
            "keyword1":  {sentiment: json, count: 5},
            ...

    I need to set up a test for this
    and a fission function that requires a GET request with a body (list of keywords)
    and an address with the type of keyword yay
    like /sentiment/keyword?type=people

    """
    status = {}
    code = 200

    try:
        client = Elasticsearch(
            config("ES_HOSTNAME"),
            verify_certs=False,
            ssl_show_warn=False,
            basic_auth=(config("ES_USERNAME"), config("ES_PASSWORD"))
        )

        keyword_type = request.headers.get('X-Fission-Params-type')

        data = request.get_json()
        keyword_list = data.get('keywords', [])

        if keyword_type not in ["people", "parties", "topics"]:
            raise ValueError("Invalid type provided")
        if not keyword_list:
            raise ValueError("No keywords provided")


        status["bluesky"] = bluesky.bluesky_keywords_sentiment(client, keyword_list, keyword_type)
        
        status["openaus"] = openaus.open_aus_keywords_sentiment(client, keyword_list, "topics")

        if keyword_type != "topics":
            print("getting open aus speakers too")
            status["openaus-speakers"] = openaus.open_aus_keywords_sentiment(client, keyword_list, keyword_type)

        status["reddit"] = reddit.reddit_keywords_sentiment(client, keyword_list, keyword_type)

    except Exception as e:
        print(traceback.format_exc())
        status = {"error": str(e)}
        code = 500

    return status, code

# if __name__ == "__main__":
#     # test the function
#     client: Elasticsearch = None

#     keyword_list = ["Anthony Albanese", "Peter Dutton"]
#     keyword_type = "people"
#     status = {}
#     status["bluesky"] = bluesky.bluesky_keywords_sentiment(client, keyword_list, keyword_type)
#     status["openaus"] = openaus.open_aus_keywords_sentiment(client, keyword_list, keyword_type)
#     status["reddit"] = reddit.reddit_keywords_sentiment(client, keyword_list, keyword_type)
#     print(status)