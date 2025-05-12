import os
import json
import praw
from flask import request, jsonify
from util import enqueue_data

def main():
    # Reddit API credentials from environment variables
    reddit = praw.Reddit(
        client_id=os.environ.get("REDDIT_CLIENT_ID"),
        client_secret=os.environ.get("REDDIT_CLIENT_SECRET"),
        username=os.environ.get("REDDIT_USERNAME"),
        password=os.environ.get("REDDIT_PASSWORD"),
        user_agent=os.environ.get("REDDIT_USER_AGENT", "RedditHarvester/1.0")
    )

    # Parse request parameters
    subreddits = request.args.get('subreddits', '').split(',')
    limit = int(request.args.get('limit', 10))
    keywords = request.args.get('keywords', '').split(',')

    posts = []
    for subreddit in subreddits:
        for submission in reddit.subreddit(subreddit).new(limit=limit):
            if any(keyword.lower() in submission.title.lower() for keyword in keywords):
                post = {
                    'post_id': submission.id,
                    'title': submission.title,
                    'content': submission.selftext,
                    'author': str(submission.author),
                    'created_at': submission.created_utc,
                    'upvotes': submission.score,
                    'comments_count': submission.num_comments,
                    'subreddit': subreddit,
                    'url': submission.url
                }
                posts.append(post)
                enqueue_data('reddit_posts_queue', json.dumps(post))

    return jsonify({'message': f'Enqueued {len(posts)} posts.'})