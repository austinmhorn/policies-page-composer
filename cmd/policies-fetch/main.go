// policies-fetch reads DB.Policies through the Notion API and writes normalized JSON.
// This tool is read-only against Notion and never publishes to Interact.
package main

import (
 "context"
 "encoding/json"
 "errors"
 "flag"
 "fmt"
 "os"
 "path/filepath"
 "time"

 "github.com/austinmhorn/policies-page-composer/internal/notionapi"
 "github.com/austinmhorn/policies-page-composer/internal/policies"
)

func run() error {
 output:=flag.String("output","data/policies.json","normalized JSON output")
 flag.Parse()
 client:=notionapi.Client{
  Token:os.Getenv("NOTION_TOKEN"),
  DatabaseID:os.Getenv("NOTION_DATABASE_ID"),
  DataSourceID:os.Getenv("NOTION_DATA_SOURCE_ID"),
 }
 ctx,cancel:=context.WithTimeout(context.Background(),3*time.Minute)
 defer cancel()
 pages,err:=client.Query(ctx)
 if err!=nil {return err}
 records:=policies.Normalize(pages)
 if len(records)==0 {return errors.New("no active policy records; refusing to overwrite existing snapshot")}
 payload:=struct {
  GeneratedAt string `json:"generated_at"`
  Source string `json:"source"`
  Policies []policies.Policy `json:"policies"`
 }{time.Now().UTC().Format(time.RFC3339),"notion",records}
 raw,err:=json.MarshalIndent(payload,"","  ")
 if err!=nil {return err}
 if err:=os.MkdirAll(filepath.Dir(*output),0755);err!=nil {return err}
 temporary,err:=os.CreateTemp(filepath.Dir(*output),".policies-*.tmp")
 if err!=nil {return err}
 defer os.Remove(temporary.Name())
 if err:=temporary.Chmod(0600);err!=nil {temporary.Close();return err}
 if _,err:=temporary.Write(append(raw,'\n'));err!=nil {temporary.Close();return err}
 if err:=temporary.Close();err!=nil {return err}
 if err:=os.Rename(temporary.Name(),*output);err!=nil {return err}
 fmt.Printf("Fetched %d active policy records to %s\n",len(records),*output)
 return nil
}

func main(){
 if err:=run();err!=nil {fmt.Fprintln(os.Stderr,"policies-fetch:",err);os.Exit(1)}
}
