package notionapi

import (
 "context"
 "encoding/json"
 "net/http"
 "net/http/httptest"
 "testing"
)

func TestQueryPaginates(t *testing.T){
 requests:=0
 server:=httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter,r *http.Request){
  requests++
  if r.URL.Path!="/v1/data_sources/ds/query" {t.Errorf("path: %s",r.URL.Path)}
  if r.Header.Get("Notion-Version")!="2025-09-03" {t.Errorf("version")}
  if r.Header.Get("Authorization")!="Bearer test-token" {t.Errorf("authorization")}
  var body map[string]any
  if err:=json.NewDecoder(r.Body).Decode(&body);err!=nil {t.Error(err)}
  w.Header().Set("Content-Type","application/json")
  if requests==1 {
   if body["page_size"]!=float64(100) {t.Error("missing page size")}
   _,_=w.Write([]byte(`{"results":[{"id":"one"}],"has_more":true,"next_cursor":"abc"}`))
  }else{
   if body["start_cursor"]!="abc" {t.Error("cursor missing")}
   _,_=w.Write([]byte(`{"results":[{"id":"two"}],"has_more":false}`))
  }
 }))
 defer server.Close()
 c:=Client{Token:"test-token",DataSourceID:"ds",BaseURL:server.URL}
 pages,err:=c.Query(context.Background())
 if err!=nil {t.Fatal(err)}
 if len(pages)!=2 || requests!=2 {t.Fatalf("got %d pages from %d requests",len(pages),requests)}
}

func TestBadCursorFailsClosed(t *testing.T){
 server:=httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter,r *http.Request){
  _,_=w.Write([]byte(`{"results":[],"has_more":true,"next_cursor":""}`))
 }))
 defer server.Close()
 _,err:=(Client{Token:"x",DatabaseID:"db",BaseURL:server.URL}).Query(context.Background())
 if err==nil {t.Fatal("expected error")}
}

func TestRejectsMissingSource(t *testing.T){
 _,err:=(Client{Token:"x"}).Query(context.Background())
 if err==nil {t.Fatal("expected configuration error")}
}

func TestHTTPErrorFailsClosed(t *testing.T){
 server:=httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter,r *http.Request){w.WriteHeader(403)}))
 defer server.Close()
 _,err:=(Client{Token:"x",DatabaseID:"db",BaseURL:server.URL}).Query(context.Background())
 if err==nil {t.Fatal("expected HTTP error")}
}
