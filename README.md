# comp90024_team_57

COMP90024 Assignment 2

## Setup

### Fission

Setup fission
```
fission specs init
fission env create --spec --name python --image fission/python-env --builder fission/python-builder
fission env create --spec --name python39 --image fission/python-env-3.9 --builder fission/python-builder-3.9
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
    --source src/bluesky/__init__.py \
    --source src/bluesky/bluesky.py \
    --source src/bluesky/requirements.txt \
    --source src/bluesky/build.sh \
    --env python39 \
    --buildcmd './build.sh'

fission fn create --spec --name bluesky \
    --pkg bluesky \
    --env python39 \
    --configmap shared-data \
    --entrypoint "bluesky.main"

fission route create --spec --name bluesky --url /bluesky --function bluesky --createingress
```

