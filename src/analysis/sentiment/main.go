package main

import (
	"bytes"
	"context"
	"encoding/json"
	"fmt"
	"io"
	"log"
	"net/http"
	"os"

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

type SentimentQuery struct {
	Id    string `json:"id"`
	Index string `json:"index"`
	Field string `json:"field"`
}

type Sentiment struct {
	SentimentQuery
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

func Handler(w http.ResponseWriter, r *http.Request) {
	buf, err := io.ReadAll(r.Body)
	if err != nil {
		returnError(w, fmt.Sprintln("reading request body:", err))
	}

	query := make([]SentimentQuery, 0, 100)
	err = json.Unmarshal(buf, &query)
	if err != nil {
		returnError(w, fmt.Sprintln("parsing query:", err))
	}

	client, err := es.NewTypedClient(es.Config{
		Addresses:              []string{ES_HOSTNAME},
		Username:               config("ES_USERNAME"),
		Password:               config("ES_PASSWORD"),
		CertificateFingerprint: config("ES_FINGERPRINT"),
	})
	if err != nil {
		returnError(w, fmt.Sprintln("es login:", err))
	}

	sent := make([]Sentiment, 0, len(query))
	for _, q := range query {
		res, err := processQuery(client, q)
		if err != nil {
			log.Println("processing query:", err)
			continue
		}

		sent = append(sent, res)
	}

	buf, err = json.Marshal(sent)
	if err != nil {
		returnError(w, err.Error())
	}

	w.Write(buf)
}

func processQuery(client *es.TypedClient, query SentimentQuery) (sentiment Sentiment, err error) {
	req := search.Request{
		Query: &types.Query{
			Bool: &types.BoolQuery{
				Must: []types.Query{
					matchField("id", query.Id),
					matchField("index", query.Index),
				},
			},
		},
	}

	res, err := client.Search().Index("sentiment").Request(&req).Do(context.Background())
	if err != nil {
		return
	}

	if len(res.Hits.Hits) == 0 {
		log.Printf("%s-%s does not exist in sentiment, calculating", query.Index, query.Id)
		sentiment, err = calculateSentiment(client, query)
		if err != nil {
			return
		}
	} else {
		log.Printf("%s-%s exists in sentiment", query.Index, query.Id)
		entry_json := res.Hits.Hits[0].Source_

		err = json.Unmarshal(entry_json, &sentiment)
		if err != nil {
			return
		}
	}

	return
}

func matchField(field, value string) types.Query {
	query := types.Query{
		Match: make(map[string]types.MatchQuery, 5),
	}

	query.Match[field] = types.MatchQuery{Query: value}
	return query
}

func calculateSentiment(client *es.TypedClient, query SentimentQuery) (sentiment Sentiment, err error) {
	sentiment.SentimentQuery = query

	queryType := matchField("_id", query.Id)
	req := search.Request{
		Query: &queryType,
	}

	res, err := client.Search().Index(query.Index).Request(&req).Do(context.Background())
	if err != nil {
		return
	}

	if res.Hits.Hits == nil || len(res.Hits.Hits) == 0 {
		err = fmt.Errorf("no entries in index %s with id %s", query.Index, query.Id)
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

	text_json.Text = source[query.Field]
	buf, _ = json.Marshal(text_json)

	sentRes, err := http.Post(FISSION_HOSTNAME+"/analysis/sentiment/v1", "application/json", bytes.NewReader(buf))
	if err != nil {
		return
	}

	buf, _ = io.ReadAll(sentRes.Body)
	if sentRes.StatusCode != http.StatusOK {
		err = fmt.Errorf("analysis/sentiment/v1: %s", buf)
		return
	}

	err = json.Unmarshal(buf, &sentiment)
	if err != nil {
		err = fmt.Errorf("json from vader: %s", buf)
		return
	}

	_, err = client.Index("sentiment").Request(sentiment).Do(context.Background())
	return
}
