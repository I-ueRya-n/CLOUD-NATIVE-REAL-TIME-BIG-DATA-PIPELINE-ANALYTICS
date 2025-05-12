import os
import praw
from flask import request, jsonify

# Validate and load Reddit credentials from environment variables
REQUIRED_ENV_VARS = ["REDDIT_CLIENT_ID", "REDDIT_CLIENT_SECRET", "REDDIT_USERNAME", "REDDIT_PASSWORD"]
missing_env_vars = [var for var in REQUIRED_ENV_VARS if not os.environ.get(var)]
if missing_env_vars:
    raise EnvironmentError(f"Missing required environment variables: {', '.join(missing_env_vars)}")

REDDIT_CLIENT_ID = os.environ["REDDIT_CLIENT_ID"]
REDDIT_CLIENT_SECRET = os.environ["REDDIT_CLIENT_SECRET"]
REDDIT_USERNAME = os.environ["REDDIT_USERNAME"]
REDDIT_PASSWORD = os.environ["REDDIT_PASSWORD"]
REDDIT_USER_AGENT = os.environ.get("REDDIT_USER_AGENT", "COMP90024_team57 Harvester by /u/yourusername")

# Initialize Reddit client
reddit = praw.Reddit(
    client_id=REDDIT_CLIENT_ID,
    client_secret=REDDIT_CLIENT_SECRET,
    username=REDDIT_USERNAME,
    password=REDDIT_PASSWORD,
    user_agent=REDDIT_USER_AGENT
)

def main(request):
    try:
        subreddits_param = request.args.get('subreddit')
        if not subreddits_param:
            return jsonify({"error": "Missing required parameter: 'subreddit'"}), 400

        limit_param = request.args.get('limit', '10')
        try:
            limit = int(limit_param)
        except ValueError:
            return jsonify({"error": "'limit' must be an integer."}), 400

        keywords_param = request.args.get('keywords', '')

        subreddit_list = [s.strip() for s in subreddits_param.split(',') if s.strip()]
        keyword_list = [k.strip().lower() for k in keywords_param.split(',') if k.strip()]

        posts = []
        for subreddit_name in subreddit_list:
            try:
                print(f"Fetching posts from subreddit: {subreddit_name} (limit={limit})")
                subreddit = reddit.subreddit(subreddit_name)
                for submission in subreddit.new(limit=limit):
                    post = {
                        'title': submission.title,
                        'author': str(submission.author),
                        'created_utc': submission.created_utc,
                        'selftext': submission.selftext,
                        'score': submission.score,
                        'num_comments': submission.num_comments,
                        'url': submission.url
                    }
                    posts.append(post)
            except Exception as e:
                print(f"Error fetching from subreddit '{subreddit_name}': {e}")
                return jsonify({"error": f"Error with subreddit '{subreddit_name}'", "details": str(e)}), 400

        # Keyword filtering
        if keyword_list:
            print(f"Filtering posts with keywords: {keyword_list}")
            posts = [
                post for post in posts
                if any(keyword in (post['title'] + ' ' + post['selftext']).lower() for keyword in keyword_list)
            ]

        print(f"Returning {len(posts)} posts")
        return jsonify(posts), 200

    except Exception as e:
        print(f"Unexpected error: {e}")
        return jsonify({"error": "Internal server error.", "details": str(e)}), 500
