from typing import List, Dict, Any
from openaustralia import OpenAustralia
from flask import current_app, request
import json
import time
import logging
from typing import Dict, Any, Optional
import requests




def main() -> str:
    """Harvest debate information from the OA website.

    BY PERSON
    Gets all debates on a person
    gets person ids from the redis queue: "oa_debate_people"

    adds each page into the redis queue: "oa_debates"
        list of JSON debate objects
        NOT PARSED OR ANYTHING
        JUST RAW JSON FROM OA API


    Handles:
    - OpenAustralia API client initialization
    - pagination up to 1000 results
    - Rate limiting with 5-second rest between requests

    # - Timeline pagination using since_id
    # - Rate limiting with 5-second collection window
    # - JSON serialization of post data

    Returns:
        "yay!" if successful, else error message

    Raises:
        MastodonError: For API communication failures
        JSONDecodeError: If response parsing fails
    """
    # Initialize OpenAustralia client 
    oa = OpenAustralia("Ewi4hND52eCqBFGFsGCmjqoS") # REPLACE WITH KEY FROM CONFIG MAP


    # GET THE NEXT INCOMING FROM THE REDIS "oa_debate_dates" QUEUE YEAH
    request_data: List[Dict[str, Any]] = request.get_json(force=True)
    current_app.logger.info(f'Processing {len(request_data)} dates')

    # get the date and house (senate or representatives) from the request data
    person_ID: str = request_data.get('person', "")
    type: str = request_data.get('house', "senate")

    if not person_ID:
        current_app.logger.error("No person ID provided in request data")
        return json.dumps({"error": "No person ID provided"}), 400
    
    

    # Get debates for the specified person

    # gets the first 1000 (50 * 20) results 
    MAX_PAGES = 50
    page = 1


    # this is the first page of results, 
    debates_page = oa.get_debates(type, date=None, search=None, person_id=person_ID, 
                                      gid=None, year=None, order='d', page=None, num=None)
    
    while debates_page and page <= MAX_PAGES:
        # get the debates for the current page
        debates_page = oa.get_debates(type, date=None, search=None, person_id=person_ID, 
                                      gid=None, year=None, order='d', page=page, num=None)
        
        # if there are no more debates, break
        if not debates_page:
            current_app.logger.error(f"Finished finding debates at page {page}")
            break

        debates = debates_page.get('rows', [])

        if len(debates) == 0:
            current_app.logger.error(f"Finished finding debates at page {page}")
            break
        
        # add the debates to the redis queue
        current_app.logger.info(f"Adding {len(debates)} debate to redis queue for processing")

        response: Optional[requests.Response] = requests.post(
            url='http://router.fission/enqueue/oa_debates',
            headers={'Content-Type': 'application/json'},
            json=debates
        )



        # let the poor api breathe
        time.sleep(5)
        page += 1


    return "yay!"
