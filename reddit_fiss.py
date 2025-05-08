import os
import praw
from flask import request, jsonify

# Reddit credentials from environment variables
REDDIT_CLIENT_ID = os.environ.get("REDDIT_CLIENT_ID")
REDDIT_CLIENT_SECRET = os.environ.get("REDDIT_CLIENT_SECRET")
REDDIT_USERNAME = os.environ.get("REDDIT_USERNAME")
REDDIT_PASSWORD = os.environ.get("REDDIT_PASSWORD")
REDDIT_USER_AGENT = os.environ.get("REDDIT_USER_AGENT", "COMP90024_team57 Harvester by /u/yourusername")

reddit = praw.Reddit(
    client_id=REDDIT_CLIENT_ID,
    client_secret=REDDIT_CLIENT_SECRET,
    username=REDDIT_USERNAME,
    password=REDDIT_PASSWORD,
    user_agent=REDDIT_USER_AGENT
)

def main(request):
    try:
        # Parse query parameters
        subreddits_param = request.args.get('subreddit', '')
        limit = int(request.args.get('limit', 10))  # default to 10 if not specified
        keywords_param = request.args.get('keywords', '')

        subreddit_list = [s.strip() for s in subreddits_param.split(',') if s.strip()]
        keyword_list = [k.strip().lower() for k in keywords_param.split(',') if k.strip()]

        posts = []
        for subreddit_name in subreddit_list:
            try:
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
                # Handle PRAW exceptions
                return jsonify({"error": f"Error with subreddit '{subreddit_name}': {str(e)}"}), 400

        # Keyword filtering
        if keyword_list:
            filtered_posts = []
            for post in posts:
                text = (post['title'] + ' ' + post['selftext']).lower()
                if any(keyword in text for keyword in keyword_list):
                    filtered_posts.append(post)
            posts = filtered_posts

        return jsonify(posts)

    except ValueError:
        return jsonify({"error": "Invalid 'limit' parameter. Must be an integer."}), 400
    except Exception as e:
        print(f"Unexpected error: {e}")
        return jsonify({"error": "Internal server error.", "details": str(e)}), 500