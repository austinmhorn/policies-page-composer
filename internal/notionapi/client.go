// Package notionapi contains a reusable, stateless Notion query client.
// It intentionally does not import or modify the production Property Data Engine.
package notionapi

import (
 "bytes"
 "context"
 "encoding/json"
 "errors"
 "fmt"
 "io"
 "net/http"
 "net/url"
 "strings"
 "time"
)

type Client struct {
 Token string
 DatabaseID string
 DataSourceID string
 BaseURL string
 HTTPClient *http.Client
}

func (c Client) Query(ctx context.Context) ([]map[string]any, error) {
 if strings.TrimSpace(c.Token)=="" { return nil, errors.New("NOTION_TOKEN is missing") }
 if (c.DatabaseID=="")==(c.DataSourceID=="") { return nil, errors.New("set exactly one of NOTION_DATABASE_ID or NOTION_DATA_SOURCE_ID") }
 base:=c.BaseURL
 if base=="" { base="https://api.notion.com" }
 u,err:=url.Parse(base)
 if err!=nil || (u.Scheme!="https" && !(u.Scheme=="http" && (u.Hostname()=="localhost" || u.Hostname()=="127.0.0.1"))) || u.Host=="" {
  return nil,errors.New("invalid Notion API base URL")
 }
 version:="2022-06-28"
 path:="/v1/databases/"+url.PathEscape(c.DatabaseID)+"/query"
 if c.DataSourceID!="" {
  version="2025-09-03"
  path="/v1/data_sources/"+url.PathEscape(c.DataSourceID)+"/query"
 }
 endpoint:=strings.TrimRight(base,"/")+path
 client:=c.HTTPClient
 if client==nil { client=&http.Client{Timeout:30*time.Second} }
 var pages []map[string]any
 cursor:=""
 seen:=make(map[string]bool)
 for {
  requestBody:=map[string]any{"page_size":100}
  if cursor!="" {requestBody["start_cursor"]=cursor}
  body,err:=json.Marshal(requestBody)
  if err!=nil {return nil,err}
  req,err:=http.NewRequestWithContext(ctx,http.MethodPost,endpoint,bytes.NewReader(body))
  if err!=nil {return nil,err}
  req.Header.Set("Authorization","Bearer "+c.Token)
  req.Header.Set("Notion-Version",version)
  req.Header.Set("Content-Type","application/json")
  resp,err:=client.Do(req)
  if err!=nil {return nil,fmt.Errorf("Notion query: %w",err)}
  limited:=io.LimitReader(resp.Body,16<<20)
  raw,readErr:=io.ReadAll(limited)
  closeErr:=resp.Body.Close()
  if readErr!=nil {return nil,fmt.Errorf("read Notion response: %w",readErr)}
  if closeErr!=nil {return nil,fmt.Errorf("close Notion response: %w",closeErr)}
  if resp.StatusCode!=http.StatusOK {
   return nil,fmt.Errorf("Notion query returned HTTP %d",resp.StatusCode)
  }
  var payload struct {
   Results []map[string]any `json:"results"`
   HasMore bool `json:"has_more"`
   NextCursor string `json:"next_cursor"`
  }
  if err:=json.Unmarshal(raw,&payload);err!=nil {return nil,fmt.Errorf("decode Notion response: %w",err)}
  if payload.Results==nil {return nil,errors.New("Notion response did not contain a results array")}
  pages=append(pages,payload.Results...)
  if !payload.HasMore {return pages,nil}
  if payload.NextCursor=="" || seen[payload.NextCursor] {return nil,errors.New("invalid or repeated Notion pagination cursor")}
  seen[payload.NextCursor]=true
  cursor=payload.NextCursor
 }
}
