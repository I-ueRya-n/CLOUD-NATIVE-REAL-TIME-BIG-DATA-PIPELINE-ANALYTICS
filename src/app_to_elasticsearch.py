import os
import praw
import prawcore # For praw exceptions
from elasticsearch import Elasticsearch, exceptions as es_exceptions
from elasticsearch.helpers import bulk as es_bulk
from flask import Flask, request, jsonify

app = Flask(__name__)



# --- Elasticsearch 配置 ---
ES_HOSTS = os.environ.get("ES_HOSTS", "http://localhost:9200").split(',')
ES_USERNAME = os.environ.get("ES_USERNAME")
ES_PASSWORD = os.environ.get("ES_PASSWORD")
ES_INDEX_NAME = os.environ.get("ES_INDEX_NAME", "reddit_posts_manual")
ES_VERIFY_CERTS_STR = os.environ.get("ES_VERIFY_CERTS", "true").lower()
ES_VERIFY_CERTS = ES_VERIFY_CERTS_STR == "true"
ES_CLOUD_ID = os.environ.get("ES_CLOUD_ID") # For Elastic Cloud

# 初始化 PRAW
reddit = None
if all([REDDIT_CLIENT_ID, REDDIT_CLIENT_SECRET, REDDIT_USERNAME, REDDIT_PASSWORD, REDDIT_USER_AGENT]):
    try:
        reddit = praw.Reddit(
            client_id="ZFZjHYS9Inkn8Eg9Z_QoKQ",
            client_secret="oStU1IMaW9b3mvQucsEZNcyoqjeX1w",
            username="Traditional_Rock_556",
            assword="04U@nimelb25624426",
            user_agent="COMP90024_team57 Harvester by /u/Traditional_Rock_556",
            check_for_async=False
        )
        print("PRAW client initialized successfully.")
    except Exception as e:
        print(f"Error initializing PRAW client: {e}")
        reddit = None
else:
    print("Reddit API credentials missing in environment variables. PRAW client not initialized.")

# 初始化 Elasticsearch Client
es_client = None
if ES_CLOUD_ID:
    if ES_USERNAME and ES_PASSWORD:
        try:
            es_client = Elasticsearch(
                cloud_id=ES_CLOUD_ID,
                basic_auth=(ES_USERNAME, ES_PASSWORD)
            )
            if es_client.ping():
                print("Elasticsearch client (Cloud ID) initialized and connected successfully.")
            else:
                print("Elasticsearch client (Cloud ID) initialized but ping failed.")
                es_client = None
        except Exception as e:
            print(f"Error initializing Elasticsearch client (Cloud ID): {e}")
            es_client = None
    else:
        print("ES_USERNAME and ES_PASSWORD are required for ES_CLOUD_ID. Elasticsearch client not initialized.")
elif ES_HOSTS and ES_HOSTS[0]: # Check if ES_HOSTS is not empty
    auth_params = {}
    if ES_USERNAME and ES_PASSWORD:
        auth_params['basic_auth'] = (ES_USERNAME, ES_PASSWORD)
    if not ES_VERIFY_CERTS:
        auth_params['verify_certs'] = False
        # 警告：在生產環境中禁用證書驗證有安全風險
        print("Warning: Elasticsearch certificate verification is disabled. This is not recommended for production.")
    
    try:
        es_client = Elasticsearch(
            ES_HOSTS,
            **auth_params
        )
        if es_client.ping():
            print("Elasticsearch client initialized and connected successfully.")
        else:
            print("Elasticsearch client initialized but ping failed.")
            es_client = None # 標記為未成功連接
    except Exception as e:
        print(f"Error initializing Elasticsearch client: {e}")
        es_client = None
else:
    print("Elasticsearch connection details (ES_HOSTS or ES_CLOUD_ID) missing. Elasticsearch client not initialized.")


