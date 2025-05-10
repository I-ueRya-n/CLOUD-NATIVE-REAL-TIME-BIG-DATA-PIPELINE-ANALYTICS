# OA Debate Harvester

Hello!
This is an explanation of how the OA Debates are harvested.
Theres 5 main folders in the openaustralia/oa_debates folder:

ENTRY POINTS:
1. oa_date_lister - HTTP trigger, finds dates with debates during a year
2. oa_person_lister - HTTP trigger, finds people in parliament during a year
3. oa_daily_debate_harvester - runs daily, queues 2 days ago's date for harvesting (may not be any debates)
All three put the found json "KEYS" into queue "oa_debate_keys"
of format 
{
  "house": "senate" or "representatives",
  "date" or "person": date in format YYYY-MM-DD or person id
}

HARVESTER:
4. oa_debate_harvester_by_details - message queue trigger
gets debate keys FROM queue "oa_debate_keys"
puts raw returned debate data into queue "oa_debate_data"

ELASTICSEARCH ADDER:
5. debate_adder - message queue trigger
gets raw debate json from queue "oa_debate_data"
puts it into the elasticsearch index "oa_debates_comments"

DOES NOT ADD DUPLICATE IDS. - this can be changed, it was just annoying to have many versions of the same thing (even though it handled it as the same data)


## SETUP

### NEW ELASTICSEARCH WITH COMMENTS
Index called "oa_debates_comments", follows mapping open_australia/oa_debates/index.json

Forward ports
kubectl port-forward service/elasticsearch-master -n elastic 9200:9200
kubectl port-forward service/kibana-kibana -n elastic 5601:5601


curl -XPUT -k "https://127.0.0.1:9200/oa_debates_comments"\
    --header "Content-Type: application/json"\
    --data "@src/open_australia/oa_debates/index.json"\
    --user "elastic:<pass>"



### BELOW IS OLD AND 
### Create elastic search index for OA debates
First index was called "oa_debates", follows mapping open_australia/oa_debates_old/old_index.json
THIS DIDNT SUPPORT COMMENTS

Forward ports
kubectl port-forward service/elasticsearch-master -n elastic 9200:9200
kubectl port-forward service/kibana-kibana -n elastic 5601:5601


// why wouldn't localhost work?
curl -XPUT -k "https://127.0.0.1:9200/oa_debates"\
    --header "Content-Type: application/json"\
    --data "@src/open_australia/oa_debates/index.json"\
    --user "elastic:<ELASTICSEARCH_PASSWORD>"

### END OLD AND OUTDATED

## FISSION FUNCTION SETUP

common package 

fission package create --spec --name oa-debates \
    --source ./src/open_australia/oa_debates/__init__.py \
    --source ./src/open_australia/oa_debates/requirements.txt \
    --source ./src/open_australia/oa_debates/build.sh \
    --source ./src/open_australia/oa_debates/oa_daily_debate_harvester.py \
    --source ./src/open_australia/oa_debates/oa_debate_adder.py \
    --source ./src/open_australia/oa_debates/oa_debate_harvester_by_details.py \
    --source ./src/open_australia/oa_debates/oa_person_lister.py \
    --source ./src/open_australia/oa_debates/util.py \
    --env python39 \
    --buildcmd './build.sh'

## 1. OA Date Lister - START POINT
Lists dates in a year with debates on them in BOTH the senate and house of reps
Trigger by HTTP request to start the pipeline.
Feeds into the Debate Harvester By Details (into the oa_debate_key redis queue)

### OA Date Lister SETUP

#### create fission function

##### create function
fission function create --spec --name oa-date-lister \
  --pkg oa-debates \
  --env python39 \
  --configmap shared-data \
  --entrypoint "oa_date_lister.main"

fission spec apply --specdir ./specs --wait

##### create routes

fission route create --spec --name oa-dates-with-debates --function oa-date-lister \
  --method GET \
  --url '/openaustralia/year/{year:[0-9][0-9][0-9][0-9]}'\
  --createingress

fission spec apply --specdir ./specs --wait

## forward port 
kubectl port-forward service/router -n fission 9090:80

## to see logs
fission function log -f --name oa-date-lister

