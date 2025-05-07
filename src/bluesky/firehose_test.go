package main

import (
	"encoding/json"
	"os"
	"testing"

	"github.com/bluesky-social/indigo/api/atproto"
)

var raw_post = []string{
	"tests/post1.json",
	"tests/non_post.json",
}

var posts = []*Post{
	{
		Cid:       "bafyreibefryhwhk3kp7ar6cmqps5ltjbdkel5md45buxcu4tvowfgset5i",
		Did:       "did:plc:jdq7iparuwd5f2q2w6zdkymz",
		CreatedAt: "2025-05-07T05:32:04.603Z",
		Text:      "the voop wyvern...",
	},
	nil,
}

func TestProcessing(t *testing.T) {
	for i := range raw_post {
		buf, err := os.ReadFile(raw_post[i])
		if err != nil {
			t.Error(err.Error())
		}

		var evt atproto.SyncSubscribeRepos_Commit
		err = json.Unmarshal(buf, &evt)
		if err != nil {
			t.Error(err.Error())
		}

		testProcessPost(t, &evt, posts[i])
	}
}

func testProcessPost(t *testing.T, evt *atproto.SyncSubscribeRepos_Commit, post *Post) {
	evt_post, err := processRepoCommit(evt)
	if err != nil {
		t.Error(err.Error())
	}

	if evt_post == nil && post == nil {
		return
	}

	if evt_post.Cid != post.Cid {
		t.Errorf("cid: expected %v, got %v", post.Cid, evt_post.Cid)
	}

	if evt_post.Did != post.Did {
		t.Errorf("did: expected %v, got %v", post.Did, evt_post.Did)
	}

	if evt_post.CreatedAt != post.CreatedAt {
		t.Errorf("created at: expected %v, got %v", post.CreatedAt, evt_post.CreatedAt)
	}

	if evt_post.Text != post.Text {
		t.Errorf("text: expected %v, got %v", post.Text, evt_post.Text)
	}
}
