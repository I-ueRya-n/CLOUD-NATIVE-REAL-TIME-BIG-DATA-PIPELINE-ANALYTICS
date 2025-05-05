from openaustralia import OpenAustralia
from flask import Request, current_app, request
import json
from typing import Dict, Any, Optional
import requests
from flask import current_app, request
from datetime import date, datetime, timedelta

def main() -> Any:
    """
    runs the daily debate harvester for the previous day
    only gets debates for the previous day

    runs this once a day

    puts the results into the redis queue: "oa_debate_people" (need to rename)
    in the format:
        {
            "date": dd-mm-yyyy,
            "house": house (senate or representatives)
        }

    Handles:
    - adding a day to redis queue to be parsed

    Returns:
        right now returns json of all responses for testing
        ## "yay!" if successful, else error message

    """
            
    yesterday = datetime.now() - timedelta(1)
    yesterday_string = yesterday.strftime("%Y-%m-%d")

    for house in ["senators", "representatives"]:
        request = {
            "date": yesterday_string,
            "house": house,
        }
        response: Optional[requests.Response] = requests.post(
            url='http://router.fission/enqueue/oa_debate_people',
            headers={'Content-Type': 'application/json'},
            json=request
        )
        current_app.logger.info(f"Added {request} to redis queue: oa_debate_people, yay!")
        # print(f"Added {person.get('full_name', '')} to redis queue {parsed_person}")

    return "added yesterday's request to the redis queue", 200
