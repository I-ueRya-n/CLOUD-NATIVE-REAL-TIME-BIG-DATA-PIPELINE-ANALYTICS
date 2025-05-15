package main

import (
	"bytes"
	"context"
	"encoding/json"
	"io"
	"net/http"
	"strconv"
	"testing"

	es "github.com/elastic/go-elasticsearch/v8"
)

const (
	testIndex      = "test-items"
	cacheTestIndex = "cache-test"
	cacheEndpoint  = "http://localhost:9090/cache-test"
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

func TestCache(t *testing.T) {
	client, err := es.NewTypedClient(es.Config{
		Addresses:              []string{"https://localhost:9200"},
		Username:               "elastic",
		Password:               "Mi0zu6yaiz1oThithoh3Di8kohphu9pi",
		CertificateFingerprint: "5FD336DE4088D4F31C833275E9085871186FDBA6C92938C14B3C89D868AAE404",
	})
	if err != nil {
		t.Error(err)
	}

	// clean up indices
	_, err = client.Indices.Delete(cacheTestIndex).Do(context.Background())
	if err != nil {
		t.Error(err)
	}

	_, err = client.Indices.Delete(testIndex).Do(context.Background())
	if err != nil {
		t.Error(err)
	}

	// create new indices
	_, err = client.Indices.Create(cacheTestIndex).Do(context.Background())
	if err != nil {
		t.Error(err)
	}

	_, err = client.Indices.Create(testIndex).Do(context.Background())
	if err != nil {
		t.Error(err)
	}

	// add items to test index
	ss := []string{"hello", "world!", "lorem ipsum"}
	for i, s := range ss {
		id := strconv.Itoa(i)
		item := map[string]string{"text": s}
		_, err = client.Index(testIndex).Id(id).Document(item).Do(context.Background())
		if err != nil {
			t.Error(err)
		}
	}

	// calculate 'hello' and check its in the cache
	queryCache(t, []int{0, 2}, []string{ss[0], ss[2]})
	checkCacheValue(t, client, 0, ss[0])

	// add 'Hello World!' to cache with the id of 'world'
	// and check it returns the length of 'Hello world!',
	// not 'world!'
	addItemToCache(t, client, 1, "Hello World!")
	queryCache(t, []int{1}, []string{"Hello World!"})
}

func queryCache(t *testing.T, id []int, value []string) {
	ids := make([]string, len(id))
	for i, v := range id {
		ids[i] = strconv.Itoa(v)
	}

	buf, err := json.Marshal(ids)
	if err != nil {
		t.Error(err)
	}

	res, err := http.Post(cacheEndpoint, "application/json", bytes.NewReader(buf))
	if err != nil {
		t.Error(err)
	}

	buf, err = io.ReadAll(res.Body)
	if err != nil {
		t.Error(err)
	}

	if res.StatusCode != http.StatusOK {
		t.Errorf(string(buf))
	}

	// check return value is correct
	var data []int
	err = json.Unmarshal(buf, &data)
	if err != nil {
		t.Error(err)
	}

	if len(data) != 1 {
		t.Error("incorrect number of return vals")
	}

	if data[0] != len(value) {
		t.Errorf("expected %d got %d", len(value), data[0])
	}
}

func checkCacheValue(t *testing.T, client *es.TypedClient, id int, value string) {
	strID := testIndex + strconv.Itoa(id)
	res, err := client.Get(cacheTestIndex, strID).Do(context.Background())
	if err != nil {
		t.Error(err)
	}

	var cacheItem TestItem
	err = json.Unmarshal(res.Source_, cacheItem)
	if err != nil {
		t.Error(err)
	}

	if cacheItem.Idx != strconv.Itoa(id) {
		t.Error("expected", id, "got", cacheItem.Idx)
	}

	if cacheItem.Index != testIndex {
		t.Error("expected", testIndex, "got", cacheItem.Index)
	}

	if cacheItem.Value != len(value) {
		t.Error("expected", len(value), "got", cacheItem.Value)
	}
}

func addItemToCache(t *testing.T, client *es.TypedClient, id int, value string) {
	strID := testIndex + strconv.Itoa(id)
	item := TestItem{
		Index: testIndex,
		Idx:   strconv.Itoa(id),
		Value: len(value),
	}

	_, err := client.Index(cacheTestIndex).Id(strID).Document(item).Do(context.Background())
	if err != nil {
		t.Error(err)
	}
}
