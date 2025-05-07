from typing import List, Dict, Any
from openaustralia import OpenAustralia
from flask import current_app, request
import json
import time
from typing import Dict, Any, Optional
import requests




def main() -> str:
    """Harvest debate information from the OA website.

    BY PERSON OR DATE
    Gets all debates on a person OR a date
    gets person ids from the redis queue: "oa_debate_keys"

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
    # request_data = {'date': '2024-11-20', 'house': 'representatives'}
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
        

    if (not person_ID) and (not date_str):
        current_app.logger.error("No person ID or date provided in request data")
        return json.dumps({"error": "No person or date provided"}), 400
    current_app.logger.info(f'Parsed input, person: {person_ID}, date: {date_str}, type: {house}')

    if (not house) or (house not in ['senate', 'representatives']):
        current_app.logger.error(f"Invalid house type: {house}. Must be 'senate' or 'representatives'")
        return json.dumps({"error": "Invalid house type"}), 400
    # Get debates for the specified person

    # gets the first 1000 (50 * 20) results 
    MAX_PAGES = 50
    page = 1


    # this is the first page of results, 
    debates_page = oa.get_debates(debate_type=house, date=date_str, search=None, person_id=person_ID, gid=None, year=None, order='d', page=None, num=None)
    
    while debates_page and page <= MAX_PAGES:
        # get the debates for the current page
        debates_page = oa.get_debates(debate_type=house, date=date_str, search=None, person_id=person_ID, gid=None, year=None, order='d', page=page, num=None)
        
        # if there are no more debates, break
        if not debates_page:
            current_app.logger.info(f"Finished finding debates at page {page}")
            break
        
        if (date_str):
            debates = debates_page
        elif (person_ID):
            debates = debates_page.get('rows', [])
        else:
            debates = []
        if len(debates) == 0:
            current_app.logger.info(f"Finished finding debates at page {page}")
            break
        
        debates_to_add = []
        for debate in debates:
            if (date_str):
                debate_gid = debate.get('entry', {}).get('gid', "")
            elif (person_ID):
                debate_gid = debate.get('gid', "")
            else:
                debate_gid = None

            current_app.logger.info(f"Processing debate {debate_gid}")
            time.sleep(0.3)
            # get the longer version of the debate
            if debate_gid:
                # this returns a list of debate with the same gid
                try:
                    found_debates = oa.get_debates(debate_type=house, date=None, search=None,person_id=None, gid=debate_gid, year=None, order='d', page=None, num=None)
                except Exception as e:
                    current_app.logger.error(f"Error fetching debate with gid {debate_gid}: {e}")
                    current_app.logger.info(f"Could not find debate with gid {debate_gid}")
                    continue
                current_app.logger.info(f"Found debates: {found_debates}")
                current_app.logger.info("yay")
                if found_debates and isinstance(found_debates, list):
                    for result in found_debates:
                        current_app.logger.info(f"Found debate: {result}")
                        if result.get('gid', "") == debate_gid:
                            current_app.logger.info(f"Found debate with gid {debate_gid}")
                            debates_to_add.append(result)
                            # break here if concerned about duplicates, idk. 
                            # if not it may miss some debates
                            # break
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
            

        # let the poor api breathe
        time.sleep(1)
        page += 1


    return "yay", 200

if __name__ == "__main__":
    main()