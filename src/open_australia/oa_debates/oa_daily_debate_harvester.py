from flask import current_app
from typing import Any, Optional
import requests
from datetime import datetime, timedelta
from util import config


def main() -> Any:
    """
    runs the daily debate harvester for two days before the current date
    only gets debates from two days ago (they should be available by then)

    The fission function runs this once a day

    puts the results into the redis queue: "oa_debate_keys"
    in the format:
        {
            "date": yyyy-mm-dd,
            "house": house (senate or representatives)
        }

    Handles:
    - parsing the date 2 days before
    - adding a day key to the redis queue

    Returns:
    Returns:
        the response from the most recently enqueued key 
        and a 200 status code if successful, else error message and 400

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
        # add to queue
        response: Optional[requests.Response] = requests.post(
            url=config("FISSION_HOSTNAME") + '/enqueue/oa_debate_keys',
            headers={'Content-Type': 'application/json'},
            json=request
        )
        if response.status_code != 200:
            current_app.logger.error(f"Failed to add {yesterday_string} to redis queue: {response.text}")
            return {"error": "Failed to add date to redis queue"}, 500
        else:
            current_app.logger.info(f"Added {request} to redis queue: oa_debate_keys, yay!")

    return request, 200
