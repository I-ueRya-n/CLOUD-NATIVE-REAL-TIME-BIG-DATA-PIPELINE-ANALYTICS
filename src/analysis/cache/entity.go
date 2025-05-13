package main

import (
	"bytes"
	"encoding/json"
	"fmt"
	"io"
	"net/http"
)

type NamedEntities struct {
	Idx     string              `json:"id"`
	Index   string              `json:"index"`
	Entites map[string][]string `json:"entities"`
}

func (n NamedEntities) Id() string {
	return n.Idx
}

/*
Handler: takes a list of id's from an elastic search index,
and calculates the sentiment of each one, using the 'sentiment'
es index as a cache for previously calculated sentiments.
*/
func EntityHandler(w http.ResponseWriter, r *http.Request) {
	conf := Config[NamedEntities]{
		w:          w,
		r:          r,
		calculate:  CalculateNamed,
		cacheIndex: "named-entity",
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

func CalculateNamed(index, id, text string) (n NamedEntities, err error) {
	var text_json struct {
		Text string `json:"text"`
	}

	text_json.Text = text
	buf, err := json.Marshal(text_json)
	if err != nil {
		return
	}

	addr := config("FISSION_HOSTNAME") + "/analysis/ner/v1"
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

	err = json.Unmarshal(buf, &n.Entites)
	if err != nil {
		err = fmt.Errorf("json from named-entity: %s", buf)
		return
	}

	n.Idx = id
	n.Index = index
	return
}
