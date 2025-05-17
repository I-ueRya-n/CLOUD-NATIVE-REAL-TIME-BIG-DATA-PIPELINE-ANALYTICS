from typing import List, Dict, Any
from elasticsearch8 import Elasticsearch
from flask import current_app, request
from util import config


def format_debate(data: Dict[str, any]) -> Dict[str, Any]:
    """ 
        Formats debate to match the mapping template to put into ES.
        
        Handles:
        - extracting and formatting the data to match the mapping template
        - if a field is not present, it will be set to an empty string

        Args:
            incoming_data: The raw data representation of a debate topic.
        Returns:
            a debate comment mapped and ready to go into the ES index. woo hoo!
    """
    formatted_data = {
        "id": data.get("epobject_id", ""),
        "gid": data.get("gid", ""),
        "date": data.get("hdate", ""),
        "parent_topic": data.get("parent", {}).get("body", ""),
        "transcript": data.get("body", ""),
        "speaker": {
            "first_name": data.get("speaker", {}).get("first_name", ""),
            "last_name": data.get("speaker", {}).get("last_name", ""),
            "party": data.get("speaker", {}).get("party", ""),
            "house": (data.get("speaker", {}).get("house", 0)),
            "state": data.get("speaker", {}).get("constituency", ""),
            "person_id": data.get("speaker", {}).get("person_id", ""),
            "position": data.get("speaker", {}).get("title", "")
        },
    }
    current_app.logger.info(f'Formatted debate: {formatted_data}')
    return formatted_data


def format_debate_comment(data: Dict[str, Any], parent_debate: str) -> Dict[str, Any]:
    """ 
        Formats debate comment to match the mapping template to put into ES.

        Handles:
        - extracting and formatting the data to match the mapping template
        - if a field is not present, it will be set to an empty string

        Args:
            incoming_data: The raw data representation of a debate topic.
        Returns:
            a debate comment mapped and ready to go into the ES index. woo hoo!
    """
    comment = data.get("comment", {})

    formatted_data = {
        "id": comment.get("comment_id", ""),
        "user_id": comment.get("user_id", ""),
        "user_name": comment.get("username", ""),
        "comment": comment.get("body", ""),
        "date": comment.get("posted", "").split(" ")[0],
        "parent_debate_id": parent_debate,
    }
    return formatted_data


def add_debate(es_client: Elasticsearch, debate: Dict[str, Any]) -> None:
    """
    Formats and adds a debate.
    """
    try:
        # add the debate
        debate_mapped = format_debate(debate)
        try:
            index_response: Dict[str, Any] = es_client.index(
                index='oa-debates',
                id=debate_mapped.get("id"),
                body=debate_mapped,
            )
            current_app.logger.info(
                f'Indexed debate {debate_mapped.get("id")} - Version: {index_response["_version"]}'
            )

        except Exception as e:
            current_app.logger.error(f"Error indexing debate: {e}")
            return

        # if it has a comment, add it
        add_debate_comment(es_client, debate)

    except ValueError as e:
        current_app.logger.error(f"Error formatting debate: {e}")


def add_debate_comment(es_client: Elasticsearch, data: Dict[str, Any]) -> None:
    """
    Formats and adds a debate and any one attached comment to the index.
    """
    # check if it has a comment
    comment = data.get("comment", None)
    if comment is None or comment == {}:
        return

    try:
        # add the comment
        comment_mapped = format_debate_comment(comment, data.get("epobject_id", ""))
        try:
            index_response: Dict[str, Any] = es_client.index(
                index='oa-comments',
                id=comment_mapped.get("id"),
                body=comment_mapped,
            )
            current_app.logger.info(
            f'Indexed comment {comment_mapped.get("id")} - Version: {index_response["_version"]}'
            )

        except Exception as e:
            current_app.logger.error(f"Error indexing comment: {e}")
            return

    except ValueError as e:
        current_app.logger.error(f"Error formatting comment: {e}")


def main() -> str:
    """Process and index debate information from the OA website.
    reads from redis queue: "oa_debate_data"
    puts these into the elasticsearch index: "oa_debates_comments"

    Does not add duplicates of comments or debates if the id already exists!

    (subsection = topic)

    Handles:
    - Elasticsearch client initialization
    - parent child relationship between comments and debates
    - parent child relationship between debates and topics

    - checks if the "debate" object is a section, subsection or a debate
    - does not add sections, only subsections and debates and their comments

    - routes by the subsection id so they are in the same shard

    THIS DOESNT WORK FOR JUST THE COMMENT API BECAUSE THEYRE FORMATTED DIFFERENTLY

    Returns:
        "success message" if successful, else error message
    """

    es_client: Elasticsearch = Elasticsearch(
        config("ES_HOSTNAME"),
        verify_certs=False,
        ssl_show_warn=False,
        basic_auth=(config("ES_USERNAME"), config("ES_PASSWORD"))
    )

    # GET THE NEXT INCOMING FROM THE REDIS "oa_debate_data" QUEUE
    request_data: List[Dict[str, Any]] = request.get_json(force=True)
    current_app.logger.info(f'Processing {len(request_data)} debates')

    for debate in request_data:

        # check if its a "section" (really boring, just a single word like "bills" skip it)
        if (debate.get("section_id", -1) == "0") or (debate.get("subsection_id", -1) == "0"):
            current_app.logger.info(f"Skipping section: {debate.get('body', '')}")
            continue
        else:
            # its probably a normal debate, add it and any comments
            add_debate(es_client, debate)

    return f'added {len(request_data)} debates to the index, yay!'

