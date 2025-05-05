
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

curl -XPUT -k "https://localhost:9200/oa_debates"\
    --header 'Content-Type: application/json'\
    --data "@src/openaustralia/index.json"\
    --user 'elastic:<ES_PASSWORD>'


## FISSION FUNCTIONS

### OA Person List
    DOES NOT YET PUT IT INTO THE REDIS QUEUE
    GIVEN THAT THERE IS NO REDIS QUEUE 
    BECAUSE THIS TOOK LONGER THAN EXPECTED


Finds all details of politicians in either the senate or house of reps at the start of a year
This really doesn't need to be run much

Call by:
  HTTP get request to 
  curl "/openaustralia/year/{date}/house/{"representatives" | "senate"}"

  e.g. curl "http://localhost:9090/openaustralia/year/2024/house/senate" | jq '.'

Then ENQUEUES the found people to be serached by OA_debate_harvester_by_person


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

fission spec apply --specdir ./specs --wait

##### create function
fission function create --spec --name oa-person-lister \
  --pkg oa-person-lister \
  --env python39 \
  --entrypoint "oa_person_lister.main"

fission spec apply --specdir ./specs --wait


##### create routes

fission route create --spec --name oa-people-year-house --function oa-person-lister \
  --method GET \
  --url '/openaustralia/year/{year:[0-9][0-9][0-9][0-9]}/house/{house:[a-zA-Z0-9]+}'\
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
  e.g. curl "http://localhost:9090/openaustralia/year/2024/house/senate" | jq '.'



### OA debate harvester by person
NOT YET IMPLEMENTED, NOT YET WORKING


### OA debate adder to elasticsearch
NOT YET IMPLEMENTED, NOT YET WORKING






<!-- ### Create the fission function to get the debates on a date -->

<!-- 

### Create the fission function for openaustralia

  fission package create --spec --name OAcomments \
    --source src/openaustralia/OAcomments/__init__.py \
    --source ./functions/OAcomments/OAcomments.py \
    --source ./functions/OAcomments/requirements.txt \
    --source ./functions/OAcomments/build.sh \
    --env python \
    --buildcmd './build.sh'
    
  fission fn create --spec --name avgtemp \
    --pkg OAcomments \
    --env python \
    --entrypoint "OAcomments.main"


fission routes 

  fission route create --spec --name recentOAcomments --function avgtemp \
    --method GET \
    --url '/temperature/days/{date:[0-9][0-9][0-9][0-9]-[0-1][0-9]-[0-3][0-9]}'
  fission route create --spec --name avgtempdaystation --function avgtemp \
    --method GET \
    --url '/temperature/days/{date:[0-9][0-9][0-9][0-9]-[0-1][0-9]-[0-3][0-9]}/stations/{station:[a-zA-Z0-9]+}' -->
