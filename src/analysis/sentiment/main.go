package main

import (
	"bytes"
	"context"
	"encoding/json"
	"fmt"
	"io"
	"log"
	"maps"
	"net/http"
	"os"
	"slices"

	es "github.com/elastic/go-elasticsearch/v8"
	"github.com/elastic/go-elasticsearch/v8/typedapi/core/search"
	"github.com/elastic/go-elasticsearch/v8/typedapi/types"
)

func config(key string) string {
	path := "/configs/default/shared-data/" + key

	buf, err := os.ReadFile(path)
	if err != nil {
		log.Println("error reading config map: ", err)
		return ""
	}

	return string(buf[:])
}

type Sentiment struct {
	Id       string  `json:"id"`
	Index    string  `json:"index"`
	Negative float64 `json:"neg"`
	Neutral  float64 `json:"neu"`
	Positive float64 `json:"pos"`
	Compound float64 `json:"compound"`
}

func returnError(w http.ResponseWriter, msg string) {
	w.WriteHeader(http.StatusInternalServerError)
	w.Write([]byte(msg))
	log.Fatalf(msg)
}

/*
Handler: takes a list of id's from an elastic search index,
and calculates the sentiment of each one, using the 'sentiment'
es index as a cache for previously calculated sentiments.
*/
func Handler(w http.ResponseWriter, r *http.Request) {
	index := r.Header.Get("X-Fission-Params-Index")
	field := r.Header.Get("X-Fission-Params-Field")

	buf, err := io.ReadAll(r.Body)
	if err != nil {
		returnError(w, fmt.Sprintln("reading request body:", err))
	}

	query := make([]string, 0, 1000)
	err = json.Unmarshal(buf, &query)
	if err != nil {
		returnError(w, fmt.Sprintln("parsing query:", err))
	}

	log.Printf("sentiment: received %d id's", len(query))

	client, err := es.NewTypedClient(es.Config{
		Addresses:              []string{config("ES_HOSTNAME")},
		Username:               config("ES_USERNAME"),
		Password:               config("ES_PASSWORD"),
		CertificateFingerprint: config("ES_FINGERPRINT"),
	})
	if err != nil {
		returnError(w, fmt.Sprintln("es login:", err))
	}

	sentiment, err := calculateSentiment(client, index, field, query)
	if err != nil {
		returnError(w, fmt.Sprintln("fetching sentiment:", err))
	}

	log.Printf("sentiment: %d posts", len(sentiment))

	buf, err = json.Marshal(sentiment)
	if err != nil {
		returnError(w, err.Error())
	}

	w.Write(buf)
}

func matchField(field, value string) types.Query {
	return types.Query{
		Match: map[string]types.MatchQuery{
			field: {
				Query: value,
			},
		},
	}
}

/*
Convert the array of id's in query to sentiments
*/
func calculateSentiment(client *es.TypedClient, index, field string, query []string) (sentiment []Sentiment, err error) {
	items := make([]types.Query, len(query))

	for i, id := range query {
		items[i] = matchField("id", id)
	}

	size := len(query)
	req := search.Request{
		Size: &size,
		Query: &types.Query{
			Bool: &types.BoolQuery{
				Must: []types.Query{
					matchField("index", index),
				},
				Should: items,
			},
		},
	}

	// search cache for sentiments
	res, err := client.Search().Index("sentiment").Request(&req).Do(context.Background())
	if err != nil {
		return
	}

	results := res.Hits.Hits
	sentimentCalculated := make(map[string]Sentiment, len(query))

	// add cached sentiments to result
	for _, item := range results {
		source := item.Source_
		var sent Sentiment

		err = json.Unmarshal(source, &sent)
		if err != nil {
			log.Println("json item:", err)
			continue
		}

		sentimentCalculated[sent.Id] = sent
	}

	log.Printf("sentiment: %d pre-calculated", len(sentiment))

	// calculate sentiment for posts not cached
	for _, q := range query {
		if _, ok := sentimentCalculated[q]; ok {
			continue
		}

		var sent Sentiment
		sent, err = calculatePostSentiment(client, index, field, q)
		if err != nil {
			err = fmt.Errorf("calculating sentiment: %s", err)
			return
		}

		sentimentCalculated[q] = sent
	}

	sentiment = slices.Collect(maps.Values(sentimentCalculated))
	return
}

func calculatePostSentiment(client *es.TypedClient, index, field, id string) (sentiment Sentiment, err error) {
	queryType := matchField("_id", id)
	req := search.Request{
		Query: &queryType,
	}

	res, err := client.Search().Index(index).Request(&req).Do(context.Background())
	if err != nil {
		log.Println("index", index, "id", id)
		return
	}

	if res.Hits.Hits == nil || len(res.Hits.Hits) == 0 {
		err = fmt.Errorf("no entries in index %s with id %s", index, id)
		return
	}

	entry_json := res.Hits.Hits[0].Source_
	var source map[string]string

	buf, _ := entry_json.MarshalJSON()
	err = json.Unmarshal(buf, &source)
	if err != nil {
		return
	}

	var text_json struct {
		Text string `json:"text"`
	}

	text_json.Text = source[field]
	buf, err = json.Marshal(text_json)
	if err != nil {
		return
	}

	addr := config("FISSION_HOSTNAME") + "/analysis/sentiment/v1"
	sentRes, err := http.Post(addr, "application/json", bytes.NewReader(buf))
	if err != nil {
		return
	}

	buf, err = io.ReadAll(sentRes.Body)
	if err != nil {
		return
	}

	if sentRes.StatusCode != http.StatusOK {
		err = fmt.Errorf("analysis/sentiment/v1: %s", buf)
		return
	}

	err = json.Unmarshal(buf, &sentiment)
	if err != nil {
		err = fmt.Errorf("json from vader: %s", buf)
		return
	}

	sentiment.Id = id
	sentiment.Index = index
	esID := index + "-" + id
	_, err = client.Index("sentiment").Id(esID).Request(sentiment).Do(context.Background())
	return
}
