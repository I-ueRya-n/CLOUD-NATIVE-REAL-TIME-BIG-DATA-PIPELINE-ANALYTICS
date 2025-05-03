# comp90024_team_57

COMP90024 Assignment 2

## Setup

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

### Bluesky

Create elastic search index

```
curl -XPUT -k "https://localhost:9200/bluesky"\
    --header 'Content-Type: application/json'\
    --data "@src/bluesky/index.json"\
    --user 'elastic:Mi0zu6yaiz1oThithoh3Di8kohphu9pi'
```

Create the fission specs for bluesky
```
fission package create --spec --name bluesky \
    --source src/bluesky/firehose.go \
    --source go.mod \
    --source go.sum \
    --env go

fission fn create --spec --name bluesky \
    --pkg bluesky \
    --env go \
    --configmap shared-data \
    --entrypoint Handler

fission route create --spec --name bluesky --url /bluesky --function bluesky --createingress
```
