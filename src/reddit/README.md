## Reddit Crawler

 Fission pipeline Setup

create fission function
create pkg

fission package create --spec --name reddit \
  --env python \
  --source ./src/reddit/__init__.py \
  --source ./src/reddit/reddit_fiss_harvester.py \
  --source ./src/reddit/requirements.txt \
  --source ./src/reddit/build.sh \
  --buildcmd './build.sh'


create function

fission function create --spec --name reddit-post \
  --pkg reddit \
  --env python \
  --entrypoint "reddit_fiss_harvester.main"

fission spec apply --specdir ./specs --wait


fission trigger

fission route create \
  --name reddit-harvester \
  --function reddit-post \
  --method GET \
  --url '/reddit-harvest/{subreddit}/{year}' \
  --createingress