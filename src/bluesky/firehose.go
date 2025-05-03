package main

import (
	"bytes"
	"context"
	"encoding/json"
	"fmt"
	"log"
	"net/http"
	"os"
	"time"

	"github.com/bluesky-social/indigo/api/atproto"
	appbsky "github.com/bluesky-social/indigo/api/bsky"
	"github.com/bluesky-social/indigo/events"
	"github.com/bluesky-social/indigo/events/schedulers/sequential"
	lexutil "github.com/bluesky-social/indigo/lex/util"
	"github.com/bluesky-social/indigo/repo"
	"github.com/bluesky-social/indigo/repomgr"
	es "github.com/elastic/go-elasticsearch/v8"
	"github.com/gorilla/websocket"
)

type MockHTTPResponse struct {
}

func (m *MockHTTPResponse) Write(buf []byte) (int, error) {
	fmt.Printf("%s", buf)

	return 0, nil
}

func (m *MockHTTPResponse) WriteHeader(status int) {

}

func (m *MockHTTPResponse) Header() http.Header {
	return make(http.Header)
}

// func main() {
// 	Handler(&MockHTTPResponse{}, nil)
// }

func config(key string) string {
	path := "/configs/default/shared-data/" + key

	buf, err := os.ReadFile(path)
	if err != nil {
		log.Println("error reading config map: %s", err)
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

	client, err := es.NewClient(es.Config{
		Addresses: []string{"http://elasticsearch-master.elastic.svc.cluster.local:9200"},
		Username:  config("ES_USERNAME"),
		Password:  config("ES_PASSWORD"),
	})
	if err != nil {
		log.Println(err)
		return nil
	}

	for _, op := range evt.Ops {
		if repomgr.EventKind(op.Action) != repomgr.EvtKindCreateRecord {
			continue
		}

		rc, rec, err := rr.GetRecord(context.Background(), op.Path)
		if err != nil {
			e := fmt.Errorf("getting record %s (%s) within seq %d for %s: %w", op.Path, *op.Cid, evt.Seq, evt.Repo, err)
			log.Println(e)
		}

		if lexutil.LexLink(rc) != *op.Cid {
			log.Printf("mismatch in record and op cid: %s != %s", rc, *op.Cid)
		}

		banana := lexutil.LexiconTypeDecoder{
			Val: rec,
		}

		b, err := banana.MarshalJSON()
		if err != nil {
			log.Println(err)
		}

		var pst = appbsky.FeedPost{}
		err = json.Unmarshal(b, &pst)
		if err != nil {
			log.Println(err)
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

		buf, _ := json.Marshal(post)
		client.Index("bluesky", bytes.NewReader(buf))
	}

	return nil
}
