package main

import (
	"bytes"
	"context"
	"encoding/json"
	"fmt"
	"log"
	"net/http"

	es "github.com/elastic/go-elasticsearch/v8"
	"github.com/elastic/go-elasticsearch/v8/esapi"
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

type Post struct {
	Cid       string `json:"cid"`
	Did       string `json:"did"`
	CreatedAt string `json:"createdAt"`
	Text      string `json:"text"`
}

func Handler(w http.ResponseWriter, r *http.Request) {
	post := Post{
		Cid:       "bafyreidgc233lxczf7gtonsewzae4s45el6ggtnktcxtxl4eal6lcffo7e",
		Did:       "did:plc:biug6mgsk6i7ymfdop2dqeva",
		CreatedAt: "2025-05-04T09:34:40.128174Z",
		Text:      "BBC Radio 1 Anthems",
	}

	client, err := es.NewTypedClient(es.Config{
		Addresses:              []string{"https://localhost:9200"},
		Username:               "elastic",
		Password:               "Mi0zu6yaiz1oThithoh3Di8kohphu9pi",
		CertificateFingerprint: "5FD336DE4088D4F31C833275E9085871186FDBA6C92938C14B3C89D868AAE404",
	})
	if err != nil {
		log.Println(err)
		return
	}

	buf, _ := json.Marshal(post)

	//res, err := client.Index("bluesky").Id(post.Cid).Request(post).Do(context.Background())
	req := esapi.IndexRequest{
		Index:      "bluesky",
		Body:       bytes.NewReader(buf),
		DocumentID: post.Cid,
		Refresh:    "true",
	}

	res, err := req.Do(context.Background(), client)
	if err != nil {
		log.Println("error indexing document: ", err)
		return
	}

	if res.IsError() {
		log.Println("error in elasticsearch: ", res.String())
	}
}
