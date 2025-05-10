from typing import List, Dict, Any
from openaustralia import OpenAustralia
from flask import current_app, request
import json
import time
from typing import Dict, Any, Optional
import requests
from util import config

def main() -> str:
    """
    Harvest debate information from the OA api.
    By person or date
    
    Input:
    - from redis queue: "oa_debate_keys"
        of the format:
            {
                "house": house (senate or representatives)
                "date" OR "person": yyyy-mm-dd OR person_id,
            }    
    Output:
    - to redis queue: "oa_debate_data"
        The raw JSON data from the OA API

    Handles:
    - OpenAustralia API client initialization
    - pagination up to 1000 results
    - Rate limiting with rest between requests

    Returns:
        "yay!" if successful, else error message

    Raises:
        MastodonError: For API communication failures
        JSONDecodeError: If response parsing fails
    """
    # Initialize OpenAustralia client 
    oa = OpenAustralia(config("OA_API_KEY"))


    # GET THE NEXT INCOMING FROM THE REDIS "oa_debate_dates" QUEUE
    request_data: List[Dict[str, Any]] = request.get_json(force=True)
    current_app.logger.info(f'Processing {request_data}')

    # get the date and house (senate or representatives) from the request data
    house: str = request_data.get('house', "")
    person_ID: str = request_data.get('person', None)
    date_str: str = request_data.get('date', None)

    # Validate and format the date string into a date if it exists
    if date_str:
        try:
            year, month, day = map(int, date_str.split('-'))
            if 1 <= day <= 31 and 1 <= month <= 12 and 1000 <= year <= 9999:
                date_str = f"{year}-{month:02d}-{day:02d}"
            else:
                current_app.logger.error(f"Invalid date provided: {date_str}")
                return json.dumps({"error": "Invalid date provided"}), 400
        except ValueError:
            current_app.logger.error(f"Date must be in D-M-Y format: {date_str}")
            return json.dumps({"error": "Date must be in D-M-Y format"}), 400
        

    # if both or neither are provided, return an error
    if ((not person_ID) and (not date_str)) or (person_ID and date_str):
        current_app.logger.error("No person ID or date provided in request data")
        return json.dumps({"error": "No person or date provided"}), 400
    
    current_app.logger.info(f'Parsed input, person: {person_ID}, date: {date_str}, type: {house}')

    if (not house) or (house not in ['senate', 'representatives']):
        current_app.logger.error(f"Invalid house type: {house}. Must be 'senate' or 'representatives'")
        return json.dumps({"error": "Invalid house type"}), 400

    # gets the first 1000 (50 * 20) results 
    MAX_PAGES = 50
    page = 1

    # first page of results
    debates_page = oa.get_debates(debate_type=house, date=date_str, search=None, person_id=person_ID, gid=None, year=None, order='d', page=None, num=None)
    
    while debates_page and page <= MAX_PAGES:
        # get the debates for the current page
        debates_page = oa.get_debates(debate_type=house, date=date_str, search=None, person_id=person_ID, gid=None, year=None, order='d', page=page, num=None)
        
        # if there are no more debates, break
        if not debates_page:
            current_app.logger.info(f"Finished finding debates at page {page}")
            break
        
        # formatting is slightly different when searching by date or person
        # when searching by person the results are in the "rows" field
        # when searching by date the results are already a list
        if (date_str):
            debates = debates_page
        elif (person_ID):
            debates = debates_page.get('rows', [])
        else:
            debates = []

        if len(debates) == 0:
            current_app.logger.info(f"Finished finding debates at page {page}")
            break
        
        # extract the gid from each debate
        debates_to_add = []
        for debate in debates:


            # if the debate has sub items, also consider them
            subs = debate.get('subs', [])
            if subs and isinstance(subs, list):
                debates.extend(subs)

            entity = debate.get('entry', None)
            if entity:
                debate = entity

            debate_gid = debate.get('gid', "")

            current_app.logger.info(f"Processing debate {debate_gid}")

            time.sleep(0.3)

            # get the longer version of the debate, so its not just an excerpt
            if debate_gid:
                # this returns a list of debate with the same gid
                try:
                    found_debates = oa.get_debates(debate_type=house, date=None, search=None,person_id=None, gid=debate_gid, year=None, order='d', page=None, num=None)
                except Exception as e:
                    current_app.logger.error(f"Error fetching debate with gid {debate_gid}: {e}")
                    continue

                current_app.logger.info(f"Found {len(found_debates)} debates matching id:")
                if found_debates and isinstance(found_debates, list):

                    # individually add each debate to the list
                    for result in found_debates:
                        # current_app.logger.info(f"Found debate: {result}")
                        current_app.logger.info(f"Found debate with gid {debate_gid}")
                        if not ((result.get('subsection_id', 1)==0) and result.get('subsection_id', "")):
                            debates_to_add.append(result)
                        # break here if concerned about duplicates, idk. 
                        # if not it may miss some debates
                        # i was having issues with the api only finding the first one
                        # which was not always the full transcript
                else:
                    current_app.logger.error(f"Could not find debate with gid {debate_gid}")
                    
            else:
                current_app.logger.error(f"Could not find debate gid for {debate}")

        # add the debates to the redis queue
        current_app.logger.info(f"Adding {len(debates_to_add)} debate to redis queue for processing")

        response: Optional[requests.Response] = requests.post(
            url='http://router.fission/enqueue/oa_debate_data',
            headers={'Content-Type': 'application/json'},
            json=debates_to_add
        )
        if response.status_code != 200:
            current_app.logger.error(f"Failed to add debates to redis queue: {response.text}")
        else:
            current_app.logger.info(f"Added {len(debates_to_add)} debates to redis queue, yay!")

        # let the poor api breathe
        time.sleep(1)
        page += 1

    # idk what to return, sometimes it adds the return value to the redis queue
    return {"house": "complete"}, 200
