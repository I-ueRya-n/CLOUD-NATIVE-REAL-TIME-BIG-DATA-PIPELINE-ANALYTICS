package main

import (
	"bytes"
	"encoding/json"
	"fmt"
	"io"
	"log"
	"net/http"
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
		w:          w,
		r:          r,
		calculate:  CalculateSentiment,
		cacheIndex: "sentiment",
	}

	sentiment, err := retrieveCache(conf)
	if err != nil {
		returnError(w, err.Error())
	}

	buf, err := json.Marshal(sentiment)
	if err != nil {
		log.Println("buffer:", string(buf[:]))
		returnError(w, err.Error())
	}

	w.Write(buf)
}

func CalculateSentiment(index, id, text string) (s Sentiment, err error) {
	var text_json struct {
		Text string `json:"text"`
	}

	text_json.Text = text
	buf, err := json.Marshal(text_json)
	if err != nil {
		log.Println("buffer:", string(buf[:]))
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
		err = fmt.Errorf("%s: %s", addr, buf)
		return
	}

	err = json.Unmarshal(buf, &s)
	if err != nil {
		log.Println("buffer:", string(buf[:]))
		err = fmt.Errorf("json from vader: %s", buf)
		return
	}

	s.Idx = id
	s.Index = index
	return
}