#### test

on another terminal window port forward the router:
kubectl port-forward service/router -n fission 9090:80

then test
  e.g. curl "http://localhost:9090/openaustralia/year/2024" | jq '.'



## 2. OA Person List - START POINT
Finds all details of politicians in either the senate or house of reps at the start of a year
This really doesn't need to be run much
OUTDATED, USE THE YEAR ONE INSTEAD TO AVOID DUPLICATES

Call by:
  HTTP get request to 
  "/openaustralia/list-people/year/{date}/house/{"representatives" | "senate"}"

  e.g. curl "http://localhost:9090/openaustralia/list-people/year/2024/house/senate" | jq '.'

Then ENQUEUES the found people to be serached by OA_debate_harvester_by_details


### SETUP

#### create fission function
  
##### create function
fission function create --spec --name oa-person-lister \
  --pkg oa-debates \
  --env python39 \
  --configmap shared-data \
  --entrypoint "oa_person_lister.main"

fission spec apply --specdir ./specs --wait


##### create routes

fission route create --spec --name oa-people-year-house --function oa-person-lister \
  --method GET \
  --url '/openaustralia/list-people/year/{year:[0-9][0-9][0-9][0-9]}/house/{house:[a-zA-Z0-9]+}'\
  --createingress

fission spec apply --specdir ./specs --wait


## forward port 
kubectl port-forward service/router -n fission 9090:80

## to see logs
fission function log -f --name oa-person-lister

#### test

on another terminal window port forward the router:
kubectl port-forward service/router -n fission 9090:80

then test
  e.g. curl "http://localhost:9090/openaustralia/list-people/year/2024/house/senate" | jq '.'



## 3. OA debate harvester by details - MIDDLE PIPELINE STEP
reads from oa_debate_keys redis queue
writes to oa_debate_data redis queue
queries api for debates by person or by date (up to 1000)

#### create fission function
  
##### create function
fission function create --spec --name oa-debate-harvester-by-details \
  --pkg oa-debates \
  --env python39 \
  --configmap shared-data \
  --entrypoint "oa_debate_harvester_by_details.main"

fission spec apply --specdir ./specs --wait


##### create redis trigger for queue

  fission mqtrigger create --name oa-debate-harvester-by-details \
    --spec\
    --function oa-debate-harvester-by-details \
    --mqtype redis\
    --mqtkind keda\
    --topic oa_debate_keys \
    --resptopic oa_debate_data \
    --errortopic errors-debate-harvester \
    --maxretries 3 \
    --metadata address=redis-headless.redis.svc.cluster.local:6379\
    --metadata listLength=1000\
    --metadata listName=oa_debate_keys

fission spec apply --specdir ./specs --wait

## 4. OA debate adder to elasticsearch - FINAL STEP OF DEBATE PIPELINE
adds to the NEW index "oa_debates_comments"

##### create function
fission function create --spec --name oa-debate-adder \
  --pkg oa-debates \
  --env python39 \
  --configmap shared-data \
  --entrypoint "oa_debate_adder.main"

fission spec apply --specdir ./specs --wait

##### create redis trigger for queue
  fission mqtrigger create --name oa-debate-adder \
    --spec\
    --function oa-debate-adder \
    --mqtype redis\
    --mqtkind keda\
    --topic oa_debate_data \
    --errortopic errors-debate-adder \
    --maxretries 3 \
    --metadata address=redis-headless.redis.svc.cluster.local:6379\
    --metadata listLength=10000\
    --metadata listName=oa_debate_data

fission spec apply --specdir ./specs --wait

## 5. OA daily debate scraper for TWO DAYS before the current date - ANOTHER PIPELINE START POINT
Two days before was chosen as the debates are usually updated by 5pm the day after

##### create function
fission function create --spec --name oa-daily-debate-harvester \
  --pkg oa-debates \
  --env python39 \
  --configmap shared-data \
  --entrypoint "oa_daily_debate_harvester.main"

fission spec apply --specdir ./specs --wait

##### create time trigger to run daily

fission timer create f --function oa-daily-debate-harvester --cron "@daily"

fission spec apply --specdir ./specs --wait
