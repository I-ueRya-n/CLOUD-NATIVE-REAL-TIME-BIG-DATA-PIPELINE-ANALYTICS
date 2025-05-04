package main

import (
	"bytes"
	"context"
	"encoding/json"
	"log"
	"net/http"
	"os"
	"sync/atomic"
	"time"

	"github.com/bluesky-social/indigo/api/atproto"
	appbsky "github.com/bluesky-social/indigo/api/bsky"
	"github.com/bluesky-social/indigo/events"
	"github.com/bluesky-social/indigo/events/schedulers/sequential"
	lexutil "github.com/bluesky-social/indigo/lex/util"
	"github.com/bluesky-social/indigo/repo"
	"github.com/bluesky-social/indigo/repomgr"
	es "github.com/elastic/go-elasticsearch/v8"
	"github.com/elastic/go-elasticsearch/v8/esutil"
	"github.com/gorilla/websocket"
)

const ES_INDEX = "bluesky"

func config(key string) string {
	path := "/configs/default/shared-data/" + key

	buf, err := os.ReadFile(path)
	if err != nil {
		log.Println("error reading config map: ", err)
		return ""
	}

	return string(buf[:])
}

type Post struct {
	Cid       string `json:"cid"`
	Did       string `json:"did"`
	CreatedAt string `json:"createdAt"`
	Text      string `json:"text"`
}

var ch chan Post

func Handler(w http.ResponseWriter, r *http.Request) {
	uri := "wss://bsky.network/xrpc/com.atproto.sync.subscribeRepos"
	con, _, err := websocket.DefaultDialer.Dial(uri, http.Header{})
	if err != nil {
		log.Println(err)
	}

	ctx, closed := context.WithCancel(context.Background())
	rsc := &events.RepoStreamCallbacks{
		RepoCommit: handleRepoCommit,
	}

	ch = make(chan Post, 1_000)
	go indexPosts(ctx)

	sched := sequential.NewScheduler("myfirehose", rsc.EventHandler)
	go events.HandleRepoStream(ctx, con, sched, nil)

	time.Sleep(1 * time.Minute)
	log.Println("shutting down firehose function")
	closed()
}

func handleRepoCommit(evt *atproto.SyncSubscribeRepos_Commit) error {
	rr, err := repo.ReadRepoFromCar(context.Background(), bytes.NewReader(evt.Blocks))
	if err != nil {
		return err
	}

	for _, op := range evt.Ops {
		if repomgr.EventKind(op.Action) != repomgr.EvtKindCreateRecord {
			continue
		}

		rc, rec, err := rr.GetRecord(context.Background(), op.Path)
		if err != nil {
			log.Println("error getting record: ", err)
			continue
		}

		if lexutil.LexLink(rc) != *op.Cid {
			log.Printf("mismatch in record and op cid: %s != %s", rc, *op.Cid)
			continue
		}

		banana := lexutil.LexiconTypeDecoder{
			Val: rec,
		}

		b, err := banana.MarshalJSON()
		if err != nil {
			log.Println("error marshalling lexicon: ", err)
			continue
		}

		var pst = appbsky.FeedPost{}
		err = json.Unmarshal(b, &pst)
		if err != nil {
			log.Println("error marshalling post: ", err)
			continue
		}

		if pst.LexiconTypeID != "app.bsky.feed.post" {
			continue
		}

		post := Post{
			Cid:       op.Cid.String(),
			Did:       evt.Repo,
			CreatedAt: pst.CreatedAt,
			Text:      pst.Text,
		}

		ch <- post
	}

	return nil
}

func indexPosts(ctx context.Context) {
	client, err := es.NewClient(es.Config{
		Addresses:              []string{"https://elasticsearch-master.elastic.svc.cluster.local:9200"},
		Username:               config("ES_USERNAME"),
		Password:               config("ES_PASSWORD"),
		CertificateFingerprint: config("ES_FINGERPRINT"),

		RetryOnStatus: []int{502, 503, 504, 429},
		MaxRetries:    5,
	})
	if err != nil {
		log.Println(err)
		return
	}

	bi, err := esutil.NewBulkIndexer(esutil.BulkIndexerConfig{
		Index:         ES_INDEX,         // The default index name
		Client:        client,           // The Elasticsearch client
		NumWorkers:    8,                // The number of worker goroutines
		FlushBytes:    1_000_000,        // The flush threshold in bytes
		FlushInterval: 30 * time.Second, // The periodic flush interval
	})
	if err != nil {
		log.Fatalf("Error creating the indexer: %s", err)
	}

	var countSuccessful uint64
	var post Post

	for {
		select {
		case post = <-ch:
		case <-ctx.Done():
			if err := bi.Close(context.Background()); err != nil {
				log.Fatalf("Unexpected error: %s", err)
			}

			log.Printf("bluesky: indexed %d posts", countSuccessful)
			return
		}

		buf, err := json.Marshal(post)
		if err != nil {
			log.Println("error marshalling json: ", err)
			continue
		}

		err = bi.Add(
			context.Background(),
			esutil.BulkIndexerItem{
				Action:     "index",
				DocumentID: post.Cid,
				Body:       bytes.NewReader(buf),

				OnSuccess: func(ctx context.Context, item esutil.BulkIndexerItem, res esutil.BulkIndexerResponseItem) {
					atomic.AddUint64(&countSuccessful, 1)
				},

				OnFailure: func(ctx context.Context, item esutil.BulkIndexerItem,
					res esutil.BulkIndexerResponseItem, err error) {
					if err != nil {
						log.Printf("ERROR: %s", err)
					} else {
						log.Printf("ERROR: %s: %s", res.Error.Type, res.Error.Reason)
					}
				},
			})
		if err != nil {
			log.Println("error adding post to bulk indexer: ", err)
			continue
		}
	}

}
