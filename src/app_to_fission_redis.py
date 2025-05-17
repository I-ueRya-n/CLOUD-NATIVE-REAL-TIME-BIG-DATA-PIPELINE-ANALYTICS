import os
import praw
import prawcore # For praw exceptions
import requests # For making HTTP requests to Fission
from flask import Flask, request, jsonify

app = Flask(__name__)

# --- Reddit API 配置 ---

REDDIT_CLIENT_ID = "ZFZjHYS9Inkn8Eg9Z_QoKQ"
REDDIT_CLIENT_SECRET = "oStU1IMaW9b3mvQucsEZNcyoqjeX1w"
REDDIT_USERNAME = "Traditional_Rock_556"
REDDIT_PASSWORD = "04U@nimelb25624426"
REDDIT_USER_AGENT = "COMP90024_team57 Harvester by /u/Traditional_Rock_556"

# --- Fission Pipeline 配置 ---
FISSION_ENQUEUE_URL = os.environ.get("FISSION_ENQUEUE_URL") # 例如: http://localhost:9090/enqueue/reddit_data

# 初始化 PRAW
reddit = None
if all([REDDIT_CLIENT_ID, REDDIT_CLIENT_SECRET, REDDIT_USERNAME, REDDIT_PASSWORD, REDDIT_USER_AGENT]):
    try:
        reddit = praw.Reddit(
            client_id="ZFZjHYS9Inkn8Eg9Z_QoKQ",
            client_secret="oStU1IMaW9b3mvQucsEZNcyoqjeX1w",
            username="Traditional_Rock_556",
            password="04U@nimelb25624426",
            user_agent="COMP90024_team57 Harvester by /u/Traditional_Rock_556",
            check_for_async=False # 根據您的 PRAW 版本和使用情境調整
        )
        print("PRAW client initialized successfully.")
    except Exception as e:
        print(f"Error initializing PRAW client: {e}")
        reddit = None
else:
    print("Reddit API credentials missing in environment variables. PRAW client not initialized.")


@app.route('/reddit_to_pipeline', methods=['GET'])
def get_reddit_posts_and_send_to_pipeline():
    if not reddit:
        return jsonify({"error": "PRAW client not initialized. Check Reddit credentials and server logs."}), 500
    if not FISSION_ENQUEUE_URL:
        return jsonify({"error": "FISSION_ENQUEUE_URL not set in environment variables."}), 500

    try:
        subreddits_param = request.args.get('subreddit', 'australia') # 預設值
        try:
            limit = int(request.args.get('limit', 10)) # 預設值
            if limit <= 0 or limit > 100: # 避免過大的請求
                limit = 10
        except ValueError:
            return jsonify({"error": "Invalid 'limit' parameter. Must be an integer."}), 400
        
        keywords_param = request.args.get('keywords', '')

        subreddit_list = [s.strip() for s in subreddits_param.split(',') if s.strip()]
        keyword_list = [k.strip().lower() for k in keywords_param.split(',') if k.strip()]

        all_fetched_posts = []
        for subreddit_name in subreddit_list:
            try:
                print(f"Fetching posts from subreddit: {subreddit_name}")
                subreddit_instance = reddit.subreddit(subreddit_name)
                for submission in subreddit_instance.new(limit=limit):
                    post = {
                        'id': submission.id,
                        'title': submission.title,
                        'author': str(submission.author), # 可能為 None
                        'created_utc': submission.created_utc,
                        'selftext': submission.selftext,
                        'score': submission.score,
                        'num_comments': submission.num_comments,
                        'url': submission.url,
                        'permalink': submission.permalink,
                        'subreddit': subreddit_name # 加入 subreddit 名稱
                    }
                    all_fetched_posts.append(post)
            except prawcore.exceptions.NotFound:
                print(f"Subreddit '{subreddit_name}' not found.")
                # 可以選擇繼續處理其他 subreddits 或返回錯誤
                # return jsonify({"error": f"Subreddit '{subreddit_name}' not found."}), 404
            except prawcore.exceptions.Forbidden:
                print(f"Subreddit '{subreddit_name}' is private or banned.")
                # return jsonify({"error": f"Subreddit '{subreddit_name}' is private or banned."}), 403
            except prawcore.exceptions.PrawcoreException as e:
                print(f"Reddit API error for '{subreddit_name}': {str(e)}")
                # return jsonify({"error": f"Reddit API error for '{subreddit_name}': {str(e)}"}), 502
            except Exception as e:
                print(f"An unexpected error occurred while fetching from '{subreddit_name}': {e}")
                # return jsonify({"error": f"Unexpected error fetching from '{subreddit_name}': {str(e)}"}), 500
        
        # 關鍵字過濾
        posts_to_send_to_pipeline = []
        if keyword_list:
            for post in all_fetched_posts:
                # 確保 title 和 selftext 存在且為字串
                title_text = post.get('title', '') or ''
                selftext_content = post.get('selftext', '') or ''
                text_to_search = (title_text + ' ' + selftext_content).lower()
                if any(keyword in text_to_search for keyword in keyword_list):
                    posts_to_send_to_pipeline.append(post)
        else:
            posts_to_send_to_pipeline = all_fetched_posts

        # 將處理後的貼文發送到 Fission enqueue 服務
        successful_submissions_count = 0
        failed_submissions_details = []

        print(f"Attempting to send {len(posts_to_send_to_pipeline)} posts to Fission pipeline at {FISSION_ENQUEUE_URL}")
        for post_data in posts_to_send_to_pipeline:
            try:
                response = requests.post(FISSION_ENQUEUE_URL, json=post_data, headers={'Content-Type': 'application/json'}, timeout=10) # 增加 timeout
                response.raise_for_status() # 如果 HTTP 狀態碼是 4xx 或 5xx，則拋出異常
                successful_submissions_count += 1
            except requests.exceptions.RequestException as e:
                error_message = f"Error sending post (ID: {post_data.get('id', 'N/A')}) to Fission: {e}"
                print(error_message)
                failed_submissions_details.append({"post_id": post_data.get('id', 'N/A'), "error": str(e)})
        
        return jsonify({
            "message": "Reddit data fetching and pipeline submission process completed.",
            "total_fetched_from_reddit": len(all_fetched_posts),
            "posts_matching_keywords": len(posts_to_send_to_pipeline),
            "successful_submissions_to_pipeline": successful_submissions_count,
            "failed_submissions_to_pipeline": len(failed_submissions_details),
            "failure_details": failed_submissions_details
        })

    except prawcore.exceptions.OAuthException:
        return jsonify({"error": "Reddit authentication failed. Check your credentials."}), 401
    except Exception as e:
        print(f"Unexpected error in /reddit_to_pipeline endpoint: {e}") # 伺服器端日誌
        return jsonify({"error": "An internal server error occurred.", "details": str(e)}), 500

if __name__ == '__main__':
    # 確保設定了所有必要的環境變數
    required_vars = ["REDDIT_CLIENT_ID", "REDDIT_CLIENT_SECRET", "REDDIT_USERNAME", "REDDIT_PASSWORD", "REDDIT_USER_AGENT", "FISSION_ENQUEUE_URL"]
    missing_vars = [var for var in required_vars if not os.environ.get(var)]
    if missing_vars:
        print(f"Error: Missing required environment variables: {', '.join(missing_vars)}")
    else:
        app.run(host='0.0.0.0', port=5000, debug=True) # debug=True 僅用於開發