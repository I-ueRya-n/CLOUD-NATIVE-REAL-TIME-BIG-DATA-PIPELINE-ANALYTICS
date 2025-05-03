package main

import (
	"context"
	"encoding/json"
	"fmt"
	"log"
	"net/http"
	"sync"
	"time"

	"github.com/bluesky-social/indigo/api/atproto"
	"github.com/bluesky-social/indigo/events"
	"github.com/bluesky-social/indigo/events/schedulers/sequential"
	"github.com/gorilla/websocket"
)

func Handler(w http.ResponseWriter, r *http.Request) {
	uri := "wss://bsky.network/xrpc/com.atproto.sync.subscribeRepos"
	con, _, err := websocket.DefaultDialer.Dial(uri, http.Header{})
	if err != nil {
		log.Println(err)
	}

	var l sync.Mutex
	array := make([]string, 0, 50)

	rsc := &events.RepoStreamCallbacks{
		RepoCommit: func(evt *atproto.SyncSubscribeRepos_Commit) error {
			for _, op := range evt.Ops {
				s := fmt.Sprintf("%s: %s record from %s", evt.Repo, op.Action, op.Path)

				l.Lock()
				array = append(array, s)
				l.Unlock()
			}
			return nil
		},
	}

	ctx, closed := context.WithCancel(context.Background())
	sched := sequential.NewScheduler("myfirehose", rsc.EventHandler)
	go events.HandleRepoStream(ctx, con, sched, nil)

	time.Sleep(time.Second)
	closed()

	l.Lock()
	buf, err := json.Marshal(array)
	if err != nil {
		log.Println(err)
	}

	w.Write(buf)
}
