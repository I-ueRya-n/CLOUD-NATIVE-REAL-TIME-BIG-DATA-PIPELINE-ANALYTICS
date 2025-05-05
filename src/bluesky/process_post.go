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
	"github.com/elastic/go-elasticsearch/v8/esapi"
)

type Post struct {
	Cid       string `json:"cid"`
	Did       string `json:"did"`
	CreatedAt string `json:"createdAt"`
	Text      string `json:"text"`
}

var client *es.TypedClient

func PostHandler(w http.ResponseWriter, r *http.Request) {
	var err error
	client, err = es.NewTypedClient(es.Config{
		Addresses:              []string{"https://elasticsearch-master.elastic.svc.cluster.local:9200"},
		Username:               config("ES_USERNAME"),
		Password:               config("ES_PASSWORD"),
		CertificateFingerprint: config("ES_FINGERPRINT"),
	})
	if err != nil {
		log.Println(err)
		return
	}

	if r == nil {
		log.Println("process post: ", "request is nil")
		return
	}

	buf, err := io.ReadAll(r.Body)
	if err != nil {
		log.Println("process post: ", err)
	}

	var evt atproto.SyncSubscribeRepos_Commit
	err = json.Unmarshal(buf, &evt)
	if err != nil {
		log.Println("process post: ", err)
	}

	err = processRepoCommit(&evt)
	if err != nil {
		log.Println("process post: ", err)
	}
}

func processRepoCommit(evt *atproto.SyncSubscribeRepos_Commit) error {
	ctx := context.Background()
	rr, err := repo.ReadRepoFromCar(ctx, bytes.NewReader(evt.Blocks))
	if err != nil {
		return err
	}

	for _, op := range evt.Ops {
		if repomgr.EventKind(op.Action) != repomgr.EvtKindCreateRecord {
			continue
		}

		rc, rec, err := rr.GetRecord(ctx, op.Path)
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

		indexPosts(ctx, post)
	}

	return nil
}
func indexPosts(ctx context.Context, post Post) {
	if client == nil {
		log.Println("error: ", "client is not initialised")
		return
	}

	buf, err := json.Marshal(post)
	if err != nil {
		log.Println("error marshalling json: ", err)
	}

	req := esapi.IndexRequest{
		Index:      "bluesky",
		Body:       bytes.NewReader(buf),
		DocumentID: post.Cid,
		Refresh:    "true",
	}

	res, err := req.Do(ctx, client)
	if err != nil {
		log.Println("error indexing document: ", err)
		return
	}

	if res.IsError() {
		log.Println("error in elasticsearch: ", res.String())
	}
}
