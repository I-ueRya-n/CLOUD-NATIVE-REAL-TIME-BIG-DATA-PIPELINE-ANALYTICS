from typing import List, Dict, Any
import json
import time
import logging
from elasticsearch8 import Elasticsearch
from flask import current_app, request


def format_to_mapping(incoming_data: Dict[str, Any]) -> Dict[str, Any]:
    """ Helper function
    Format debate objects to match the mapping template to put into ES.
    Args:
        incoming_data: The raw debate data.

    Returns:
        a debate mapped and ready to go into the ES index.
    """
    print("FORMATTING TO MAPPING")
    try:
        formatted_data = {
            "id": incoming_data.get("gid", ""),
            "parent_topic": incoming_data.get("parent", {}).get("body", ""),
            "discussion_date": incoming_data.get("hdate", ""),
            "major": int(incoming_data.get("major", 0)),
            "transcript": incoming_data.get("body", ""),
            "speaker": {
                "first_name": incoming_data.get("speaker", {}).get("first_name", ""),
                "last_name": incoming_data.get("speaker", {}).get("last_name", ""),
                "party": incoming_data.get("speaker", {}).get("party", ""),
                "house": int(incoming_data.get("speaker", {}).get("house", 0)),
                "state": incoming_data.get("speaker", {}).get("constituency", ""),
                "person_id": incoming_data.get("speaker", {}).get("person_id", ""),
                "position": incoming_data.get("speaker", {}).get("title", "")
            }
        }
        return formatted_data
    except Exception as e:
        current_app.logger.error(f"Error formatting data: {e}")
        raise ValueError("Failed to format incoming data to mapping template.")


def main() -> str:
    """Process and index debate information from the OA website.
    reads from redis queue: "oa_debate_data"
    puts these into the elasticsearch index: "oa_debates"

    Handles:
    - Elasticsearch client initialization

    - Timeline pagination using since_id
    - Rate limiting with 5-second collection window
    - JSON serialization of post data


    Returns:
        "ok" if successful, else error message

    Raises:
        JSONDecodeError: If invalid JSON payload received from harvester
        ElasticsearchException: For indexing failures

    """

    es_client: Elasticsearch = Elasticsearch(
        'https://elasticsearch-master.elastic.svc.cluster.local:9200',
        verify_certs=False,
        ssl_show_warn=False,
        basic_auth=('elastic', "Mi0zu6yaiz1oThithoh3Di8kohphu9pi") ## I NEED TO ADD THE KEY FROM THE CONFIG MAP
    )


    # GET THE NEXT INCOMING FROM THE REDIS "oa_debates" QUEUE YEAH
    request_data: List[Dict[str, Any]] = request.get_json(force=True)
    current_app.logger.info(f'Processing {len(request_data)} debates')

    # Index each debate
    for debate in request_data:
        # Format the observation to match the mapping template
        try:
            debate_mapped = format_to_mapping(debate)
        except ValueError as e:
            current_app.logger.error(f"Error formatting data: {e}")
            continue

        # only add to index if the debate is not already in the index
        if es_client.exists(index='oa_debates', id=debate_mapped.get("id")):
            current_app.logger.info(
                f'Debate {debate_mapped.get("id")} already exists in the index.'
            )
            continue

        # actually add to index
        index_response: Dict[str, Any] = es_client.index(
            index='oa_debates',
            id=debate_mapped.get("id"),
            body=debate_mapped,
        )

        current_app.logger.info(
            f'Indexed observation {debate_mapped.get("id")} - '
            f'Version: {index_response["_version"]}'
        )

    return f'added {len(request_data)} debates to the index, yay!'
