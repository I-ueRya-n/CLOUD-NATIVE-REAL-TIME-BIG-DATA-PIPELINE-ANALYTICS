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

Create the package containing the required packages

```bash
fission package create --spec --name vader \
  --source ./src/analysis/vader/__init__.py \
  --source ./src/analysis/vader/sentiment_function.py \
  --source ./src/analysis/vader/requirements.txt \
  --source ./src/analysis/vader/build.sh \
  --env python \
  --buildcmd './build.sh'
```

Create the function from the file

```
fission function create --spec --name sentiment-function \
  --pkg sentiment-pkg \
  --env python \
  --executortype newdeploy \
  --entrypoint "sentiment_function.main"
```

Create the trigger/route

```
fission route create --spec --name sentiment-function \
  --url /analysis/sentiment/v1 \
  --method POST \
  --createingress \
  --function vader-sentiment-function
```

Test the function with
```
curl -XPOST -k "http://localhost:9090/analysis/sentiment/v1"\
    --header 'Content-Type: application/json'\
    --data '{"text": "The Liberal Party is not a party of aspiration… it’s a party of asps. #auspol #abc730"}'
```


### Analysis (named entities)

Create the python-ner environment
```
fission env create --spec --name python-ner --image pulpss/python-ner
```

Create the function with the new environment
```
fission fn create --spec --name ner-function \
    --env python-ner \
    --executortype newdeploy \
    --code src/analysis/ner/ner_function.py
```

Create the route
```
fission route create --spec --name ner-route --method POST --url analysis/ner/v1 --function ner-function
```

Test the function
```
curl -X POST http://localhost:8888/analysis/ner/v1 -H "Content-Type: application/json" -d '{"text": "SpaCy is great for NLP!"}'
```
Should return something like:
```
{"PERSON": ["SpaCy"], "ORG": ["NLP"]}
```

### Analysis Cache

Sentiment + NER wrapper, checks elastic search for sentiment/ner, calculates and inserts if it doesn't exist.

```
curl -XPUT -k "https://localhost:9200/named-entity"\
    --header 'Content-Type: application/json'\
    --data "@src/analysis/cache/ner-index.json"\
    --user 'elastic:Mi0zu6yaiz1oThithoh3Di8kohphu9pi'
```

```
fission package create --spec --name elastic-cache \
    --source src/analysis/cache/cache.go \
    --source src/analysis/cache/item.go \
    --source src/analysis/cache/sentiment.go \
    --source src/analysis/cache/entity.go \
    --source src/analysis/cache/go.mod \
    --source src/analysis/cache/go.sum \
    --env go

fission fn create --spec --name elastic-sentiment \
    --pkg elastic-cache \
    --env go \
    --configmap shared-data \
    --entrypoint SentimentHandler

fission route create --spec --name elastic-sentiment\
  --url /analysis/sentiment/v2/index/{index}/field/{field} \
  --method POST \
  --function elastic-sentiment

fission fn create --spec --name elastic-ner \
    --pkg elastic-cache \
    --env go \
    --configmap shared-data \
    --entrypoint EntityHandler

fission route create --spec --name elastic-ner \
  --url /analysis/ner/v2/index/{index}/field/{field} \
  --method POST \
  --function elastic-ner
```

Test the cache 
```
fission fn create --spec --name elastic-cache-test \
    --pkg elastic-cache \
    --env go \
    --configmap shared-data \
    --entrypoint ItemHandler

fission route create --spec --name elastic-cache-test \
  --url /cache-test/index/{index}/field/{field} \
  --method POST \
  --function elastic-cache-test

go test
```

### REDIS Queue

Install KEDA

```
export KEDA_VERSION='2.9'
helm repo add kedacore https://kedacore.github.io/charts
helm repo add ot-helm https://ot-container-kit.github.io/helm-charts/
helm repo update
helm upgrade keda kedacore/keda --install --namespace keda --create-namespace --version ${KEDA_VERSION}
```

Install redis (USED THE SAME PASSWORD AS ES)

```
export REDIS_VERSION='0.19.1'
helm repo add ot-helm https://ot-container-kit.github.io/helm-charts/
helm upgrade redis-operator ot-helm/redis-operator \
    --install --namespace redis --create-namespace --version ${REDIS_VERSION}
    
kubectl create secret generic redis-secret --from-literal=password=<ES_PASSWORD> -n redis

helm upgrade redis ot-helm/redis --install --namespace redis   
```

Install redis insight (gui for redis) 

```
kubectl apply -f ./specs/redis-insight.yaml --namespace redis

To view redis insight start port forwarding:

kubectl port-forward service/redis-insight --namespace redis 5540:5540
```

Then go to `http://localhost:5540/`.
Create redis fission package, function and HTTPS trigger 
```
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
```

How to use: In your function, to add to a queue for a topic
```
    response: Optional[requests.Response] = requests.post(
        url='http://router.fission/enqueue oa_debate_keys',
        headers={'Content-Type': 'application/json'},
        json=parsed_person
    )
```

To test the queue: 
    on another terminal window port forward the router:

```
kubectl port-forward service/router -n fission 9090:80
```

```
curl --header "Content-Type: application/json" \
  --request POST \
  --data '{"data1":"xyz","data2":"xyz"}' \
  http://localhost:9090/enqueue/test
```

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

## Frontend 

### Sentiment

```
fission package create --spec --name ui-sentiment \
  --source ./src/ui/sentiment/__init__.py \
  --source ./src/ui/sentiment/sentiment.py \
  --source ./src/ui/sentiment/bluesky.py \
  --source ./src/ui/sentiment/reddit.py \
  --source ./src/ui/sentiment/openaus.py \
  --source ./src/ui/sentiment/requirements.txt \
  --source ./src/ui/sentiment/build.sh \
  --env python \
  --buildcmd './build.sh'

fission function create --spec --name ui-sentiment \
  --pkg ui-sentiment \
  --env python \
  --configmap shared-data \
  --entrypoint "sentiment.main"

fission route create --spec --name ui-sentiment \
  --function ui-sentiment \
  --method GET \
  --createingress \
  --url '/ui/sentiment/start/{date:[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9]}/'\
  --createingress
```

### Named Entities

```
fission package create --spec --name ui-named-entity \
  --source ./src/ui/entities/__init__.py \
  --source ./src/ui/entities/entities.py \
  --source ./src/ui/entities/bluesky.py \
  --source ./src/ui/entities/reddit.py \
  --source ./src/ui/entities/openaus.py \
  --source ./src/ui/entities/requirements.txt \
  --source ./src/ui/entities/build.sh \
  --env python \
  --buildcmd './build.sh'

fission function create --spec --name ui-named-entity \
  --pkg ui-named-entity \
  --env python \
  --configmap shared-data \
  --entrypoint "entities.main"

fission route create --spec --name ui-named-entity \
  --function ui-named-entity \
  --method GET \
  --createingress \
  --url '/ui/named-entities/count/{count:[0-9]+}/label/{label:[a-zA-Z0-9]+}'\
  --createingress
```

## Open Australia

the ElasticSearch "oa_debates" index holds:

debates
  has the transcript of a debate / politicial discussion
  can search by keyword, date, or person id 


SEE README IN OA_DEBATES
