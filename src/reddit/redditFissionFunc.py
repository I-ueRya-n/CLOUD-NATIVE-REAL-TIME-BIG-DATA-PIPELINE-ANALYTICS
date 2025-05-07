import os
import praw
import prawcore
from elasticsearch import Elasticsearch

# Initialize Elasticsearch client
es = Elasticsearch([{'host': 'localhost', 'port': 9200}])

# Index data into Elasticsearch
def index_to_elasticsearch(post):
    es.index(index='reddit-posts', document=post

def main(req):
    """
    Fission-compatible Reddit harvester function.
    Expects query parameters:
    - subreddit: comma-separated subreddit names (e.g., australia,melbourne)
    - limit: number of posts per subreddit (default: 10)
    - keywords: comma-separated keywords for filtering (optional)
    Returns: JSON list of posts.
    """

    # Get query parameters
    params = req.get("query", {})
    subreddits_param = params.get("subreddit", "")
    limit = int(params.get("limit", 10))
    keywords_param = params.get("keywords", "")

    subreddit_list = [s.strip() for s in subreddits_param.split(",") if s.strip()]
    keyword_list = [k.strip().lower() for k in keywords_param.split(",") if k.strip()]

    # Reddit API credentials from environment variables (set in Fission/K8s secret)
    REDDIT_CLIENT_ID = os.environ.get("REDDIT_CLIENT_ID")
    REDDIT_CLIENT_SECRET = os.environ.get("REDDIT_CLIENT_SECRET")
    REDDIT_USERNAME = os.environ.get("REDDIT_USERNAME")
    REDDIT_PASSWORD = os.environ.get("REDDIT_PASSWORD")
    REDDIT_USER_AGENT = os.environ.get("REDDIT_USER_AGENT", "COMP90024_teamXX Harvester")

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
                posts.append(post)
        except prawcore.exceptions.NotFound:
            # Subreddit does not exist
            return {
                "statusCode": 404,
                "body": {"error": f"Subreddit '{subreddit_name}' not found."}
            }
        except prawcore.exceptions.Forbidden:
            # Subreddit is private or banned
            return {
                "statusCode": 403,
                "body": {"error": f"Subreddit '{subreddit_name}' is private or banned."}
            }
        except prawcore.exceptions.PrawcoreException as e:
            # Other Reddit API errors
            return {
                "statusCode": 502,
                "body": {"error": f"Reddit API error for '{subreddit_name}': {str(e)}"}
            }
        except Exception as e:
            return {
                "statusCode": 500,
                "body": {"error": f"Unexpected error for '{subreddit_name}': {str(e)}"}
            }

    # Keyword filtering (if any)
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