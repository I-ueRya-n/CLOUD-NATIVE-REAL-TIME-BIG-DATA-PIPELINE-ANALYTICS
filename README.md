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

### Prometheus

Install prometheus on the cluster
```
export METRICS_NAMESPACE=monitoring
kubectl create namespace $METRICS_NAMESPACE

helm repo add prometheus-community https://prometheus-community.github.io/helm-charts
helm repo update
helm install prometheus prometheus-community/kube-prometheus-stack -n monitoring
```

Create `config/values.yaml` to enable service monitors in fission.

```
helm upgrade fission fission-charts/fission-all --namespace fission -f config/values.yaml
```

To monitor fission, port-forward the grafana port and go to `localhost:3000`
```
kubectl --namespace monitoring port-forward svc/prometheus-grafana 3000:80
```

### Analysis (vader)

#### Create the package containing the required packages

```bash
fission package create --spec --name vader \
  --source ./src/functions/vader/sentiment_function.py \
  --source ./src/functions/vader/requirements.txt \
  --source ./src/functions/vader/build.sh \
  --env python \
  --buildcmd './build.sh'
```

#### Create the function from the file

```
fission function create --spec --name vader-sentiment-function \
  --pkg vader \
  --env python \
  --entrypoint "sentiment_function.main"
```

#### Create the trigger/route

```
fission route create --spec --name vader-sentiment-function \
  --url /analysis/sentiment \
  --method POST \
  --function vader-sentiment-function
```

### REDIS Queue

#### install KEDA
export KEDA_VERSION='2.9'
helm repo add kedacore https://kedacore.github.io/charts
helm repo add ot-helm https://ot-container-kit.github.io/helm-charts/
helm repo update
helm upgrade keda kedacore/keda --install --namespace keda --create-namespace --version ${KEDA_VERSION}


#### Install redis (USED THE SAME PASSWORD AS ES)

export REDIS_VERSION='0.19.1'
helm repo add ot-helm https://ot-container-kit.github.io/helm-charts/
helm upgrade redis-operator ot-helm/redis-operator \
    --install --namespace redis --create-namespace --version ${REDIS_VERSION}
    
kubectl create secret generic redis-secret --from-literal=password=<ES_PASSWORD> -n redis

helm upgrade redis ot-helm/redis --install --namespace redis   

#### Install redis insight (gui for redis) 

kubectl apply -f ./specs/redis-insight.yaml --namespace redis

To view redis insight start port forwarding:

kubectl port-forward service/redis-insight --namespace redis 5540:5540

Then go to:
http://localhost:5540/


#### Create redis fission package, function and HTTPS trigger 
  fission package create --spec --name enqueue \
    --source ./src/enqueue/__init__.py \
    --source ./src/enqueue/enqueue.py \
    --source ./src/enqueue/requirements.txt \
    --source ./src/enqueue/build.sh \
    --env python \
    --buildcmd './build.sh'



  fission function create --spec --name enqueue \
    --pkg enqueue \
    --env python \
    --entrypoint "enqueue.main"

    fission spec apply --specdir ./specs --wait

  fission httptrigger create --spec --name enqueue --url "/enqueue/{topic}" --method POST --function enqueue

      fission spec apply --specdir ./specs --wait


#### how to use


  In your function, to add to a queue for a topic
        response: Optional[requests.Response] = requests.post(
            url='http://router.fission/enqueue oa_debate_people',
            headers={'Content-Type': 'application/json'},
            json=parsed_person
        )

To test the queue:

on another terminal window port forward the router:
kubectl port-forward service/router -n fission 9090:80

curl --header "Content-Type: application/json" \
  --request POST \
  --data '{"data1":"xyz","data2":"xyz"}' \
  http://localhost:9090/enqueue/test





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
    --source src/bluesky/process_post.go \
    --source src/bluesky/go.mod \
    --source src/bluesky/go.sum \
    --env go

fission fn create --spec --name bluesky-post \
    --pkg bluesky \
    --env go \
    --configmap shared-data \
    --executortype newdeploy \
    --maxscale=30 \
    --entrypoint PostHandler

fission route create --spec --name bluesky-post --url /bluesky/repo-commit --method POST --function bluesky-post 
```

Bluesky firehose docker container
```
cd src/bluesky/
docker build -t jcchil/bluesky-firehose:<version> .
docker push jcchil/bluesky-firehose:<version>
```

Then deploy with kubectl
```
kubectl create -f src/bluesky/bluesky-firehose.yaml
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

