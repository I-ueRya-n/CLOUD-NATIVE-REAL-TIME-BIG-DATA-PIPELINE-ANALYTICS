# comp90024_team_57

COMP90024 Assignment 2

## Setup
DO NOT RE-RUN THIS CODE!

### Fission

Setup fission
```
fission specs init
fission env create --spec --name python --image fission/python-env --builder fission/python-builder
fission env create --spec --name python39 --image fission/python-env-3.9 --builder fission/python-builder-3.9

fission env create --spec --name go --image ghcr.io/fission/go-env-1.23 --builder ghcr.io/fission/go-builder-1.23

```

To update fission with the current specs, run
```
fission spec apply --wait
```

### Config maps

Create `specs/shared-data.yaml` config map with elastic search login, and run

```
kubectl apply -f specs/shared-data.yaml
```

This contains the following values:
  ES_USERNAME
  ES_PASSWORD 
  BSKY_USERNAME
  BSKY_PASSWORD 

and can be accessed using the following route

### Bluesky

Create elastic search index

```
curl -XPUT -k "https://localhost:9200/bluesky"\
    --header 'Content-Type: application/json'\
    --data "@src/bluesky/index.json"\
    --user 'elastic:<ES_PASSWORD>'
```

Create the fission specs for bluesky

```
fission package create --spec --name bluesky \
    --source src/bluesky/firehose.go \
    --source src/bluesky/go.mod \
    --source src/bluesky/go.sum \
    --env go

fission fn create --spec --name bluesky \
    --pkg bluesky \
    --env go \
    --configmap shared-data \
    --entrypoint Handler

fission route create --spec --name bluesky --url /bluesky --function bluesky
fission timer create --spec --name bluesky --function bluesky --cron "@every 1m"
```

## Open Australia
DO NOT RUN THESE COMMANDS, JUST HERE TO KEEP TRACK OF WHAT I HAVE DONE!

Ok so: 
the OpenAustralia index holds:

comments
  has user info
  can search by keyword, date, or person id

debates
  has the transcript of a debate / politicial discussion
  can search by keyword, date, or person id 


SEE README IN OA_DEBATES
