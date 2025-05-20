from typing import Dict, List # Ensure List is imported from typing
from elasticsearch8 import Elasticsearch
from datetime import datetime # For local testing example

# Assuming AnalysisIterator is a custom class defined in 'iterator.py'
# and is available in the same directory or Python path.
from iterator import AnalysisIterator

def format_single_keyword_for_field(keyword: str, field_name: str) -> Dict:
    """
    Formats a single keyword for searching in a specific field.
    Handles '*' or empty/None as a wildcard (field exists).
    """
    if keyword == "*" or not keyword: # Handles empty string or None as wildcard
        return {"exists": {"field": field_name}}
    return {"match_phrase": {field_name: keyword}}

def reddit_query(keywords: List[str], start: str, end: str) -> Dict:
    """
    Constructs an Elasticsearch query for Reddit data.
    - Differentiates between posts (flair='post') and comments.
    - For posts, searches keywords in 'title' OR 'content'.
    - For comments, searches keywords in 'content'.
    - If multiple keywords are provided, they are treated with AND logic for the overall document match.
    - Handles '*' or empty/None keyword as a wildcard for the respective fields.
    """
    
    # Date range filter - common to all parts of the query
    date_range_filter = {
        "range": {
            "timestamp": { # Field name for date in Reddit data
                "gte": start,
                "lte": end
            }
        }
    }

    # If no keywords are provided, or only a wildcard, search for any content within the date range.
    if not keywords or (len(keywords) == 1 and (keywords[0] == "*" or not keywords[0])):
        query = {
            "bool": {
                "filter": [date_range_filter],
                "must": [ # Ensure there's some content to analyze
                    {
                        "bool": {
                            "should": [
                                {"exists": {"field": "title"}}, # For posts
                                {"exists": {"field": "content"}} # For posts or comments
                            ],
                            "minimum_should_match": 1
                        }
                    }
                ]
            }
        }
        # print(f"[reddit_query] Generated wildcard query: {json.dumps(query, indent=2)}") # For debugging
        return query

    # --- Logic for specific keywords ---

    # For posts (flair is 'post'):
    # Each keyword must be in (title OR content)
    post_keyword_conditions = []
    for kw in keywords:
        post_keyword_conditions.append({
            "bool": {
                "should": [
                    format_single_keyword_for_field(kw, "title"),
                    format_single_keyword_for_field(kw, "content")
                ],
                "minimum_should_match": 1 # Keyword must be in title OR content
            }
        })
    
    flair_post_query_part = {
        "bool": {
            "filter": [
                {"term": {"flair": "post"}} # Filter for documents where flair is 'post'
            ],
            "must": post_keyword_conditions # All keyword conditions (title OR content) must be met
        }
    }

    # For comments (flair is NOT 'post', or flair field might be missing for comments):
    # Each keyword must be in content
    comment_keyword_conditions = []
    for kw in keywords:
        comment_keyword_conditions.append(format_single_keyword_for_field(kw, "content"))

    # Assuming comments might not have 'flair: post' or might not have a flair field at all.
    # A robust way to identify comments could be "NOT (flair: post)" if flair always exists.
    # If flair can be missing for comments, this needs adjustment or rely on other fields.
    # For this example, let's assume comments are those not having flair='post'.
    flair_comment_query_part = {
        "bool": {
            "filter": [
                {
                    "bool": {
                        "must_not": [
                            {"term": {"flair": "post"}} # Filter for documents where flair is NOT 'post'
                        ]
                    }
                }
            ],
            "must": comment_keyword_conditions # All keyword conditions (in content) must be met
        }
    }
    
    # Final query: matches date range AND (is a matching post OR is a matching comment)
    final_query = {
        "bool": {
            "filter": [date_range_filter], # Apply date range to all
            "should": [
                flair_post_query_part,
                flair_comment_query_part
            ],
            "minimum_should_match": 1 # Document must be either a matching post or a matching comment
        }
    }
    # import json # For debugging
    # print(f"[reddit_query] Generated query: {json.dumps(final_query, indent=2)}") # For debugging
    return final_query


