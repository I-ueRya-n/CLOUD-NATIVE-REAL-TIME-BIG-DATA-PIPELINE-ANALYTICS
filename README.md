# comp90024_team_57

COMP90024 Assignment 2

## Table of Contents

- [Repo Contents](#repo-contents)
- [Client](#client)
- [Docs (Report)](#docs-report)
- [Fission Setup](#fission-setup)
  - [Config maps](#config-maps)
  - [Prometheus](#prometheus)
- [Open Australia Setup](#open-australia-setup)
  - [REDIS Queue](#redis-queue)
  - [ElasticSearch](#elasticsearch)
  - [Fission](#fission)
  - [Date Lister](#date-lister)
  - [Person Lister](#person-lister)
  - [Debate Harvester by Details](#debate-harvester-by-details)
  - [Debate Adder](#debate-adder)
  - [Daily Debate Harvester](#daily-debate-harvester)
- [Bluesky Setup](#bluesky-setup)
- [Analysis Setup](#analysis-setup)
  - [Vader](#vader)
  - [Named Entities](#named-entities)
  - [Analysis Cache](#analysis-cache)
- [User Interface](#user-interface)
  - [Sentiment](#sentiment)
  - [Named Entities](#named-entities-1)


## Repo Contents

```
comp90024_team_57
├───config                  // grafana config files
├───docs                    // report files
├───examples                // frontend jupyter notebooks
├───specs                   // fission yamls
├───src
│   ├───analysis
│   │   ├───cache           // analysis cache
│   │   ├───ner             // named entity recognition
│   │   └───vader           // vader sentiment analysis
│   ├───bluesky             // bluesky client
│   ├───enqueue             // redis queue manager
│   ├───open_australia      // open australia clients
│   │   ├───comments        // comments harvester
│   │   └───oa_debates      // debate harvester
│   └───ui                  // ui fission functions
```

## Client 

Setup a jupyter notebook with matplotlib, numpy, pandas and wordcloud installed in the python environment.
Create a port forward to fission.
```bash
kubectl port-forward service/router -n fission 9090:80
```

Open the notebook `examples/sample.ipynb` and run all cells.


## Tests

### Python

First of all, you need to install the requirements for the tests (you might need to create a virtual environment):

```bash
# Optional
python3 -m venv venv
source venv/bin/activate
```

Then install the requirements:
```bash
pip install -r tests/requirements.txt
```

Then make sure you have the kubernetes cluster running and the fission router port-forwarded to `localhost:9090`.

To run the tests, you can use `pytest`:
```bash
pytest tests/
```


## Docs (Report)

The report is located in the `docs` folder and it contains the latex report that can be compiled with `latexmk` using the following command:
```bash
latexmk -pdf -outdir=docs/out/ docs/report.tex
```

## Fission Setup

Setup fission
```bash
fission specs init
fission env create --spec --name python --image fission/python-env --builder fission/python-builder
fission env create --spec --name go --image ghcr.io/fission/go-env-1.23 --builder ghcr.io/fission/go-builder-1.23
```

To update fission with the current specs, run
```bash
fission spec apply --wait
```

### Config maps

Create `specs/shared-data.yaml` config map with elastic search login, and run

```bash
kubectl apply -f specs/shared-data.yaml
```

### Prometheus

Install prometheus on the cluster
```bash
export METRICS_NAMESPACE=monitoring
kubectl create namespace $METRICS_NAMESPACE

helm repo add prometheus-community https://prometheus-community.github.io/helm-charts
helm repo update
helm install prometheus prometheus-community/kube-prometheus-stack -n monitoring
```

Create `config/values.yaml` to enable service monitors in fission.

```bash
helm upgrade fission fission-charts/fission-all --namespace fission -f config/values.yaml
```

To monitor fission, port-forward the grafana port and go to `localhost:3000`
```bash
kubectl --namespace monitoring port-forward svc/prometheus-grafana 3000:80
```

## Open Australia Setup

### REDIS Queue

Install KEDA

```bash
export KEDA_VERSION='2.9'
helm repo add kedacore https://kedacore.github.io/charts
helm repo add ot-helm https://ot-container-kit.github.io/helm-charts/
helm repo update
helm upgrade keda kedacore/keda --install --namespace keda --create-namespace --version ${KEDA_VERSION}
```

Install redis (USED THE SAME PASSWORD AS ES)

```bash
export REDIS_VERSION='0.19.1'
helm repo add ot-helm https://ot-container-kit.github.io/helm-charts/
helm upgrade redis-operator ot-helm/redis-operator \
    --install --namespace redis --create-namespace --version ${REDIS_VERSION}
    
kubectl create secret generic redis-secret --from-literal=password=<ES_PASSWORD> -n redis

helm upgrade redis ot-helm/redis --install --namespace redis   
```

Install redis insight (gui for redis) 

```bash
kubectl apply -f ./specs/redis-insight.yaml --namespace redis

To view redis insight start port forwarding:

kubectl port-forward service/redis-insight --namespace redis 5540:5540
```

Then go to `http://localhost:5540/`.
Create redis fission package, function and HTTPS trigger 
```bash
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
```python
    response: Optional[requests.Response] = requests.post(
        url='http://router.fission/enqueue oa_debate_keys',
        headers={'Content-Type': 'application/json'},
        json=parsed_person
    )
```

To test the queue: 
    on another terminal window port forward the router:

```bash
kubectl port-forward service/router -n fission 9090:80
```

```bash
curl --header "Content-Type: application/json" \
  --request POST \
  --data '{"data1":"xyz","data2":"xyz"}' \
  http://localhost:9090/enqueue/test
```

### ElasticSearch

Two indices called `oa-debates` and `oa-comments`, follows mapping `open_australia/oa_debates/oa-comments.json` and `oa-debates.json`

```bash
curl -XPUT -k "https://127.0.0.1:9200/oa-debates"\
    --header "Content-Type: application/json"\
    --data "@src/open_australia/oa_debates/oa-debates.json"\
    --user "elastic:<es_password>"

curl -XPUT -k "https://127.0.0.1:9200/oa-comments"\
    --header "Content-Type: application/json"\
    --data "@src/open_australia/oa_debates/oa-comments.json"\
    --user "elastic:<es_password>"
```

### Fission

Create the common fission package for all debate functions,
```bash
fission package create --spec --name oa-debates \
    --source ./src/open_australia/oa_debates/__init__.py \
    --source ./src/open_australia/oa_debates/requirements.txt \
    --source ./src/open_australia/oa_debates/build.sh \
    --source ./src/open_australia/oa_debates/oa_daily_debate_harvester.py \
    --source ./src/open_australia/oa_debates/oa_debate_adder.py \
    --source ./src/open_australia/oa_debates/oa_debate_harvester_by_details.py \
    --source ./src/open_australia/oa_debates/oa_person_lister.py \
    --source ./src/open_australia/oa_debates/util.py \
    --env python \
    --buildcmd './build.sh'
```

### Date Lister 

Lists dates in a year with debates on them in BOTH the senate and house of reps.
Trigger by HTTP request to start the pipeline.
Feeds into the Debate Harvester By Details (into the oa_debate_key redis queue).

Create fission package and route.
```bash
fission function create --spec --name oa-date-lister \
  --pkg oa-debates \
  --env python \
  --configmap shared-data \
  --entrypoint "oa_date_lister.main"

fission route create --spec --name oa-dates-with-debates --function oa-date-lister \
  --method GET \
  --url '/openaustralia/year/{year:[0-9][0-9][0-9][0-9]}'\
  --createingress
```

### Person Lister

Finds all details of politicians in either the senate or house of reps at the start of a year

Create fission package and route.
```bash
fission function create --spec --name oa-person-lister \
  --pkg oa-debates \
  --env python \
  --configmap shared-data \
  --entrypoint "oa_person_lister.main"

fission route create --spec --name oa-people-year-house --function oa-person-lister \
  --method GET \
  --url '/openaustralia/list-people/year/{year:[0-9][0-9][0-9][0-9]}/house/{house:[a-zA-Z0-9]+}'\
  --createingress
```

### Debate Harvester by Details

Reads from oa_debate_keys redis queue.
Writes to oa_debate_data redis queue.
Queries api for debates by person or by date (up to 1000).

Create fission function and redis trigger.

```bash
fission function create --spec --name oa-debate-harvester-by-details \
    --pkg oa-debates \
    --env python \
    --configmap shared-data \
    --entrypoint "oa_debate_harvester_by_details.main"

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
```

### Debate Adder 

Adds data from redis queue to elasticsearch indices `oa-debates` AND `oa-comments`

Create fission function and redis trigger.
```bash
fission function create --spec --name oa-debate-adder \
    --pkg oa-debates \
    --env python \
    --configmap shared-data \
    --entrypoint "oa_debate_adder.main"

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
```

### Daily Debate Harvester

Pulls debate data from 2 days prior to the current date.

Create fission function and timer trigger.
```bash
fission function create --spec --name oa-daily-debate-harvester \
  --pkg oa-debates \
  --env python \
  --configmap shared-data \
  --entrypoint "oa_daily_debate_harvester.main"

fission timer create f --function oa-daily-debate-harvester --cron "@daily"
```

## Bluesky Setup

Create elastic search index

```bash
curl -XPUT -k "https://localhost:9200/bluesky"\
    --header 'Content-Type: application/json'\
    --data "@src/bluesky/index.json"\
    --user 'elastic:<ES_PASSWORD>'
```

Create the fission specs for bluesky

```bash
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

Build the Bluesky firehose docker container
```bash
cd src/bluesky/
docker build -t jcchil/bluesky-firehose:<version> .
docker push jcchil/bluesky-firehose:<version>
```

Then deploy with kubectl
```bash
kubectl create -f src/bluesky/bluesky-firehose.yaml
```

## Analysis Setup

### Vader

Create the package containing the required packages, the function for vader, and the http route.

```bash
fission package create --spec --name sentiment-pkg \
  --source ./src/analysis/vader/__init__.py \
  --source ./src/analysis/vader/sentiment_function.py \
  --source ./src/analysis/vader/requirements.txt \
  --source ./src/analysis/vader/build.sh \
  --env python \
  --buildcmd './build.sh'

fission function create --spec --name sentiment-function \
  --pkg sentiment-pkg \
  --env python \
  --maxscale=30 \
  --executortype newdeploy \
  --entrypoint "sentiment_function.main"

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

### Named Entities

Create the python-ner environment, function and the http route

```bash
fission env create --spec --name python-ner --image pulpss/python-ner

fission fn create --spec --name ner-function \
    --env python-ner \
    --maxscale=30 \
    --executortype newdeploy \
    --code src/analysis/ner/ner_function.py

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
Create Elastic Search indices,

```bash
curl -XPUT -k "https://localhost:9200/sentiment"\
    --header 'Content-Type: application/json'\
    --data "@src/analysis/cache/sentiment-index.json"\
    --user 'elastic:<es_password>'

curl -XPUT -k "https://localhost:9200/named-entity"\
    --header 'Content-Type: application/json'\
    --data "@src/analysis/cache/ner-index.json"\
    --user 'elastic:<es_password>'
```

Create fission package for caching,
```bash
fission package create --spec --name elastic-cache \
    --source src/analysis/cache/cache.go \
    --source src/analysis/cache/item.go \
    --source src/analysis/cache/sentiment.go \
    --source src/analysis/cache/entity.go \
    --source src/analysis/cache/go.mod \
    --source src/analysis/cache/go.sum \
    --env go
```

Create fission function and http route for sentiment cache.
```bash
fission fn create --spec --name elastic-sentiment \
    --pkg elastic-cache \
    --env go \
    --executortype newdeploy \
    --minscale 1 \
    --configmap shared-data \
    --entrypoint SentimentHandler

fission route create --spec --name elastic-sentiment\
  --url /analysis/sentiment/v2/index/{index}/field/{field} \
  --method POST \
  --function elastic-sentiment
```

Create fission function and http route for ner cache.
```bash
fission fn create --spec --name elastic-ner \
    --pkg elastic-cache \
    --env go \
    --executortype newdeploy \
    --minscale 1 \
    --configmap shared-data \
    --entrypoint EntityHandler

fission route create --spec --name elastic-ner \
  --url /analysis/ner/v2/index/{index}/field/{field} \
  --method POST \
  --function elastic-ner
```

## User Interface

### Sentiment

Create fission package, function and http route for the `ui-sentiment` function which aggregates sentiment data per day over a period of time.
```bash
fission package create --spec --name ui-sentiment \
  --source ./src/ui/iterator.py \
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
  --rpp 10 \
  --configmap shared-data \
  --entrypoint "sentiment.main"

fission route create --spec --name ui-sentiment \
  --function ui-sentiment \
  --method GET \
  --createingress \
  --url '/ui/sentiment/keyword/{keyword}/start/{start:[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9]}/end/{end:[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9]}' \
  --createingress
```

### Named Entities

Create fission package, function and http route for the `ui-named-entity` function which collects the count of named entities.
```bash
fission package create --spec --name ui-named-entity \
  --source ./src/ui/iterator.py \
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
  --rpp 10 \
  --configmap shared-data \
  --entrypoint "entities.main"

fission route create --spec --name ui-named-entity \
  --function ui-named-entity \
  --method GET \
  --createingress \
  --url '/ui/named-entities/label/{label:[a-zA-Z0-9]+}'\
  --createingress
```

### Sentiment averager by keywords

Create fission package, function and http route for the `ui-keywords-sentiment-averager` function which computes the average sentiment for posts containing a keyword.
```bash
fission package create --spec --name ui-keywords-sentiment-averager \
  --source ./src/ui/iterator.py \
  --source ./src/ui/sentiment_by_keyword/__init__.py \
  --source ./src/ui/sentiment_by_keyword/sentiment-averager.py \
  --source ./src/ui/sentiment_by_keyword/bluesky.py \
  --source ./src/ui/sentiment_by_keyword/reddit.py \
  --source ./src/ui/sentiment_by_keyword/openaus.py \
  --source ./src/ui/sentiment_by_keyword/requirements.txt \
  --source ./src/ui/sentiment_by_keyword/build.sh \
  --env python \
  --buildcmd './build.sh'

fission function create --spec --name ui-keywords-sentiment-averager \
  --pkg ui-keywords-sentiment-averager \
  --env python \
  --rpp 10 \
  --configmap shared-data \
  --entrypoint "sentiment-averager.main"

fission route create --spec --name ui-keywords-sentiment-averager \
  --function ui-keywords-sentiment-averager \
  --method POST \
  --createingress \
  --url '/ui/sentiment-averager/type/{type:[a-zA-Z0-9]+}'\
  --createingress
```

### Counts

Create fission package, function and http route for the `ui-counts` function which calculates the number of posts containing a keyword.
```bash
fission package create --spec --name ui-counts \
  --source ./src/ui/iterator.py \
  --source ./src/ui/counts/__init__.py \
  --source ./src/ui/counts/counts.py \
  --source ./src/ui/counts/bluesky.py \
  --source ./src/ui/counts/reddit.py \
  --source ./src/ui/counts/openaus.py \
  --source ./src/ui/counts/requirements.txt \
  --source ./src/ui/counts/build.sh \
  --env python \
  --buildcmd './build.sh'

fission function create --spec --name ui-counts \
  --pkg ui-counts \
  --env python \
  --rpp 10 \
  --configmap shared-data \
  --entrypoint "counts.main"

fission route create --spec --name ui-counts \
  --function ui-counts \
  --method GET \
  --createingress \
  --url '/ui/counts/start/{date:[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9]}/keyword/{keyword}'\
  --createingress
```
