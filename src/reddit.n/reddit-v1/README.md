## Create Functions and Triggers
fission package create --spec --name reddit-data-lister \
  --source ./src/reddit.n/reddit-v1/reddit_daily_trigger.py \
  --source ./src/reddit.n/reddit-v1/reddit_data_formatter.py \
  --source ./src/reddit.n/reddit-v1/reddit_data_harvester.py \
  --source ./src/reddit.n/reddit-v1/__init__.py \
  --source ./src/reddit.n/reddit-v1/reddit_to_elasticsearch.py \
  --source ./src/reddit.n/reddit-v1/util.py \
  --source ./src/reddit.n/reddit-v1/requirements.txt \
  --source ./build.sh \
  --env python39 \
  --buildcmd './build.sh'


chmod +x ./build.sh
dos2unix ./build.sh



## Create Functions and Triggers
### A: HTTP Trigger for Manual Scrape
fission function create --spec --name reddit-data-harvester \
  --pkg reddit-package \
  --env python39 \
  --entrypoint "reddit_scraper.main"

fission route create --spec --name reddit-harvest-trigger \
  --function reddit-data-harvester \
  --method GET \
  --url '/reddit/harvest' \
  --createingress

fission timer create --name reddit-daily-harvest-trigger \
  --function reddit-data-harvester \
  --cron "@daily"


### B: Redis Trigger for Message Queue (e.g., reddit_scraper → reddit_to_elasticsearch)
fission function create --spec --name reddit-data-formatter \
  --pkg reddit-package \
  --env python39 \
  --entrypoint "reddit_data_formatter.main"

fission mqtrigger create --spec --name reddit-formatter-trigger \
  --function reddit-data-formatter \
  --mqtype redis \
  --mqtkind keda \
  --topic reddit_posts_queue \
  --resptopic reddit_posts_formatted_queue \
  --errortopic errors-reddit-formatter \
  --maxretries 3 \
  --metadata address=redis-headless.redis.svc.cluster.local:6379 \
  --metadata listLength=1000 \
  --metadata listName=reddit_posts_queue


### C: Timer Trigger for Daily Scrape
fission function create --spec --name reddit-to-elasticsearch \
  --pkg reddit-package \
  --env python39 \
  --entrypoint "reddit_to_elasticsearch.main"

fission mqtrigger create --spec --name reddit-es-indexer-trigger \
  --function reddit-to-elasticsearch \
  --mqtype redis \
  --mqtkind keda \
  --topic reddit_posts_formatted_queue \
  --errortopic errors-reddit-es-indexer \
  --maxretries 3 \
  --metadata address=redis-headless.redis.svc.cluster.local:6379 \
  --metadata listLength=10000 \
  --metadata listName=reddit_posts_formatted_queue

## Apply Spec and Test

fission spec apply --specdir ./specs --wait

kubectl port-forward service/router -n fission 9090:80

curl -v "http://localhost:9090/reddit/scrape?subreddits=melbourne,sydney&limit=5&keywords=tram,weather"