package main

import (
	"context"
	"encoding/json"
	"fmt"
	"io"
	"log"
	"net/http"
	"os"
	"sync"

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
	w          http.ResponseWriter
	r          *http.Request
	calculate  func(index, id, text string) (T, error)
	cacheIndex string
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
	// inverse mapping from query to index
	queryIndex := make(map[string]int, 2*len(query))
	for i, q := range query {
		queryIndex[q] = i
	}

	exists := make([]bool, len(query))
	items := make([]types.Query, len(query))

	{
		// search cache for sentiments
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

		res, err := client.Search().Index(conf.cacheIndex).Request(&req).Do(context.Background())
		if err != nil {
			return cache, err
		}

		results := res.Hits.Hits
		cache = make([]T, len(query))

		// add cached sentiments to result
		for _, item := range results {
			source := item.Source_
			var item T

			err = json.Unmarshal(source, &item)
			if err != nil {
				log.Println("json item:", err)
				continue
			}

			id := item.Id()
			cache[queryIndex[id]] = item
			exists[queryIndex[id]] = true
		}

		log.Printf("cache: %d pre-calculated", len(results))
	}

	{
		// calculate sentiment for posts not cached
		items = items[:0]

		for i, id := range query {
			if exists[i] {
				continue
			}

			items = append(items, matchField("_id", id))
		}

		size := len(items)
		req := search.Request{
			Size: &size,
			Query: &types.Query{
				Bool: &types.BoolQuery{
					Should: items,
				},
			},
		}

		// search index for the content of posts
		res, err := client.Search().Index(index).Request(&req).Do(context.Background())
		if err != nil {
			return cache, err
		}

		results := res.Hits.Hits

		var wg sync.WaitGroup
		j := 0

		log.Printf("cache: calculating %d", len(results))

		// calculate values
		for _, item := range results {
			var fields map[string]string

			err = json.Unmarshal(item.Source_, &fields)
			if err != nil {
				log.Println("fetching cache:", err)
				continue
			}

			j++

			wg.Add(1)
			go func(i int, id, text string) {
				cache[i], err = conf.calculate(index, id, text)
				if err != nil {
					log.Println("caching index", index, ":", err)
				}

				wg.Done()
			}(queryIndex[*item.Id_], *item.Id_, fields[field])
		}

		wg.Wait()
	}

	// insert newly calculated posts to elastic search
	for i, item := range cache {
		if exists[i] || item.Id() == "" {
			// no item
			continue
		}

		cacheID := index + "-" + cache[i].Id()

		_, err := client.Index(conf.cacheIndex).Id(cacheID).Request(item).Do(context.Background())
		if err != nil {
			log.Println("fetching cache:", err)
		}
	}

	return
}
