package main

import (
	"bytes"
	"context"
	"encoding/json"
	"fmt"
	"io"
	"log"
	"net/http"
	"strconv"
	"testing"
	"time"

	es "github.com/elastic/go-elasticsearch/v8"
)

func TestCache(t *testing.T) {
	client, err := es.NewTypedClient(es.Config{
		Addresses:              []string{"https://localhost:9200"},
		Username:               "elastic",
		Password:               "Mi0zu6yaiz1oThithoh3Di8kohphu9pi",
		CertificateFingerprint: "5FD336DE4088D4F31C833275E9085871186FDBA6C92938C14B3C89D868AAE404",
	})
	if err != nil {
		t.Error(err)
		return
	}

	// clean up indices
	client.Indices.Delete(cacheTestIndex).Do(context.Background())
	client.Indices.Delete(testIndex).Do(context.Background())

	// create new indices
	_, err = client.Indices.Create(cacheTestIndex).Do(context.Background())
	if err != nil {
		t.Error(err)
		return
	}

	_, err = client.Indices.Create(testIndex).Do(context.Background())
	if err != nil {
		t.Error(err)
		return
	}

	// add items to test index
	ss := []string{"hello", "world!", "lorem"}
	for i, s := range ss {
		id := strconv.Itoa(i)
		item := map[string]string{"text": s}
		_, err = client.Index(testIndex).Id(id).Document(item).Do(context.Background())
		if err != nil {
			t.Error(err)
			return
		}
	}

	// calculate 'hello' and check its in the cache
	queryCache(t, []int{0, 1}, ss[:2])
	time.Sleep(3 * time.Second)

	checkCacheValue(t, client, 0, ss[0])
	checkCacheValue(t, client, 1, ss[1])

	// add 'Hello World!' to cache with the id of 'lorem'
	// and check it returns the length of 'Hello world!',
	// not 'lorem'
	addItemToCache(t, client, 2, "Hello World!")
	time.Sleep(3 * time.Second)

	queryCache(t, []int{2}, []string{"Hello World!"})
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
	var data []TestItem
	err = json.Unmarshal(buf, &data)
	if err != nil {
		log.Println("recieved:", string(buf[:]))
		t.Error(err)
	}

	if len(data) != len(id) {
		t.Error("incorrect number of return vals")
	}

	for i := range id {
		item, _ := CalculateItem(testIndex, strconv.Itoa(id[i]), value[i])
		err = isEqual(data[i], item)
		if err != nil {
			log.Println(data[i], item)
			t.Error(id, ":", err)
		}
	}
}

func checkCacheValue(t *testing.T, client *es.TypedClient, id int, value string) {
	strID := fmt.Sprint(testIndex, "-", id)
	res, err := client.Get(cacheTestIndex, strID).Do(context.Background())
	if err != nil {
		t.Error(id, ":", err)
		return
	}

	var cacheItem TestItem
	err = json.Unmarshal(res.Source_, &cacheItem)
	if err != nil {
		log.Println("source:", string(res.Source_[:]))
		t.Error(id, ":", err)
		return
	}

	item, _ := CalculateItem(testIndex, strconv.Itoa(id), value)
	err = isEqual(cacheItem, item)
	if err != nil {
		t.Error(id, ":", err)
		return
	}
}

func addItemToCache(t *testing.T, client *es.TypedClient, id int, value string) {
	strID := fmt.Sprint(testIndex, "-", id)
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

func isEqual(t1 TestItem, t2 TestItem) error {
	if t1.Idx != t2.Idx {
		return fmt.Errorf("expected %v, got %v", t2.Idx, t1.Idx)
	}

	if t1.Index != t2.Index {
		return fmt.Errorf("expected %v, got %v", t2.Index, t1.Index)
	}

	if t1.Value != t2.Value {
		return fmt.Errorf("expected %v, got %v", t2.Value, t1.Value)
	}

	return nil
}
