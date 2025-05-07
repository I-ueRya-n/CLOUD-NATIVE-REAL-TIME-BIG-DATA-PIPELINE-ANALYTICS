
## REDIS QUEUE




## OA debates
The main scraper for debates gets info on all debates that occured on a date
for both the senate and house of reps.
This spits out regular json data, which must be queued to enter the debate parser

There are two ways this is triggered:
1. One runs daily to check for new posts. It checks the day before.

  (This will be relevant on the 5th of May when parliament isn't in recess lol.)

2. The other checks years for the dates with debates, then queues each date to be     scraped. it only checks the last 5 years because... that seems most relevant.
Can change this if we need!


### Create elastic search index for OA debates
DONE, BUT IDK IF IT WORKED

kubectl port-forward service/elasticsearch-master -n elastic 9200:9200
kubectl port-forward service/kibana-kibana -n elastic 5601:5601


// why wouldn't localhost work?
curl -XPUT -k "https://127.0.0.1:9200:9200/oa_debates"\
    --header "Content-Type: application/json"\
    --data "@src/open_australia/oa_debates/index.json"\
    --user "elastic:Mi0zu6yaiz1oThithoh3Di8kohphu9pi"


# FISSION FUNCTIONS

## 1. OA Date Lister - START POINT
Lists dates in a year with debates on them in BOTH the senate and house of reps
Trigger by HTTP request to start the pipeline.
Feeds into the Debate Harvester By Details (into the oa_debate_key redis queue)

### OA Date Lister SETUP

#### create fission function
##### create package

fission package create --spec --name oa-date-lister \
  --source ./src/open_australia/oa_debates/oa_date_lister/__init__.py \
  --source ./src/open_australia/oa_debates/oa_date_lister/oa_date_lister.py \
  --source ./src/open_australia/oa_debates/oa_date_lister/requirements.txt \
  --source ./src/open_australia/oa_debates/oa_date_lister/build.sh \
  --env python39 \
  --buildcmd './build.sh'


##### create function
fission function create --spec --name oa-date-lister \
  --pkg oa-date-lister \
  --env python39 \
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
  
##### create package

fission package create --spec --name oa-person-lister \
  --source ./src/open_australia/oa_debates/oa_person_lister/__init__.py \
  --source ./src/open_australia/oa_debates/oa_person_lister/oa_person_lister.py \
  --source ./src/open_australia/oa_debates/oa_person_lister/requirements.txt \
  --source ./src/open_australia/oa_debates/oa_person_lister/build.sh \
  --env python39 \
  --buildcmd './build.sh'


##### create function
fission function create --spec --name oa-person-lister \
  --pkg oa-person-lister \
  --env python39 \
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
  

##### create package

fission package create --spec --name oa-debate-harvester-by-details \
  --source ./src/open_australia/oa_debates/oa_debate_harvester_by_details/__init__.py \
  --source ./src/open_australia/oa_debates/oa_debate_harvester_by_details/oa_debate_harvester_by_details.py \
  --source ./src/open_australia/oa_debates/oa_debate_harvester_by_details/requirements.txt \
  --source ./src/open_australia/oa_debates/oa_debate_harvester_by_details/build.sh \
  --env python39 \
  --buildcmd './build.sh'


##### create function
fission function create --spec --name oa-debate-harvester-by-details \
  --pkg oa-debate-harvester-by-details \
  --env python39 \
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



## OA debate adder to elasticsearch - FINAL STEP OF DEBATE PIPELINE

##### create package

fission package create --spec --name oa-debate-adder \
  --source ./src/open_australia/oa_debates/debate_adder/__init__.py \
  --source ./src/open_australia/oa_debates/debate_adder/oa_debate_adder.py \
  --source ./src/open_australia/oa_debates/debate_adder/requirements.txt \
  --source ./src/open_australia/oa_debates/debate_adder/build.sh \
  --env python39 \
  --buildcmd './build.sh'


##### create function
fission function create --spec --name oa-debate-adder \
  --pkg oa-debate-adder \
  --env python39 \
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


## OA daily debate scraper for the day before

NOT YET ADDED

##### create package

fission package create --spec --name oa-daily-debate-harvester \
  --source ./src/open_australia/oa_debates/oa_daily_debate_harvester/__init__.py \
  --source ./src/open_australia/oa_debates/oa_daily_debate_harvester/oa_daily_debate_harvester.py \
  --source ./src/open_australia/oa_debates/oa_daily_debate_harvester/requirements.txt \
  --source ./src/open_australia/oa_debates/oa_daily_debate_harvester/build.sh \
  --env python39 \
  --buildcmd './build.sh'


##### create function
fission function create --spec --name oa-daily-debate-harvester \
  --pkg oa-daily-debate-harvester \
  --env python39 \
  --entrypoint "oa_daily_debate_harvester.main"

fission spec apply --specdir ./specs --wait


##### create time trigger to run daily

fission timer create f --function oa-daily-debate-harvester --cron "@daily"


fission spec apply --specdir ./specs --wait
