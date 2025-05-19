package main

import (
	"bytes"
	"context"
	"encoding/json"
	"io"
	"log"
	"net/http"
	"os"
	"slices"
	"sync/atomic"
	"time"

	"github.com/bluesky-social/indigo/api/atproto"
	"github.com/bluesky-social/indigo/events"
	"github.com/bluesky-social/indigo/events/schedulers/parallel"
	es "github.com/elastic/go-elasticsearch/v8"
	"github.com/elastic/go-elasticsearch/v8/esutil"
	"github.com/gorilla/websocket"
)

const ES_INDEX = "bluesky"

var bi esutil.BulkIndexer
var countSuccessful atomic.Uint64

// config: get the value for a key from the config map
func config(key string) string {
	path := "/configs/default/shared-data/" + key

	buf, err := os.ReadFile(path)
	if err != nil {
		log.Println("error reading config map: ", err)
		return ""
	}

	return string(buf[:])
}

// main: Listen to the bluesky firehose, and pass any commit Ops
// to the handleRepoCommit function
func main() {
	err := initClient()
	if err != nil {
		log.Println(err)
		return
	}

	go countIndex()
	uri := "wss://bsky.network/xrpc/com.atproto.sync.subscribeRepos"
	dialer := websocket.Dialer{
		Proxy:            http.ProxyFromEnvironment,
		HandshakeTimeout: 45 * time.Second,
	}

	for {
		con, _, err := dialer.Dial(uri, http.Header{})
		if err != nil {
			log.Println("dial bsky:", err)
		}

		rsc := &events.RepoStreamCallbacks{
			RepoCommit: handleRepoCommit,
		}

		sched := parallel.NewScheduler(100, 1000, "wss://bsky.network", rsc.EventHandler)

		err = events.HandleRepoStream(context.Background(), con, sched, nil)
		if err != nil {
			log.Println("handle repo stream:", err)
		}
	}
}

// initClient: initialise elasticsearch bulk indexer
func initClient() error {
	client, err := es.NewClient(es.Config{
		Addresses:              []string{config("ES_HOSTNAME")},
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

// countIndex: log the number of docs indexed per hour
func countIndex() {
	for {
		time.Sleep(1 * time.Hour)

		log.Printf("indexed %d docs", countSuccessful.Load())
		countSuccessful.Store(0)
	}
}

// handleRepoCommit: post a bluesky repo commit to the fission
// function at /bluesky/repo-commit. If the response is 200 OK,
// insert the post, contained in the body of the response as a
// json, to the bluesky elastic search index using the bulk
// indexer. If the response is a 404 not found, the commit did
// not contain a post, so we ignore this commit.
func handleRepoCommit(evt *atproto.SyncSubscribeRepos_Commit) error {
	if !slices.ContainsFunc(evt.Ops, isCreateRecord) {
		// not a create record commit
		return nil
	}

	buf, err := json.Marshal(evt)
	if err != nil {
		log.Println("error marshalling repo commit: ", err)
		return nil
	}

	addr := config("FISSION_HOSTNAME") + "/bluesky/repo-commit"
	res, err := http.Post(addr, "application/json", bytes.NewReader(buf))
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
