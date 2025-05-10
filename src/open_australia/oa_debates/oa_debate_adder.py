from typing import List, Dict, Any
from elasticsearch8 import Elasticsearch
from flask import current_app, request
from util import config


def format_debate(incoming_data: Dict[str, Any]) -> Dict[str, Any]:
    """ 
        Helper function
        Formats debate objects to match the mapping template to put into ES.
        Args:
            incoming_data: The raw debate json representation of a debate.
        
        Handles:
        - extracting and formatting the data to match the mapping template
        - if a field is not present, it will be set to an empty string
        - also connects the debate to its parent topic using the subsection_id
        
        Returns:
            a debate mapped and ready to go into the ES index. woo hoo!
    """

    try:
        formatted_data = {
            "id": incoming_data.get("epobject_id", ""),
            "gid": incoming_data.get("gid", ""),
            "parent_topic": incoming_data.get("parent", {}).get("body", ""),
            "date": incoming_data.get("hdate", ""),
            "transcript": incoming_data.get("body", ""),
            "speaker": {
                "first_name": incoming_data.get("speaker", {}).get("first_name", ""),
                "last_name": incoming_data.get("speaker", {}).get("last_name", ""),
                "party": incoming_data.get("speaker", {}).get("party", ""),
                "house": (incoming_data.get("speaker", {}).get("house", 0)),
                "state": incoming_data.get("speaker", {}).get("constituency", ""),
                "person_id": incoming_data.get("speaker", {}).get("person_id", ""),
                "position": incoming_data.get("speaker", {}).get("title", "")
            },
            "oa_relations":{
                "name": "debate",
                "parent": incoming_data.get("subsection_id", "")
            },

        }
        return formatted_data
    
    except Exception as e:
        current_app.logger.error(f"Error formatting data: {e}")
        raise ValueError("Failed to format incoming data to mapping template.")
    

def format_debate_topic(incoming_data: Dict[str, Any]) -> Dict[str, Any]:
    """ 
        Helper function
        Formats debate TOPIC objects to match the mapping template to put into ES.
        You can tell its a topic because it has a subsection id of 0, but not a section id of 0.
        
        Handles:
        - extracting and formatting the data to match the mapping template
        - if a field is not present, it will be set to an empty string
        - also lists it as a "debate_topic" in the oa_relations field

        Args:
            incoming_data: The raw data representation of a debate topic.
        Returns:
            a debate topic mapped and ready to go into the ES index. woo hoo!
    """

    formatted_data = {
        "debate_topic_title": incoming_data.get("body", ""),
        "date": incoming_data.get("hdate", ""),
        "debate_topic_section": incoming_data.get("section_id", ""),
        "id": incoming_data.get("epobject_id", ""),
        "gid": incoming_data.get("gid", ""),
        "oa_relations": {
            "name": "debate_topic",
        }
    }
    return formatted_data


def format_debate_comment(incoming_data: Dict[str, Any], parent_id) -> Dict[str, Any]:
    """ 
        Helper function
        Formats debate COMMENT objects to match the mapping template to put into ES.

        Handles:
        - extracting and formatting the data to match the mapping template
        - if a field is not present, it will be set to an empty string
        - also connects the comment to its parent debate using the debate id

        Args:
            incoming_data: The raw data representation of a debate comment.
        Returns:
            a debate comment mapped and ready to go into the ES index. woo hoo!
    """

    formatted_data = {
        "id": incoming_data.get("comment_id", ""),
        "user_id": incoming_data.get("user_id", ""),
        "user_name": incoming_data.get("username", ""),
        "comment": incoming_data.get("body", ""),
        "date": incoming_data.get("posted", "").split(" ")[0],
        "oa_relations": {
            "name": "debate_comment",
            "parent": parent_id
        }
    }   

    return formatted_data


def add_topic_to_index(es_client: Elasticsearch, debate: Dict[str, Any]) -> None:
    """
        Formats and adds a debate topic to the index.
        Does not check if it already exists.
        ROUTES BY THE YEAR AND MONTH IN THE FORMAT YYYY-MM
    """
    
    topic_mapped = format_debate_topic(debate)
    # actually add to index
    index_response: Dict[str, Any] = es_client.index(
        index='oa_debates_comments',
        id=topic_mapped.get("id"),
        body=topic_mapped,
        routing=topic_mapped.get("id"),
    )
    current_app.logger.info(
        f'Indexed topic {topic_mapped.get("id")} - Version: {index_response["_version"]}'
    )


def add_debate_to_index(es_client: Elasticsearch, debate: Dict[str, Any]) -> None:
    """
        Formats and adds a debate and any one attached comment to the index.
        Checks if either already exists.
        Routes them both by the subsection id.
        So they will be in the same shard (and as the subsection)

        Does not add the topic, that is done in the add_topic_to_index function.
        because it is fine if the parent does not exist yet.
    """

    # check if debate already exists
    if es_client.exists(index='oa_debates_comments', id=debate.get("epobject_id", "")):
        current_app.logger.info(f'Debate {debate.get("epobject_id", "no id")} already exists in the index.')

    else:
        # actually the parent DOESNT have to exist before you add the child
        # # make sure the topic exists, if not, add it 
        # if not (es_client.exists(index='oa_debates_comments', id=debate.get("subsection_id", -1))):
        #     add_topic_to_index(es_client, debate)

        try:
            debate_mapped = format_debate(debate)
            # actually add to index
            index_response: Dict[str, Any] = es_client.index(
                index='oa_debates_comments',
                id=debate_mapped.get("id"),
                body=debate_mapped,
                # route by the subsection id
                routing=debate_mapped.get("oa_relations", {}).get("parent", debate_mapped.get("id"))
            )
            current_app.logger.info(
                f'Indexed debate {debate_mapped.get("id")} - Version: {index_response["_version"]}'
            )
        except ValueError as e:
            current_app.logger.error(f"Error formatting data: {e}")

    # check if it has a comment
    comment = debate.get("comment", None)
    if comment:
        # only add to index if the comment is not already in the index
        if es_client.exists(index='oa_debates_comments', id=comment.get("comment_id", debate.get("epobject_id", ""))):
            current_app.logger.info(
                f'Comment {comment.get("comment_id", "no id")} already exists in the index.'
            )
        try:
            comment_mapped = format_debate_comment(comment, debate.get("epobject_id", -1))

            index_response: Dict[str, Any] = es_client.index(
                index='oa_debates_comments',
                id=comment_mapped.get("id"),
                body=comment_mapped,
                # route by the parent subsection
                routing=debate.get("subsection_id", -1)
            )
            current_app.logger.info(
            f'Indexed comment {comment_mapped.get("id")} - Version: {index_response["_version"]}'
        )

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
        if (debate.get("section_id", -1) == 0) and (debate.get("subsection_id", -1) == 0):
            current_app.logger.info(f"Skipping section: {debate.get('body', '')}")
            continue
        
        # check if its a subsection, not just a debate
        elif (debate.get("subsection_id", -1) == 0):
            add_topic_to_index(es_client, debate)
            
        # its probably a normal debate, add it and any comments
        else:
            add_debate_to_index(es_client, debate)


    return f'added {len(request_data)} debates to the index, yay!'
