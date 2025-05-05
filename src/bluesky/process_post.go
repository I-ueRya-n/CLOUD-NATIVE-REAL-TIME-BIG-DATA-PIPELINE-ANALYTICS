package main

import (
	"bytes"
	"context"
	"encoding/json"
	"io"
	"log"
	"net/http"

	"github.com/bluesky-social/indigo/api/atproto"
	appbsky "github.com/bluesky-social/indigo/api/bsky"
	lexutil "github.com/bluesky-social/indigo/lex/util"
	"github.com/bluesky-social/indigo/repo"
	"github.com/bluesky-social/indigo/repomgr"
	es "github.com/elastic/go-elasticsearch/v8"
)

type Post struct {
	Cid       string `json:"cid"`
	Did       string `json:"did"`
	CreatedAt string `json:"createdAt"`
	Text      string `json:"text"`
}

var client *es.TypedClient

func PostHandler(w http.ResponseWriter, r *http.Request) {
	if r == nil {
		w.WriteHeader(http.StatusInternalServerError)
		w.Write([]byte("request is nil"))
		return
	}

	buf, err := io.ReadAll(r.Body)
	if err != nil {
		log.Println("process post: ", err)
		w.WriteHeader(http.StatusInternalServerError)
		w.Write([]byte(err.Error()))
		return
	}

	var evt atproto.SyncSubscribeRepos_Commit
	err = json.Unmarshal(buf, &evt)
	if err != nil {
		log.Println("process post: ", err)
		w.WriteHeader(http.StatusInternalServerError)
		w.Write([]byte(err.Error()))
		return
	}

	p, err := processRepoCommit(&evt)
	if err != nil {
		log.Println("process post: ", err)
		w.WriteHeader(http.StatusInternalServerError)
		w.Write([]byte(err.Error()))
		return
	}

	if p == nil {
		w.WriteHeader(http.StatusNotFound)
		return
	}

	buf, _ = json.Marshal(p)
	w.Write(buf)
}

func processRepoCommit(evt *atproto.SyncSubscribeRepos_Commit) (post *Post, err error) {
	ctx := context.Background()
	rr, err := repo.ReadRepoFromCar(ctx, bytes.NewReader(evt.Blocks))
	if err != nil {
		log.Println(err)
		return nil, nil
	}

	for _, op := range evt.Ops {
		if repomgr.EventKind(op.Action) != repomgr.EvtKindCreateRecord {
			continue
		}

		rc, rec, err := rr.GetRecord(ctx, op.Path)
		if err != nil {
			log.Println(err)
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

		post := &Post{
			Cid:       op.Cid.String(),
			Did:       evt.Repo,
			CreatedAt: pst.CreatedAt,
			Text:      pst.Text,
		}
		return post, nil
	}

	return nil, nil
}
