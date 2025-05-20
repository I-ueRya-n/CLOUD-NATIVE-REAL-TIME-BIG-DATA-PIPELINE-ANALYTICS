from openaustralia import OpenAustralia
from flask import Request, current_app, request
import json
from typing import Any, Optional
import requests
from datetime import datetime
from util import config


def main() -> Any:
    """
    Gets a list of the ids of Senators or House of Reps members
    who were in parliament during a given year.
    This really only needs to be run once per year to get the backlog.

    Input:
    - http trigger with:
        - year: YYYY
        - house: "senate" or "representatives"

    Output:
    puts the results into the redis queue: "oa_debate_keys"   
    in the format:
        {
            "person": person_id,
            "house": house ("senate" or "representatives")
        }

    Handles:
    - OpenAustralia API client initialization
    - querying the OpenAustralia API for members during a specific year
    - adding these people to redis queue

    Returns:
        Returns the OA api response (list of politician ids) and code 200
        To allow visual checking when called
        Or an error message and 400 if something goes wrong

    """
    # Initialize OpenAustralia client
    oa = OpenAustralia(config("OA_API_KEY"))

    # Extract and validate headers
    req: Request = request

    year: Optional[str] = req.headers.get('X-Fission-Params-year')
    house: Optional[str] = req.headers.get('X-Fission-Params-house')

    # parse date 
    date_object = datetime.strptime(year + "-01-01", "%Y-%m-%d")

    date_string = date_object.strftime("%Y-%m-%d")
    if not date_string or date_object > datetime.now():
        current_app.logger.error(f"Invalid year format: {year}")
        return json.dumps({"error": "Invalid year format"}), 400

    # query API
    if house == 'senate':
        resp = oa.get_senators(date=date_string, party=None, state=None, search=None)
    elif house == 'representatives':
        resp = oa.get_representatives(date=date_string, party=None, state=None, search=None)
    else:
        current_app.logger.error(f"Invalid house type: {house}. Must be 'senate' or 'representatives'")
        return json.dumps({"error": "Invalid house type"}), 400

    # add each found person to the redis queue
    for person in resp:
        parsed_person = {
            "person": person.get("person_id", ""),
            "house": house,
        }

        response: Optional[requests.Response] = requests.post(
            url=config("FISSION_HOSTNAME") + '/enqueue/oa_debate_keys',
            headers={'Content-Type': 'application/json'},
            json=parsed_person
        )
        if response.status_code != 200:
            current_app.logger.error(f"Failed to add {person.get('person_id', '')} to redis queue: {response.text}")
            return json.dumps({"error": "Failed to add person to redis queue"}), 400
        else:
            current_app.logger.info(f"Added {person.get('full_name', '')} to redis queue {parsed_person}, yay!")

    return resp[0], 200
