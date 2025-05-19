package main

import (
	"bytes"
	"encoding/json"
	"io"
	"net/http"
	"os"
	"testing"
)

const endpoint = "http://localhost:9090/bluesky/repo-commit"

type Post struct {
	Cid       string `json:"cid"`
	Did       string `json:"did"`
	CreatedAt string `json:"createdAt"`
	Text      string `json:"text"`
}

var evt_posts = []string{
	"post1.json",
	"non_post.json",
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
	for i := range evt_posts {
		buf, err := os.ReadFile(evt_posts[i])
		if err != nil {
			t.Error(err.Error())
			continue
		}

		testProcessPost(t, buf, posts[i])
	}
}

func testProcessPost(t *testing.T, buf []byte, post *Post) {
	res, err := http.Post(endpoint, "application/json", bytes.NewReader(buf))
	if err != nil {
		t.Error(err.Error())
		return
	}

	buf, err = io.ReadAll(res.Body)
	if err != nil {
		t.Error(err)
		return
	}

	if post == nil && res.StatusCode == http.StatusNotFound {
		return
	}

	if res.StatusCode != http.StatusOK {
		t.Error(res.StatusCode, string(buf))
		return
	}

	var evt_post Post
	err = json.Unmarshal(buf, &evt_post)
	if err != nil {
		t.Errorf(string(buf))
		return
	}

	if evt_post.Cid != post.Cid {
		t.Errorf("cid: expected %v, got %v", post.Cid, evt_post.Cid)
		return
	}

	if evt_post.Did != post.Did {
		t.Errorf("did: expected %v, got %v", post.Did, evt_post.Did)
		return
	}

	if evt_post.CreatedAt != post.CreatedAt {
		t.Errorf("created at: expected %v, got %v", post.CreatedAt, evt_post.CreatedAt)
		return
	}

	if evt_post.Text != post.Text {
		t.Errorf("text: expected %v, got %v", post.Text, evt_post.Text)
		return
	}
}
