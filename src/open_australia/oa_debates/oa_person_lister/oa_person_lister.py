from openaustralia import OpenAustralia
from flask import Request, current_app, request
import json
from typing import Dict, Any, Optional
import requests
from flask import current_app, request
from datetime import datetime

def main() -> Any:
    """gets CURRENT SENATOR AND HOUSE OF REPS DETAILS.
    BY WHO IS IN OFFICE AT THE START OF A YEAR
    This really only needs to be run once per year yay.

    puts the results into the redis queue: "oa_debate_people"   
    in the format:
        {
            "person": person_id,
            "house": house (senate or representatives)
        }

    Handles:
    - OpenAustralia API client initialization
    - adding people to redis queue

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
    house: Optional[str] = req.headers.get('X-Fission-Params-house')
        
    date_object = datetime.strptime(year + "-01-01", "%Y-%m-%d")

    date_string = date_object.strftime("%Y-%m-%d")
    if not date_string or date_object > datetime.now():
        current_app.logger.error(f"Invalid year format: {year}")
        return json.dumps({"error": "Invalid year format"}), 400

    if house == 'senate':
        resp = oa.get_senators(date=date_string, party=None, state=None, search=None)

    elif house == 'representatives':
        resp = oa.get_representatives(date=date_string, party=None, state=None, search=None)
    else:
        current_app.logger.error(f"Invalid house type: {house}. Must be 'senate' or 'representatives'")
        return json.dumps({"error": "Invalid house type"}), 400

    for person in resp:
        parsed_person = {
            "person": person.get("person_id", ""),
            "house": house,
        }

        response: Optional[requests.Response] = requests.post(
            url='http://router.fission/enqueue/oa_debate_people',
            headers={'Content-Type': 'application/json'},
            json=parsed_person
        )
        current_app.logger.info(f"Added {person.get('full_name', '')} to redis queue {parsed_person}, yay!")
        # print(f"Added {person.get('full_name', '')} to redis queue {parsed_person}")

    return resp[0], 200


#     [{
#   "member_id" : "100014",
#   "house" : "2",
#   "first_name" : "Simon",
#   "last_name" : "Birmingham",
#   "constituency" : "SA",
#   "party" : "Liberal Party",
#   "entered_house" : "2007-05-03",
#   "left_house" : "2025-01-28",
#   "entered_reason" : "unknown",
#   "left_reason" : "resigned",
#   "person_id" : "10044",
#   "title" : "",
#   "lastupdate" : "2025-03-31 04:51:47",
#   "full_name" : "Simon Birmingham",
#   "name" : "Simon Birmingham",
#   "image" : "/images/mpsL/10044.jpg",
#   "office" : [{
#   "moffice_id" : "215684",
#   "dept" : "",
#   "position" : "Shadow Minister for Foreign Affairs",
#   "from_date" : "2022-06-05",
#   "to_date" : "9999-12-31",
#   "person" : "10044",
#   "source" : ""
# },


