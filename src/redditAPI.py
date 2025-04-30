import os
import praw
from flask import Flask, request, jsonify

app = Flask(__name__) # app location 

# Testing (Hard code)
"""
REDDIT_CLIENT_ID = os.environ.get("REDDIT_CLIENT_ID", "ZFZjHYS9Inkn8Eg9Z_QoKQ")
REDDIT_CLIENT_SECRET = os.environ.get("REDDIT_CLIENT_SECRET", "")
REDDIT_USERNAME = os.environ.get("REDDIT_USERNAME", "Traditional_Rock_556")
REDDIT_PASSWORD = os.environ.get("REDDIT_PASSWORD", "")
REDDIT_USER_AGENT = "COMP90024_team57 Harvester by /u/Traditional_Rock_556"

"""

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
    user_agent=REDDIT_USER_AGENT)


@app.route('/reddit', methods=['GET'])
def get_reddit_posts():
    try:
        # Parse query parameters
        subreddits_param = request.args.get('subreddit', '')
        # Data input pipeline
        limit = int(request.args.get('limit')) 
        keywords_param = request.args.get('keywords', '')
        # Fetching multiple themes
        subreddit_list = [s.strip() for s in subreddits_param.split(',') if s.strip()]
        # Fetching multiple keywords
        keyword_list = [k.strip().lower() for k in keywords_param.split(',') if k.strip()]

        # E.g. http://127.0.0.1:5000//reddit?subreddit=australia,melbourne,sydney,brisbane&limit=50&keywords=coffee,cafe,brunch,sandich

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
            except prawcore.exceptions.NotFound:
                # Subreddit does not exist
                return jsonify({"error": f"Subreddit '{subreddit_name}' not found."}), 404
            except prawcore.exceptions.Forbidden:
                # Subreddit is private or banned
                return jsonify({"error": f"Subreddit '{subreddit_name}' is private or banned."}), 403
            except prawcore.exceptions.PrawcoreException as e:
                # Other Reddit API errors
                return jsonify({"error": f"Reddit API error for '{subreddit_name}': {str(e)}"}), 502

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
    except prawcore.exceptions.OAuthException:
        return jsonify({"error": "Reddit authentication failed. Check your credentials."}), 401
    except Exception as e:
        # Log the error for debugging (print or use logging)
        print(f"Unexpected error in /reddit endpoint: {e}")
        return jsonify({"error": "Internal server error.", "details": str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
