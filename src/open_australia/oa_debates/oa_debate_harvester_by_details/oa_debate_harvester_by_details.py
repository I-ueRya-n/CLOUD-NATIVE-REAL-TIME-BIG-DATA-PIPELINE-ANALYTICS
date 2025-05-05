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

    adds each page into the redis queue: "oa_debate_data"
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
    current_app.logger.info(f'Processing {len(request_data)} people')

    # get the date and house (senate or representatives) from the request data
    type: str = request_data.get('house', "senate")
    person_ID: str = request_data.get('person', None)
    date_str: str = request_data.get('date', None)

    # Validate and format the date string into a date if it exists
    if date_str:
        try:
            day, month, year = map(int, date_str.split('-'))
            if 1 <= day <= 31 and 1 <= month <= 12 and 1000 <= year <= 9999:
                date_str = f"{day:02d}-{month:02d}-{year}"
            else:
                current_app.logger.error(f"Invalid date provided: {date_str}")
                return json.dumps({"error": "Invalid date provided"}), 400
        except ValueError:
            current_app.logger.error(f"Date must be in D-M-Y format: {date_str}")
            return json.dumps({"error": "Date must be in D-M-Y format"}), 400
        

    if not person_ID or date_str:
        current_app.logger.error("No person ID or date provided in request data")
        return json.dumps({"error": "No person or date provided"}), 400
    
    

    # Get debates for the specified person

    # gets the first 1000 (50 * 20) results 
    MAX_PAGES = 50
    page = 1


    # this is the first page of results, 
    debates_page = oa.get_debates(type, date=date_str, search=None, person_id=person_ID, 
                                      gid=None, year=None, order='d', page=None, num=None)
    
    while debates_page and page <= MAX_PAGES:
        # get the debates for the current page
        debates_page = oa.get_debates(type, date=None, search=None, person_id=person_ID, 
                                      gid=None, year=None, order='d', page=page, num=None)
        
        # if there are no more debates, break
        if not debates_page:
            current_app.logger.info(f"Finished finding debates at page {page}")
            break

        debates = debates_page.get('rows', [])

        if len(debates) == 0:
            current_app.logger.info(f"Finished finding debates at page {page}")
            break
        
        debates_to_add = []
        for debate in debates:
            current_app.logger.info(f"Processing debate {debate.get('gid', '')}")
            time.sleep(0.5)
            debate_gid = debate.get('gid', "")
            # get the longer version of the debate
            if debate_gid:
                # this returns a list of debate with the same gid
                found_debates = oa.get_debates(type, date=None, search=None, person_id=None, 
                                      gid=debate_gid, year=None, order='d', page=None, num=None)
                                      
                if found_debates and isinstance(found_debates, list):
                    for result in found_debates:
                        
                        if result.get('gid', "") == debate_gid:
                            debates_to_add.append(result)
                            break
                else:
                    current_app.logger.error(f"Could not find debate with gid {debate_gid}")

        # add the debates to the redis queue
        current_app.logger.info(f"Adding {len(debates_to_add)} debate to redis queue for processing")

        response: Optional[requests.Response] = requests.post(
            url='http://router.fission/enqueue/oa_debate_data',
            headers={'Content-Type': 'application/json'},
            json=debates_to_add
        )


        # let the poor api breathe
        time.sleep(5)
        page += 1


    return "yay!"