package main

import (
	"bytes"
	"context"
	"encoding/json"
	"log"
	"net/http"
	"os"
	"time"

	"github.com/bluesky-social/indigo/api/atproto"
	"github.com/bluesky-social/indigo/events"
	"github.com/bluesky-social/indigo/events/schedulers/sequential"
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

func FirehoseHandler(w http.ResponseWriter, r *http.Request) {
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

	time.Sleep(10 * time.Minute)
	log.Println("shutting down firehose function")
	closed()
}

func handleRepoCommit(evt *atproto.SyncSubscribeRepos_Commit) error {
	buf, err := json.Marshal(evt)
	if err != nil {
		log.Println("error marshalling repo commit: ", err)
		return err
	}

	_, err = http.Post("http://router.fission.svc.cluster.local/bluesky/repo-commit", "application/json", bytes.NewReader(buf))
	if err != nil {
		log.Println("error writing commit: ", err)
		return err
	}

	return nil
}
