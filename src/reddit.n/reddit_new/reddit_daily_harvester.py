import json
from datetime import date, datetime, timezone, timedelta 
import praw
from util import enqueue_data, config 


DAILY_SUBREDDITS = ["melbourne", "australia", "auspol", "sydney", "brisbane", "aussie", "australianpolitics"]
DAILY_KEYWORDS = ["election", "government", "policy", "housing", "cost of living", "environment", "health", "vote", "federal"]




DAILY_LIMIT_PER_KEYWORD_SUBREDDIT = 10000 
DAILY_SORT_METHOD = "new" 
DAILY_SCRAPE_DAYS_AGO = 365 

def get_post_comments_for_daily(reddit_client, post, limit=10):
    """
    Similar to get_post_comments in reddit_harvester.py,
    but ensures it enqueues data to the correct queue and can operate independently.
    """
    post.comments.replace_more(limit=0) # Get all top-level comments
    curr_date = datetime.now(timezone.utc).isoformat()
    parsed_comments = []
    for comment in post.comments.list():
        timestamp_utc = getattr(comment, 'created_utc', None)
        if timestamp_utc is not None:
            timestamp_str = datetime.fromtimestamp(timestamp_utc, tz=timezone.utc).strftime('%Y-%m-%d')
        else:
            timestamp_str = None

        
        if comment.parent_id == comment.link_id:
            parsed_comments.append({
                'post_id': getattr(comment, 'id', None),
                'title': "Parent: " + getattr(post, 'title', ""), # Using parent post's title
                'author': str(getattr(comment, 'author', None)),
                'content': getattr(comment, 'body', None),
                'timestamp': timestamp_str,
                'harvested_at': curr_date,
                'url': getattr(comment, 'permalink', None),
                'subreddit': getattr(getattr(post, 'subreddit', None), 'display_name', None),
                'upvotes': getattr(comment, 'score', None),
                'flair': "comment"
            })

    if parsed_comments:
        enqueue_data('reddit_posts_queue', json.dumps(parsed_comments))
        print(f"Daily Harvester: Enqueued {len(parsed_comments)} comments for post {getattr(post, 'id', None)} to redis queue")
    return len(parsed_comments)

def main():
    print("Daily Reddit Harvester: Starting job...")
    try:
        # Read Reddit API credentials from ConfigMap
        reddit_client = praw.Reddit(
            client_id=config("REDDIT_CLIENT_ID"),
            client_secret=config("REDDIT_CLIENT_SECRET"),
            username=config("REDDIT_USERNAME"),
            password=config("REDDIT_PASSWORD"),
            user_agent=config("REDDIT_USER_AGENT")
        )
        print("Daily Reddit Harvester: Successfully initialized Reddit client.")
    except Exception as e:
        print(f"Daily Reddit Harvester: Error initializing Reddit client: {e}")
        return json.dumps({"error": f"Error initializing Reddit client: {e}"}), 500

    # Set the time range for scraping
    # scrape_until_date is always today for this "daily" harvester logic.
    # scrape_from_date goes back N days as specified by DAILY_SCRAPE_DAYS_AGO.
    scrape_until_date = date.today()
    scrape_from_date = scrape_until_date - timedelta(days=DAILY_SCRAPE_DAYS_AGO)

    print(f"Daily Reddit Harvester: Scraping posts from {scrape_from_date.isoformat()} to {scrape_until_date.isoformat()} (inclusive)")
    print(f"Daily Reddit Harvester: Config: DAILY_SCRAPE_DAYS_AGO = {DAILY_SCRAPE_DAYS_AGO}, DAILY_LIMIT_PER_KEYWORD_SUBREDDIT = {DAILY_LIMIT_PER_KEYWORD_SUBREDDIT}")

    curr_date_iso = datetime.now(timezone.utc).isoformat()
    total_posts_enqueued_session = 0

    for subreddit_name in DAILY_SUBREDDITS:
        print(f"Daily Reddit Harvester: Scraping subreddit: r/{subreddit_name}")
        try:
            subreddit_obj = reddit_client.subreddit(subreddit_name)
            for keyword in DAILY_KEYWORDS:
                print(f"Daily Reddit Harvester: Scraping keyword '{keyword}' in r/{subreddit_name}")
                posts_for_queue = []
                query = f'title:"{keyword}"'

                # PRAW's search with time_filter='all' gets the 'limit' newest posts matching the query.
                # The Python date filtering below then narrows these down to your defined window.
                found_posts = subreddit_obj.search(
                    query=query,
                    sort=DAILY_SORT_METHOD,
                    time_filter='all', # Search across all time, then filter by date in Python
                    limit=DAILY_LIMIT_PER_KEYWORD_SUBREDDIT
                )

                for post in found_posts:
                    post_created_utc_date = datetime.fromtimestamp(post.created_utc, tz=timezone.utc).date()

                    # Filter posts to be within the desired date range
                    if scrape_from_date <= post_created_utc_date <= scrape_until_date:
                        timestamp_utc = getattr(post, 'created_utc', None)
                        if timestamp_utc is not None:
                            timestamp_str = datetime.fromtimestamp(timestamp_utc, tz=timezone.utc).strftime('%Y-%m-%d')
                        else:
                            timestamp_str = None

                        post_data = {
                            'post_id': getattr(post, 'id', None),
                            'title': getattr(post, 'title', None),
                            'content': getattr(post, 'selftext', None),
                            'author': str(getattr(post, 'author', None)),
                            'timestamp': timestamp_str,
                            'upvotes': getattr(post, 'score', None),
                            'comments_count': getattr(post, 'num_comments', None),
                            'subreddit': subreddit_name,
                            'url': getattr(post, 'url', None),
                            'keyword': keyword,
                            'harvested_at': curr_date_iso,
                            'flair': "post",
                        }
                        posts_for_queue.append(post_data)

                if posts_for_queue:
                    enqueue_data('reddit_posts_queue', json.dumps(posts_for_queue))
                    total_posts_enqueued_session += len(posts_for_queue)
                    print(f"Daily Harvester: Enqueued {len(posts_for_queue)} posts for keyword '{keyword}' in r/{subreddit_name} to redis queue (within the {DAILY_SCRAPE_DAYS_AGO}-day window)")
                else:
                    print(f"Daily Harvester: No new posts found for keyword '{keyword}' in r/{subreddit_name} within the {DAILY_SCRAPE_DAYS_AGO}-day window.")

        except Exception as e:
            print(f"Daily Reddit Harvester: Error processing subreddit r/{subreddit_name}. Keyword: '{keyword if 'keyword' in locals() else 'N/A'}'. Error: {e}")
            continue

    print(f"Daily Reddit Harvester: Job finished. Total new posts enqueued in this session: {total_posts_enqueued_session}")
    return json.dumps({'message': f'Daily Reddit harvest completed. Enqueued {total_posts_enqueued_session} posts within the {DAILY_SCRAPE_DAYS_AGO}-day window.'}), 200

if __name__ == "__main__":
    print("Running daily harvester locally (for testing)...")
    # Add local testing setup if needed, e.g., mocking 'config' and 'enqueue_data'
    pass
