from openaustralia import OpenAustralia
from flask import Request, current_app, request
import json
from typing import Any, Optional
import requests
from flask import current_app, request

def main() -> Any:
    """gets dates in a year with senate or house of reps debates.
    This is better than the "by person" method because it avoids duplcates

    puts the results into the redis queue: "oa_debate_keys"   
    in the format:
        {
            "date": date,
            "house": house (senate or representatives)
        }

    Handles:
    - OpenAustralia API client initialization
    - adding dates to redis queue

    Returns:
        right now returns json of all responses for testing
        ## "yay!" if successful, else error message
    Raises:
        JSONDecodeError: If response parsing fails
    """
    
    # Initialize OpenAustralia client 
    oa = OpenAustralia("Ewi4hND52eCqBFGFsGCmjqoS") # REPLACE WITH KEY FROM CONFIG MAP


    # Extract and validate headers
    req: Request = request

    year: Optional[str] = req.headers.get('X-Fission-Params-year')

    try:
        year = int(year)
    except ValueError:
        current_app.logger.error(f"Invalid year format: {year}")
        return json.dumps({"error": "Invalid year format"}), 400

    if not year or not isinstance(year, int) or year < 1900:
        current_app.logger.error(f"Invalid year provided: {year}")
        return json.dumps({"error": "Invalid year provided"}), 400
    
    # consider both houses
    for house in ['senate', 'representatives']:
        resp = oa.get_debates(house, year=year, date=None, search=None, gid=None,
                               person_id=None, order=None, page=None, num=None)
        dates = resp.get('dates', [])
        
        if not resp or len(dates) == 0:
            current_app.logger.error(f"No debates found for year {year} in {house}")
            continue

        # add each date to the redis queue individually
        for date in dates:
            parsed_date = {
                "date": date,
                "house": house,
            }

            response: Optional[requests.Response] = requests.post(
                url='http://router.fission/enqueue/oa_debate_keys',
                headers={'Content-Type': 'application/json'},
                json=parsed_date
            )
            if response.status_code != 200:
                current_app.logger.error(f"Failed to add {date} to redis queue: {response.text}")
                return json.dumps({"error": "Failed to add date to redis queue"}), 500
            else:
                current_app.logger.info(f"Added {date} to redis queue {parsed_date}, yay!")

    return resp, 200