@app.route('/reddit_to_es', methods=['GET'])
def get_reddit_posts_and_send_to_es():
    if not reddit:
        return jsonify({"error": "PRAW client not initialized. Check Reddit credentials and server logs."}), 500
    if not es_client:
        return jsonify({"error": "Elasticsearch client not initialized. Check ES connection details and server logs."}), 500

    try:
        subreddits_param = request.args.get('subreddit', 'australia')
        try:
            limit = int(request.args.get('limit', 10))
            if limit <= 0 or limit > 100:
                limit = 10
        except ValueError:
            return jsonify({"error": "Invalid 'limit' parameter. Must be an integer."}), 400
        
        keywords_param = request.args.get('keywords', '')

        subreddit_list = [s.strip() for s in subreddits_param.split(',') if s.strip()]
        keyword_list = [k.strip().lower() for k in keywords_param.split(',') if k.strip()]

        all_fetched_posts = []
        # (與版本一相同的 PRAW 資料獲取邏輯)
        for subreddit_name in subreddit_list:
            try:
                print(f"Fetching posts from subreddit: {subreddit_name}")
                subreddit_instance = reddit.subreddit(subreddit_name)
                for submission in subreddit_instance.new(limit=limit):
                    post = {
                        'id': submission.id, # 使用 Reddit 的 ID 作為文檔 ID
                        'title': submission.title,
                        'author': str(submission.author),
                        'created_utc': submission.created_utc,
                        'selftext': submission.selftext,
                        'score': submission.score,
                        'num_comments': submission.num_comments,
                        'url': submission.url,
                        'permalink': submission.permalink,
                        'subreddit': subreddit_name
                    }
                    all_fetched_posts.append(post)
            except prawcore.exceptions.NotFound:
                print(f"Subreddit '{subreddit_name}' not found.")
            except prawcore.exceptions.Forbidden:
                print(f"Subreddit '{subreddit_name}' is private or banned.")
            except prawcore.exceptions.PrawcoreException as e:
                print(f"Reddit API error for '{subreddit_name}': {str(e)}")
            except Exception as e:
                print(f"An unexpected error occurred while fetching from '{subreddit_name}': {e}")

        # 關鍵字過濾
        posts_to_send_to_es = []
        if keyword_list:
            for post in all_fetched_posts:
                title_text = post.get('title', '') or ''
                selftext_content = post.get('selftext', '') or ''
                text_to_search = (title_text + ' ' + selftext_content).lower()
                if any(keyword in text_to_search for keyword in keyword_list):
                    posts_to_send_to_es.append(post)
        else:
            posts_to_send_to_es = all_fetched_posts
        
        # 將處理後的貼文批量發送到 Elasticsearch
        actions = []
        for post_data in posts_to_send_to_es:
            actions.append({
                "_index": ES_INDEX_NAME,
                "_id": post_data['id'], # 使用 Reddit post ID 作為 Elasticsearch document ID，避免重複
                "_source": post_data
            })

        successes_count = 0
        errors_list = []
        if actions:
            try:
                print(f"Attempting to bulk index {len(actions)} documents to Elasticsearch index '{ES_INDEX_NAME}'")
                successes_count, errors_list = es_bulk(es_client, actions, raise_on_error=False, request_timeout=30) #增加timeout
            except es_exceptions.ElasticsearchException as e:
                print(f"Elasticsearch bulk operation failed: {e}")
                return jsonify({"error": "Elasticsearch bulk operation failed.", "details": str(e)}), 500
            except Exception as e: # 其他可能的錯誤，例如 helpers.bulk 本身的參數問題
                print(f"An unexpected error occurred during Elasticsearch bulk operation: {e}")
                return jsonify({"error": "Unexpected error during Elasticsearch bulk operation.", "details": str(e)}), 500


        return jsonify({
            "message": "Reddit data fetching and Elasticsearch submission process completed.",
            "total_fetched_from_reddit": len(all_fetched_posts),
            "posts_matching_keywords_sent_to_es": len(posts_to_send_to_es),
            "elasticsearch_bulk_successes": successes_count,
            "elasticsearch_bulk_errors": len(errors_list),
            "elasticsearch_errors_details": errors_list[:10] # 只顯示前10個錯誤詳情，避免回應過大
        })

    except prawcore.exceptions.OAuthException:
        return jsonify({"error": "Reddit authentication failed. Check your credentials."}), 401
    except Exception as e:
        print(f"Unexpected error in /reddit_to_es endpoint: {e}")
        return jsonify({"error": "An internal server error occurred.", "details": str(e)}), 500

if __name__ == '__main__':
    # 確保設定了所有必要的環境變數
    required_vars_reddit = ["REDDIT_CLIENT_ID", "REDDIT_CLIENT_SECRET", "REDDIT_USERNAME", "REDDIT_PASSWORD", "REDDIT_USER_AGENT"]
    required_vars_es = ["ES_HOSTS"] # ES_CLOUD_ID 是另一種選擇
    
    missing_vars = [var for var in required_vars_reddit if not os.environ.get(var)]
    if not (os.environ.get("ES_HOSTS") or os.environ.get("ES_CLOUD_ID")):
        missing_vars.append("ES_HOSTS or ES_CLOUD_ID")
    if os.environ.get("ES_CLOUD_ID") and not (os.environ.get("ES_USERNAME") and os.environ.get("ES_PASSWORD")):
        missing_vars.append("ES_USERNAME and ES_PASSWORD (for ES_CLOUD_ID)")


    if missing_vars:
        print(f"Error: Missing required environment variables: {', '.join(missing_vars)}")
    else:
        app.run(host='0.0.0.0', port=5001, debug=True) # 使用不同 port，避免與上一個 app 衝突