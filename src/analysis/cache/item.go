package main

import (
	"encoding/json"
	"net/http"
)

const (
	testIndex      = "test-items"
	cacheTestIndex = "cache-test"
	cacheEndpoint  = "http://localhost:9090/cache-test/index/" + testIndex + "/field/text"
)

type TestItem struct {
	Idx   string `json:"id"`
	Index string `json:"index"`
	Value int    `json:"value"`
}

func (t TestItem) Id() string {
	return t.Idx
}

/*
Handler: takes a list of id's from an elastic search index,
and calculates the sentiment of each one, using the 'sentiment'
es index as a cache for previously calculated sentiments.
*/
func ItemHandler(w http.ResponseWriter, r *http.Request) {
	conf := Config[TestItem]{
		w:          w,
		r:          r,
		calculate:  CalculateItem,
		cacheIndex: cacheTestIndex,
	}

	items, err := retrieveCache(conf)
	if err != nil {
		returnError(w, err.Error())
	}

	buf, err := json.Marshal(items)
	if err != nil {
		returnError(w, err.Error())
	}

	w.Write(buf)
}

func CalculateItem(index, id, text string) (t TestItem, err error) {
	t = TestItem{
		Index: index,
		Idx:   id,
		Value: len(text),
	}
	return
}
