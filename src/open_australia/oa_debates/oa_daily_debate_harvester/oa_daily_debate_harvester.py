from flask import current_app
from typing import  Any, Optional
import requests
from datetime import datetime, timedelta

def main() -> Any:
    """
    runs the daily debate harvester for two days before the current date
    only gets debates from two days ago (they should be available by then)

    runs this once a day

    puts the results into the redis queue: "oa_debate_keys" (need to rename)
    in the format:
        {
            "date": yyyy-mm-dd,
            "house": house (senate or representatives)
        }

    Handles:
    - adding a day to redis queue to be parsed

    Returns:
    - json of one of the things added to the redis queue

    """
    
    # get the date two days ago
    yesterday = datetime.now() - timedelta(2)
    yesterday_string = yesterday.strftime("%Y-%m-%d")

    # consider both houses
    for house in ["senate", "representatives"]:
        request = {
            "date": yesterday_string,
            "house": house,
        }
        response: Optional[requests.Response] = requests.post(
            url='http://router.fission/enqueue/oa_debate_keys',
            headers={'Content-Type': 'application/json'},
            json=request
        )
        if response.status_code != 200:
                current_app.logger.error(f"Failed to add {date} to redis queue: {response.text}")
                return {"error": "Failed to add date to redis queue"}, 500
        else:
            current_app.logger.info(f"Added {request} to redis queue: oa_debate_keys, yay!")

    return request, 200
