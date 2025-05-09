package main

import (
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

func returnError(w http.ResponseWriter, msg string) {
	w.WriteHeader(http.StatusInternalServerError)
	w.Write([]byte(msg))
	log.Fatalf(msg)
}

type CacheItem interface {
	Id() string
}

type Config[T CacheItem] struct {
	w http.ResponseWriter
	r *http.Request

	calculateItem func(client *es.TypedClient, index, field, id string) (T, error)
	cacheIndex    string
}

func retrieveCache[T CacheItem](conf Config[T]) ([]T, error) {
	index := conf.r.Header.Get("X-Fission-Params-Index")
	field := conf.r.Header.Get("X-Fission-Params-Field")

	buf, err := io.ReadAll(conf.r.Body)
	if err != nil {
		return nil, fmt.Errorf("reading request body: %s", err)
	}

	query := make([]string, 0, 1000)
	err = json.Unmarshal(buf, &query)
	if err != nil {
		return nil, fmt.Errorf("parsing query: %s", err)
	}

	log.Printf("received %d id's", len(query))

	client, err := es.NewTypedClient(es.Config{
		Addresses:              []string{config("ES_HOSTNAME")},
		Username:               config("ES_USERNAME"),
		Password:               config("ES_PASSWORD"),
		CertificateFingerprint: config("ES_FINGERPRINT"),
	})
	if err != nil {
		return nil, fmt.Errorf("es login: %s", err)
	}

	cache, err := fetchCache(client, conf, index, field, query)
	if err != nil {
		return nil, fmt.Errorf("fetching cache: %s", err)
	}

	log.Printf("cached %d posts", len(cache))
	return cache, nil
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
func fetchCache[T CacheItem](client *es.TypedClient, conf Config[T], index, field string,
	query []string) (cache []T, err error) {
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
	res, err := client.Search().Index(conf.cacheIndex).Request(&req).Do(context.Background())
	if err != nil {
		return
	}

	results := res.Hits.Hits
	cacheMap := make(map[string]T, len(query))

	// add cached sentiments to result
	for _, item := range results {
		source := item.Source_
		var item T

		err = json.Unmarshal(source, &item)
		if err != nil {
			log.Println("json item:", err)
			continue
		}

		cacheMap[item.Id()] = item
	}

	log.Printf("cache: %d pre-calculated", len(cache))

	// calculate sentiment for posts not cached
	for _, q := range query {
		if _, ok := cacheMap[q]; ok {
			continue
		}

		var item T
		item, err = conf.calculateItem(client, index, field, q)
		if err != nil {
			err = fmt.Errorf("calculating item: %s", err)
			return
		}

		err = insertIntoCache(client, conf.cacheIndex, index, item)
		if err != nil {
			err = fmt.Errorf("caching item: %s", err)
			return
		}
		cacheMap[item.Id()] = item
	}

	cache = slices.Collect(maps.Values(cacheMap))
	return
}

func insertIntoCache[T CacheItem](client *es.TypedClient, cache, index string, item T) error {
	cacheID := index + "-" + item.Id()
	_, err := client.Index(cache).Id(cacheID).Request(item).Do(context.Background())
	return err
}
