### CREATE ES INDEX
reddit_posts


## Create Functions and Triggers
fission package create --spec --name reddit-harvester-new \
  --source ./src/reddit_new/reddit_harvester.py \
  --source ./src/reddit_new/reddit_to_elasticsearch.py \
  --source ./src/reddit_new/__init__.py \
  --source ./src/reddit_new/util.py \
  --source ./src/reddit_new/requirements.txt \
  --source ./src/reddit_new/build.sh \
  --source ./src/reddit_new/reddit_daily_trigger.py \
  --source ./src/reddit_new/reddit_query_trigger.py \
  --env python \
  --buildcmd './build.sh'

fission timer create --name reddit-daily-trigger-r \
--function reddit-daily-job \
--cron "@daily"





## Create Functions and Triggers
### A: HTTP Trigger for Manual Scrape - ENTRYPOINT

Puts data in reddit-keys
adds the all time top + new for as list of keywords and subreddits to the queue
Trigger with a bodyof format
{
  "keywords": [keywords],
  "subreddits": [subreddits],
  "limit": limit, (optional, default 1000)
}

fission function create --spec --name reddit-query-trigger-new \
  --pkg reddit-harvester-new \
  --env python \
  --configmap shared-data \
  --entrypoint "reddit_query_trigger.main"


fission route create --spec --name reddit-query-trigger-new \
  --function reddit-query-trigger-new \
  --method POST \
  --url '/reddit-new/scrape/'


example to test:
```
curl -X POST "http://localhost:9090/reddit-new/scrape/" \
  -H "Content-Type: application/json" \
  -d '{
    "keywords": ["election", "vote", "politics"],
    "subreddits": ["melbourne", "auspol", "australia"],
    "limit": 5
  }'
```

### B: Time Trigger for daily Scrape - ENTRYPOINT
Puts data in reddit-keys
runs daily, gets the new posts in the last 24 hours for a list of predefined
subreddits + keywords

fission function create --spec --name reddit-daily-trigger-new \
  --pkg reddit-harvester-new \
  --env python \
  --configmap shared-data \
  --entrypoint "reddit_daily_trigger.main"


fission timer create f --function reddit-daily-trigger-new --cron "@daily"


### C: Redis Trigger - to scrape data


Gets data from reddit-keys
Puts data in reddit-posts-queue

Trigger with a body (in reddit-keys) of format
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



fission function create --spec --name reddit-harvester-new \
  --pkg reddit-harvester-new \
  --env python \
  --configmap shared-data \
  --entrypoint "reddit_harvester.main"

fission mqtrigger create --name reddit-harvester-new \
  --spec\
  --function reddit-harvester-new \
  --mqtype redis\
  --mqtkind keda\
  --topic reddit-keys \
  --errortopic reddit_harvester_error \
  --maxretries 3 \
  --metadata address=redis-headless.redis.svc.cluster.local:6379\
  --metadata listLength=1000\
  --metadata listName=reddit-keys




### B: Redis Trigger - to add data to ES
fission function create --spec --name reddit-to-es-new \
  --pkg reddit-harvester-new \
  --env python \
  --configmap shared-data \
  --entrypoint "reddit_to_elasticsearch.main"



fission mqtrigger create --name reddit-to-es-new \
  --spec\
  --function reddit-to-es-new \
  --mqtype redis\
  --mqtkind keda\
  --topic reddit-posts-queue \
  --errortopic reddit_adder_error \
  --maxretries 3 \
  --metadata address=redis-headless.redis.svc.cluster.local:6379\
  --metadata listLength=1000\
  --metadata listName=reddit-posts-queue



### C: adder


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
    "limit": 5
  }'


curl -X POST "http://localhost:9090/reddit-new/scrape/" \
  -H "Content-Type: application/json" \
  -d '{
    "keywords": ["election", "vote", "politics"],
    "subreddits": ["melbourne"],
    "limit": 5
  }'

