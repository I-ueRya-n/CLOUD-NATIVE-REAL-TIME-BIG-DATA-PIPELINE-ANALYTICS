package main

import (
	"bytes"
	"context"
	"encoding/json"
	"io"
	"log"
	"net/http"
	"os"
	"sync/atomic"
	"time"

	"github.com/bluesky-social/indigo/api/atproto"
	"github.com/bluesky-social/indigo/events"
	"github.com/bluesky-social/indigo/events/schedulers/sequential"
	es "github.com/elastic/go-elasticsearch/v8"
	"github.com/elastic/go-elasticsearch/v8/esutil"
	"github.com/gorilla/websocket"
)

const ES_INDEX = "bluesky"

var bi esutil.BulkIndexer
var countSuccessful atomic.Uint64

func config(key string) string {
	path := "/configs/default/shared-data/" + key

	buf, err := os.ReadFile(path)
	if err != nil {
		log.Println("error reading config map: ", err)
		return ""
	}

	return string(buf[:])
}

func main() {
	err := initClient()
	if err != nil {
		log.Println(err)
		return
	}

	uri := "wss://bsky.network/xrpc/com.atproto.sync.subscribeRepos"
	dialer := websocket.Dialer{
		Proxy:            http.ProxyFromEnvironment,
		HandshakeTimeout: 30 * time.Minute,
	}

	con, _, err := dialer.Dial(uri, http.Header{})
	if err != nil {
		log.Println(err)
	}

	rsc := &events.RepoStreamCallbacks{
		RepoCommit: handleRepoCommit,
	}

	go func() {
		for {
			time.Sleep(1 * time.Minute)

			log.Printf("indexed %d docs", countSuccessful.Load())
			countSuccessful.Store(0)
		}
	}()

	sched := sequential.NewScheduler("firehose", rsc.EventHandler)
	events.HandleRepoStream(context.Background(), con, sched, nil)
}

func initClient() error {
	client, err := es.NewClient(es.Config{
		Addresses:              []string{"https://elasticsearch-master.elastic.svc.cluster.local:9200"},
		Username:               config("ES_USERNAME"),
		Password:               config("ES_PASSWORD"),
		CertificateFingerprint: config("ES_FINGERPRINT"),
	})
	if err != nil {
		return err
	}

	bi, err = esutil.NewBulkIndexer(esutil.BulkIndexerConfig{
		Index:         "bluesky",
		Client:        client,
		NumWorkers:    8,
		FlushBytes:    1_000_000,
		FlushInterval: 30 * time.Second,
	})
	if err != nil {
		return err
	}

	return nil
}

func handleRepoCommit(evt *atproto.SyncSubscribeRepos_Commit) error {
	buf, err := json.Marshal(evt)
	if err != nil {
		log.Println("error marshalling repo commit: ", err)
		return nil
	}

	res, err := http.Post("http://router.fission.svc.cluster.local/bluesky/repo-commit", "application/json", bytes.NewReader(buf))
	if err != nil {
		log.Println("error writing commit: ", err)
		return nil
	}

	if res.StatusCode == http.StatusNotFound {
		return nil
	} else if res.StatusCode != http.StatusOK {
		log.Println("error in repo commit: ", string(buf[:]))
		return nil
	}

	buf, _ = io.ReadAll(res.Body)
	var post Post
	_ = json.Unmarshal(buf, &post)

	err = bi.Add(
		context.Background(),
		esutil.BulkIndexerItem{
			Action:     "index",
			DocumentID: post.Cid,
			Body:       bytes.NewReader(buf),

			OnSuccess: func(ctx context.Context, item esutil.BulkIndexerItem, res esutil.BulkIndexerResponseItem) {
				countSuccessful.Add(1)
			},

			OnFailure: func(ctx context.Context, item esutil.BulkIndexerItem,
				res esutil.BulkIndexerResponseItem, err error) {
				if err != nil {
					log.Printf("ERROR: %s", err)
				} else {
					log.Printf("ERROR: %s: %s", res.Error.Type, res.Error.Reason)
				}
			},
		},
	)
	if err != nil {
		log.Println(err)
	}

	return nil
}
