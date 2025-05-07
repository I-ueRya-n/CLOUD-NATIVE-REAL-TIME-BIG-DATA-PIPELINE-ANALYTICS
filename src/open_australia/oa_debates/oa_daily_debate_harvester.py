from flask import current_app
from typing import Any, Optional
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
        right now returns json of all responses for testing
        ## "yay!" if successful, else error message

    """
    yesterday = datetime.now() - timedelta(2)
    yesterday_string = yesterday.strftime("%Y-%m-%d")

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
        current_app.logger.info(f"Added {request} to redis queue: oa_debate_keys, yay!")
        # print(f"Added {request} to redis queue: oa_debate_keys, yay!")

    return "added two days ago's date to the redis queue", 200
