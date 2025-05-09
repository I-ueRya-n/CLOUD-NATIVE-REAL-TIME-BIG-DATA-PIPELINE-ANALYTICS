package main

import (
	"bytes"
	"context"
	"encoding/json"
	"fmt"
	"io"
	"log"
	"net/http"

	es "github.com/elastic/go-elasticsearch/v8"
	"github.com/elastic/go-elasticsearch/v8/typedapi/core/search"
)

type Sentiment struct {
	Idx      string  `json:"id"`
	Index    string  `json:"index"`
	Negative float64 `json:"neg"`
	Neutral  float64 `json:"neu"`
	Positive float64 `json:"pos"`
	Compound float64 `json:"compound"`
}

func (s Sentiment) Id() string {
	return s.Idx
}

/*
Handler: takes a list of id's from an elastic search index,
and calculates the sentiment of each one, using the 'sentiment'
es index as a cache for previously calculated sentiments.
*/
func SentimentHandler(w http.ResponseWriter, r *http.Request) {
	conf := Config[Sentiment]{
		w:             w,
		r:             r,
		calculateItem: calculatePostSentiment,
		cacheIndex:    "sentiment",
	}

	sentiment, err := retrieveCache(conf)
	if err != nil {
		returnError(w, err.Error())
	}

	buf, err := json.Marshal(sentiment)
	if err != nil {
		returnError(w, err.Error())
	}

	w.Write(buf)
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

	err = json.Unmarshal(entry_json, &source)
	if err != nil {
		return
	}

	var text_json struct {
		Text string `json:"text"`
	}

	text_json.Text = source[field]
	buf, err := json.Marshal(text_json)
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

	sentiment.Idx = id
	sentiment.Index = index
	return
}
