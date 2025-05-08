import os
import praw
import prawcore
from elasticsearch import Elasticsearch

def index_to_elasticsearch(es, post):
    es.index(index='reddit-posts', document=post)

def main(req):
    # Try to get query parameters (for GET) or JSON body (for POST)
    params = req.args or {}
    data = req.get_json(silent=True) or {}

    # Prefer query params, fallback to JSON body
    subreddit_param = params.get("subreddit") or data.get("subreddit") or "AustralianPolitics"
    limit = int(params.get("limit") or data.get("limit") or 100)
    keywords_param = params.get("keywords") or data.get("keywords") or ""

    subreddit_list = [s.strip() for s in subreddit_param.split(",") if s.strip()]
    keyword_list = [k.strip().lower() for k in keywords_param.split(",") if k.strip()]

    # Reddit API credentials from environment variables
    REDDIT_CLIENT_ID = os.environ.get("REDDIT_CLIENT_ID")
    REDDIT_CLIENT_SECRET = os.environ.get("REDDIT_CLIENT_SECRET")
    REDDIT_USERNAME = os.environ.get("REDDIT_USERNAME")
    REDDIT_PASSWORD = os.environ.get("REDDIT_PASSWORD")
    REDDIT_USER_AGENT = os.environ.get("REDDIT_USER_AGENT", "COMP90024_teamXX Harvester")

    # Elasticsearch credentials from environment variables
    ES_HOST = os.environ.get("ES_HOST", "localhost")
    ES_PORT = int(os.environ.get("ES_PORT", 9200))
    ES_USERNAME = os.environ.get("ES_USERNAME")
    ES_PASSWORD = os.environ.get("ES_PASSWORD")

    # Initialize Elasticsearch client
    es = Elasticsearch(
        [{"host": ES_HOST, "port": ES_PORT}],
        http_auth=(ES_USERNAME, ES_PASSWORD),
        scheme="https" if str(ES_PORT) == "443" or str(ES_PORT) == "9200" else "http",
        verify_certs=False
    )

    # Authenticate with Reddit
    try:
        reddit = praw.Reddit(
            client_id=REDDIT_CLIENT_ID,
            client_secret=REDDIT_CLIENT_SECRET,
            username=REDDIT_USERNAME,
            password=REDDIT_PASSWORD,
            user_agent=REDDIT_USER_AGENT
        )
    except Exception as e:
        return {
            "statusCode": 500,
            "body": {"error": f"Reddit authentication failed: {str(e)}"}
        }

    posts = []
    for subreddit_name in subreddit_list:
        try:
            subreddit = reddit.subreddit(subreddit_name)
            for submission in subreddit.new(limit=limit):
                post = {
                    'subreddit': subreddit_name,
                    'title': submission.title,
                    'author': str(submission.author),
                    'created_utc': submission.created_utc,
                    'selftext': submission.selftext,
                    'score': submission.score,
                    'num_comments': submission.num_comments,
                    'url': submission.url
                }
                # Index into Elasticsearch
                index_to_elasticsearch(es, post)
                posts.append(post)
        except prawcore.exceptions.NotFound:
            return {
                "statusCode": 404,
                "body": {"error": f"Subreddit '{subreddit_name}' not found."}
            }
        except prawcore.exceptions.Forbidden:
            return {
                "statusCode": 403,
                "body": {"error": f"Subreddit '{subreddit_name}' is private or banned."}
            }
        except prawcore.exceptions.PrawcoreException as e:
            return {
                "statusCode": 502,
                "body": {"error": f"Reddit API error for '{subreddit_name}': {str(e)}"}
            }
        except Exception as e:
            return {
                "statusCode": 500,
                "body": {"error": f"Unexpected error for '{subreddit_name}': {str(e)}"}
            }

    # Keyword filtering (optional)
    if keyword_list:
        filtered_posts = []
        for post in posts:
            text = (post['title'] + ' ' + post['selftext']).lower()
            if any(keyword in text for keyword in keyword_list):
                filtered_posts.append(post)
        posts = filtered_posts

    return {
        "statusCode": 200,
        "body": posts
    }
