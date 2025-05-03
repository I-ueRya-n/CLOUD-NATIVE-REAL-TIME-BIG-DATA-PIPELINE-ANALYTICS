package main

import (
	"bytes"
	"context"
	"encoding/json"
	"fmt"
	"log"
	"net/http"
	"time"

	"github.com/bluesky-social/indigo/api/atproto"
	appbsky "github.com/bluesky-social/indigo/api/bsky"
	"github.com/bluesky-social/indigo/events"
	"github.com/bluesky-social/indigo/events/schedulers/sequential"
	lexutil "github.com/bluesky-social/indigo/lex/util"
	"github.com/bluesky-social/indigo/repo"
	"github.com/bluesky-social/indigo/repomgr"
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

func main() {
	Handler(&MockHTTPResponse{}, nil)
}

func Handler(w http.ResponseWriter, r *http.Request) {
	uri := "wss://bsky.network/xrpc/com.atproto.sync.subscribeRepos"
	con, _, err := websocket.DefaultDialer.Dial(uri, http.Header{})
	if err != nil {
		log.Println(err)
	}

	ctx, closed := context.WithCancel(context.Background())
	rsc := &events.RepoStreamCallbacks{
		RepoCommit: func(evt *atproto.SyncSubscribeRepos_Commit) error {
			rr, err := repo.ReadRepoFromCar(ctx, bytes.NewReader(evt.Blocks))
			if err != nil {
				fmt.Println(err)
			}

			for _, op := range evt.Ops {
				if repomgr.EventKind(op.Action) != repomgr.EvtKindCreateRecord {
					continue
				}

				rc, rec, err := rr.GetRecord(ctx, op.Path)
				if err != nil {
					e := fmt.Errorf("getting record %s (%s) within seq %d for %s: %w", op.Path, *op.Cid, evt.Seq, evt.Repo, err)
					log.Println(e)
				}

				if lexutil.LexLink(rc) != *op.Cid {
					return fmt.Errorf("mismatch in record and op cid: %s != %s", rc, *op.Cid)
				}

				banana := lexutil.LexiconTypeDecoder{
					Val: rec,
				}

				b, err := banana.MarshalJSON()
				if err != nil {
					fmt.Println(err)
				}

				var pst = appbsky.FeedPost{}
				err = json.Unmarshal(b, &pst)
				if err != nil {
					fmt.Println(err)
				}

				if pst.LexiconTypeID != "app.bsky.feed.post" {
					continue
				}

				fmt.Println(pst)
			}
			return nil
		},
	}

	sched := sequential.NewScheduler("myfirehose", rsc.EventHandler)
	go events.HandleRepoStream(ctx, con, sched, nil)

	time.Sleep(time.Second)
	closed()

	log.Println("firehose closed")
}
