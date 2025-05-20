### CREATE ES INDEX
reddit_posts


## Create Functions and Triggers
fission package create --spec --name reddit-harvester-new-r \
  --source ./src/reddit_new/reddit_harvester.py \
  --source ./src/reddit_new/reddit_to_elasticsearch.py \
  --source ./src/reddit_new/reddit_daily_trigger.py \
  --source ./src/reddit_new/__init__.py \
  --source ./src/reddit_new/util.py \
  --source ./src/reddit_new/requirements.txt \
  --source ./src/reddit_new/build.sh \
  --env python \
  --buildcmd './build.sh'

  




## Create Functions and Triggers
### A: HTTP Trigger for Manual Scrape
fission function create --spec --name reddit-harvester-new \
  --pkg reddit-harvester-new \
  --env python \
  --configmap shared-data \
  --entrypoint "reddit_harvester.main"

fission route create --spec --name reddit-harvest-route-new \
  --function reddit-harvester-new \
  --method POST \
  --url '/reddit-new/scrape/'

Trigger with a body of format
{
  "keywords": [keywords],
  "subreddits": [subreddits],
  "limit": limit, (optional, default 10)
  "scrape_from": date to scrape posts AFTER (YYYY-MM-DD), (optional, default 2000-01-01)
  "scrape_to": scrape_until: date to scrape posts UNTIL, (optional)
  sort: "top" or "new" or "relevance" or "comments", (optional, default "top")

}


    - subreddits: list of subreddits to scrape
    - keywords: list of keywords to filter posts by
    - limit: number of posts to scrape from each subreddit (optional, default is 10)
    - scrape_from: date to scrape posts AFTER (YYYY-MM-DD) (optional, defaults to 2000-01-01)
    - scrape_until: date to scrape posts UNTIL (optional, defaults to today)
    - sort: "top" or "new" or "relevance" or "comments".(optional, defaults to "top")

example to test:
```
curl -X POST "http://localhost:9090/reddit-new/scrape/" \
  -H "Content-Type: application/json" \
  -d '{
    "keywords": ["election", "vote", "politics"],
    "subreddits": ["melbourne", "auspol", "australia"],
    "limit": 5,
    "scrape_from": "2023-01-01",
    "scrape_to": "2023-12-31",
    "sort": "top"
  }'
```

### B: Redis Trigger for Message Queue (e.g., reddit_harvester → reddit_to_elasticsearch)
fission function create --spec --name reddit-to-es-new-r \
  --pkg reddit-harvester-new-r \
  --env python \
  --configmap shared-data \
  --entrypoint "reddit_to_elasticsearch.main"



fission mqtrigger create --name reddit-to-es-new-r \
  --spec\
  --function reddit-to-es-new-r \
  --mqtype redis\
  --mqtkind keda\
  --topic reddit_posts_queue \
  --errortopic reddit_adder_error \
  --maxretries 3 \
  --metadata address=redis-headless.redis.svc.cluster.local:6379\
  --metadata listLength=1000\
  --metadata listName=reddit_posts_queue




### C: Timer Trigger for Daily Scrape

fission function create --spec --name reddit-daily-job \
  --pkg reddit-harvester-new \
  --env python \
  --configmap shared-data \
  --entrypoint "reddit_daily_harvester.main" \

fission timer create --spec --name reddit-daily-trigger \
  --function reddit-daily-job \
  --cron "@daily"

## Apply Spec and Test

fission spec apply --specdir ./specs --wait

kubectl port-forward service/router -n fission 9090:80

<!-- curl -v "http://localhost:9090/reddit/scrape?subreddits=melbourne,sydney&limit=5&keywords=tram,weather" -->

test it !
curl -X POST "http://localhost:9090/reddit-new/scrape/" \
  -H "Content-Type: application/json" \
  -d '{
    "keywords": ["election", "vote", "politics"],
    "subreddits": ["melbourne"],
    "limit": 5,
  }'


curl -X POST "http://localhost:9090/reddit-new/scrape/" \
  -H "Content-Type: application/json" \
  -d '{
    "keywords": ["election", "vote", "politics"],
    "subreddits": ["melbourne"],
    "limit": 5,
    "scrape_from": "2023-01-01",
    "scrape_to": "2023-12-31",
    "sort": "top"

  }'