def reddit_sentiment(client: Elasticsearch, start: str, end: str, keyword: str) -> Dict:
    """
    Calculates the sentiment per day for data from Reddit.
    Aggregates sentiment scores (neg, neu, pos, compound) and counts for each day.

    Arguments:
    client  -- Elasticsearch client instance.
    start   -- Start date as a string 'YYYY-MM-DD'.
    end     -- End date as a string 'YYYY-MM-DD'.
    keyword -- Keyword to filter posts/comments by. Can be "*" or None/empty for wildcard.
    """
    data = {}
    # Ensure keywords is a list for reddit_query. Handle None/empty keyword as wildcard.
    query_keywords = [keyword] if keyword is not None and keyword != "" else ["*"]

    es_query = reddit_query(query_keywords, start, end)

    # Initialize the AnalysisIterator
    # The endpoint "/analysis/sentiment/v2" is assumed to be a Fission function
    # (likely the caching one: /analysis/sentiment/v2/index/{index}/field/{field})
    # that takes text and returns sentiment scores.
    # The AnalysisIterator needs to construct the full URL to the sentiment service.
    # For Reddit, the index is "reddit" and the field for sentiment is "content".
    sentiment_service_endpoint = f"/analysis/sentiment/v2/index/reddit/field/content"
    reddit_iter = AnalysisIterator(client, sentiment_service_endpoint, es_query, size=5000)
    
    # Specify which fields to retrieve from Elasticsearch for the 'reddit' index
    # 'content' will be sent for sentiment analysis.
    # 'timestamp' is used for grouping.
    # 'post_id' is for identification.
    reddit_iter.elastic_fields(index_name="reddit", id_field="post_id", content_field="content", date_field="timestamp")
    
    print(f"[reddit_sentiment] Iterator set up for keyword '{keyword}'. Starting iteration over Reddit data...") # English comment
    
    processed_count = 0
    for sentiment_result, post_data in reddit_iter:
        if post_data is None or sentiment_result is None:
            # print("[reddit_sentiment] Skipped a None post_data or sentiment_result.") # English comment
            continue

        post_date_str = post_data.get("timestamp") # This should be 'YYYY-MM-DD' string
        if not post_date_str:
            # print(f"[reddit_sentiment] Warning: Post {post_data.get('post_id')} is missing 'timestamp'. Skipping.") # English comment
            continue
        
        # Ensure post_date_key is just the date part if 'timestamp' is a full datetime string
        post_date_key = post_date_str.split("T")[0] if "T" in post_date_str else post_date_str

        if post_date_key not in data:
            data[post_date_key] = {
                "neg": 0.0,
                "neu": 0.0,
                "pos": 0.0,
                "compound": 0.0,
                "count": 0 # Initialize count for the day
            }

        # Aggregate sentiment scores
        for field in ["neg", "neu", "pos", "compound"]:
            data[post_date_key][field] += sentiment_result.get(field, 0.0) # Default to 0.0 if field missing
        data[post_date_key]["count"] += 1
        processed_count +=1

    print(f"[reddit_sentiment] Finished iterating. Processed {processed_count} items. Returning data for {len(data)} dates.") # English comment

    # If no posts were found matching the criteria for the entire period,
    # return an entry for the start date with zero sentiment and count.
    # This helps in plotting to show a baseline if no data exists for the entire range.
    if not data and start: 
        data[start] = {
            "neg": 0.0,
            "neu": 0.0,
            "pos": 0.0,
            "compound": 0.0,
            "count": 0
        }
    return data

