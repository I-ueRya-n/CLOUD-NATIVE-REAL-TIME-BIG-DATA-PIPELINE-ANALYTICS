## Create Functions and Triggers
fission package create --spec --name reddit-harvester \
  --source ./src/reddit.n/reddit_scraper.py \
  --source ./src/reddit.n/reddit_to_elasticsearch.py \
  --source ./src/reddit.n/reddit_daily_trigger.py \
  --source ./src/reddit.n/__init__.py \
  --source ./src/reddit.n/util.py \
  --source ./src/reddit.n/requirements.txt \
  --source ./build.sh \
  --env python \
  --buildcmd './build.sh'


chmod +x ./build.sh
dos2unix ./build.sh



## Create Functions and Triggers
### A: HTTP Trigger for Manual Scrape
fission function create --spec --name reddit-scraper \
  --pkg reddit-harvester \
  --env python \
  --entrypoint "reddit_scraper.main"

fission route create --spec --name reddit-scrape-route \
  --function reddit-scraper \
  --method GET \
  --url '/reddit/scrape'


###B: Redis Trigger for Message Queue (e.g., reddit_scraper → reddit_to_elasticsearch)
fission function create --spec --name reddit-to-es \
  --pkg reddit-harvester \
  --env python \
  --entrypoint "reddit_to_elasticsearch.main"

fission mqtrigger create --name reddit-to-es-trigger \
  --spec \
  --function reddit-to-es \
  --mqtype redis \
  --mqtkind keda \
  --topic reddit_raw_data \
  --errortopic reddit_errors \
  --metadata address=redis-headless.redis.svc.cluster.local:6379 \
  --metadata listLength=1000 \
  --metadata listName=reddit_raw_data


###C: Timer Trigger for Daily Scrape
fission function create --spec --name reddit-daily-trigger \
  --pkg reddit-harvester \
  --env python \
  --entrypoint "reddit_daily_trigger.main"

fission timer create --name reddit-daily-timer \
  --function reddit-daily-trigger \
  --cron "@daily"

### Apply Spec and Test

fission spec apply --specdir ./specs --wait
kubectl port-forward service/router -n fission 9090:80
curl -v "http://localhost:9090/reddit/scrape?subreddits=melbourne,sydney&limit=5&keywords=tram,weather"