# This __main__ block is for local testing and won't run when deployed in Fission.
if __name__ == "__main__":
    print("Running reddit_sentiment locally for testing (mocking ES and AnalysisIterator)...") # English comment
    
    # Mock Elasticsearch client for local testing
    class MockESClient:
        def ping(self):
            print("[MockESClient] Ping successful (mocked).") # English comment
            return True
        # Add other methods if AnalysisIterator calls them directly, e.g., search, scroll
        def search(self, index, query, size, scroll=None): # Mock search if needed
            print(f"[MockESClient] Search called on index '{index}' with query (first 100 chars): {str(query)[:100]}...") # English comment
            # Return a structure that AnalysisIterator expects, or make AnalysisIterator handle this mock
            return {"hits": {"hits": [], "total": {"value": 0}}, "_scroll_id": None}


    es_client_instance = MockESClient()

    # --- Mock AnalysisIterator for local testing ---
    # This replaces the actual AnalysisIterator when running this script directly.
    class MockAnalysisIterator:
        def __init__(self, client, endpoint, query, size=100):
            self.client = client
            self.endpoint = endpoint
            self.query = query # The ES query
            self.size = size
            self.elastic_index_name = ""
            self.id_field = ""
            self.content_field = ""
            self.date_field = ""
            print(f"[MockAnalysisIterator] Initialized. Endpoint: {self.endpoint}") # English comment
            # print(f"[MockAnalysisIterator] Query: {json.dumps(self.query, indent=2)}") # For debugging query

        def elastic_fields(self, index_name: str, id_field: str, content_field: str, date_field: str):
            self.elastic_index_name = index_name
            self.id_field = id_field
            self.content_field = content_field
            self.date_field = date_field
            print(f"[MockAnalysisIterator] Elastic fields set: index='{index_name}', id='{id_field}', content='{content_field}', date='{date_field}'") # English comment

        def __iter__(self):
            print(f"[MockAnalysisIterator] Starting iteration (mocked results)...") # English comment
            # Simulate some data based on the query (very simplified)
            # This mock assumes the query structure from the updated reddit_query.
            
            # Example mock posts - in a real scenario, these would come from ES based on self.query
            mock_posts_from_es = [
                {self.id_field: "r_id_1", self.content_field: "Reddit is a fantastic platform for positive news.", self.date_field: "2025-01-15", "flair": "post", "title": "Good News Today"},
                {self.id_field: "r_id_2", self.content_field: "Just a neutral discussion about Reddit features.", self.date_field: "2025-01-15", "flair": "comment"},
                {self.id_field: "r_id_3", self.content_field: "I had a very bad and negative time on Reddit yesterday.", self.date_field: "2025-01-16", "flair": "post", "title": "My Bad Day"},
                {self.id_field: "r_id_4", self.content_field: "This keyword 'housing' is important.", self.date_field: "2025-01-17", "flair": "post", "title": "Housing Crisis"},
                {self.id_field: "r_id_5", self.content_field: "Another post about housing.", self.date_field: "2025-01-17", "flair": "post", "title": "More on Housing"},
            ]
            # Corresponding mock sentiment results (as if from /analysis/sentiment/v2)
            mock_sentiment_results = [
                {"neg": 0.0, "neu": 0.2, "pos": 0.8, "compound": 0.88, "text_length": len(mock_posts_from_es[0][self.content_field])},
                {"neg": 0.1, "neu": 0.8, "pos": 0.1, "compound": 0.0,  "text_length": len(mock_posts_from_es[1][self.content_field])},
                {"neg": 0.9, "neu": 0.1, "pos": 0.0, "compound": -0.92,"text_length": len(mock_posts_from_es[2][self.content_field])},
                {"neg": 0.2, "neu": 0.6, "pos": 0.2, "compound": 0.0,  "text_length": len(mock_posts_from_es[3][self.content_field])},
                {"neg": 0.1, "neu": 0.7, "pos": 0.2, "compound": 0.1,  "text_length": len(mock_posts_from_es[4][self.content_field])},
            ]

            # Simplified date extraction from query for mock filtering
            start_date_filter = self.query.get("bool", {}).get("filter", [{}])[0].get("range", {}).get(self.date_field, {}).get("gte", "1900-01-01")
            end_date_filter = self.query.get("bool", {}).get("filter", [{}])[0].get("range", {}).get(self.date_field, {}).get("lte", "2999-12-31")
            
            # Simplified keyword extraction (takes the first keyword if specific, otherwise assumes wildcard)
            # This mock doesn't fully replicate the complex boolean logic of the real query.
            target_keyword = None
            try:
                # Attempt to find a specific keyword from the 'should' clauses
                should_clauses = self.query.get("bool", {}).get("should", [])
                if should_clauses:
                    # Look in the 'must' part of the first 'should' clause (e.g., post_keyword_conditions)
                    first_should_must = should_clauses[0].get("bool",{}).get("must",[])
                    if first_should_must:
                        # Look in the 'should' part of that (e.g., title OR content)
                        title_or_content_should = first_should_must[0].get("bool",{}).get("should",[])
                        if title_or_content_should:
                             if "match_phrase" in title_or_content_should[0]:
                                target_keyword = list(title_or_content_should[0]["match_phrase"].values())[0]
            except:
                pass # Keep target_keyword as None if extraction fails

            print(f"[MockAnalysisIterator] Filtering mock data for keyword '{target_keyword}' between {start_date_filter} and {end_date_filter}") # English comment

            for i, post in enumerate(mock_posts_from_es):
                post_date_obj = datetime.strptime(post[self.date_field], "%Y-%m-%d").date()
                start_dt = datetime.strptime(start_date_filter, "%Y-%m-%d").date()
                end_dt = datetime.strptime(end_date_filter, "%Y-%m-%d").date()

                # Mock keyword matching (very simplified)
                keyword_match = False
                if target_keyword is None or target_keyword == "*": # Wildcard
                    keyword_match = True
                else:
                    if target_keyword.lower() in post.get(self.content_field, "").lower() or \
                       target_keyword.lower() in post.get("title", "").lower(): # Check title too for posts
                        keyword_match = True
                
                if start_dt <= post_date_obj <= end_dt and keyword_match:
                    print(f"[MockAnalysisIterator] Yielding mock sentiment for post: {post[self.id_field]}") # English comment
                    yield mock_sentiment_results[i], post
            return

    # Replace the actual AnalysisIterator with the mock for local testing
    # This is a common technique for unit testing or local development when dependencies are complex.
    # In your Fission environment, the 'from iterator import AnalysisIterator' will import the real one.
    global AnalysisIterator 
    AnalysisIterator = MockAnalysisIterator 
    # This global replacement is generally not ideal for larger projects but works for a single script test.
    # A better way for testing would be dependency injection or using a testing framework's mock capabilities.

    # Test case 1: Specific keyword and date range
    test_start_date = "2025-01-10"
    test_end_date = "2025-01-20"
    test_keyword = "housing" 
    
    print(f"\n--- Test Case 1: Keyword '{test_keyword}', Dates: {test_start_date} to {test_end_date} ---") # English comment
    sentiment_data = reddit_sentiment(es_client_instance, test_start_date, test_end_date, test_keyword)
    print("Sentiment Data Received:") # English comment
    for day, scores in sorted(sentiment_data.items()):
        print(f"  {day}: Compound={scores.get('compound'):.2f}, Pos={scores.get('pos'):.2f}, Neu={scores.get('neu'):.2f}, Neg={scores.get('neg'):.2f}, Count={scores.get('count')}") # English comment

    # Test case 2: Wildcard keyword
    test_keyword_wildcard = "*"
    print(f"\n--- Test Case 2: Keyword '{test_keyword_wildcard}', Dates: {test_start_date} to {test_end_date} ---") # English comment
    sentiment_data_wildcard = reddit_sentiment(es_client_instance, test_start_date, test_end_date, test_keyword_wildcard)
    print("Sentiment Data Received (Wildcard):") # English comment
    for day, scores in sorted(sentiment_data_wildcard.items()):
        print(f"  {day}: Compound={scores.get('compound'):.2f}, Pos={scores.get('pos'):.2f}, Neu={scores.get('neu'):.2f}, Neg={scores.get('neg'):.2f}, Count={scores.get('count')}") # English comment

    # Test case 3: No data expected (date range outside mock data)
    test_start_date_no_data = "2024-01-01"
    test_end_date_no_data = "2024-01-05"
    print(f"\n--- Test Case 3: Keyword '{test_keyword}', Dates: {test_start_date_no_data} to {test_end_date_no_data} (expecting baseline) ---") # English comment
    sentiment_data_no_data = reddit_sentiment(es_client_instance, test_start_date_no_data, test_end_date_no_data, test_keyword)
    print("Sentiment Data Received (No Data Expected):") # English comment
    for day, scores in sorted(sentiment_data_no_data.items()):
         print(f"  {day}: Compound={scores.get('compound'):.2f}, Pos={scores.get('pos'):.2f}, Neu={scores.get('neu'):.2f}, Neg={scores.get('neg'):.2f}, Count={scores.get('count')}") # English comment

