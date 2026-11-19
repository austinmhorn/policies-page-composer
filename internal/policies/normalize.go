// Package policies converts generic Notion pages into the directory's JSON contract.
package policies

import (
 "fmt"
 "strings"
)

type Policy struct {
 Title string `json:"title"`
 Number string `json:"number"`
 Manual string `json:"manual"`
 DeepLink string `json:"deep_link"`
 Keywords []string `json:"keywords"`
 NotionPageID string `json:"notion_page_id"`
}

func object(v any) map[string]any {m,_:=v.(map[string]any);return m}
func value(v any) string {s,_:=v.(string);return s}
func plainText(v any) string {
 parts,_:=v.([]any)
 var b strings.Builder
 for _,part:=range parts {
  p:=object(part)
  s:=value(p["plain_text"])
  if s=="" {s=value(object(p["text"])["content"])}
  b.WriteString(s)
 }
 return strings.TrimSpace(b.String())
}
func field(prop any) string {
 p:=object(prop)
 kind:=value(p["type"])
 switch kind {
 case "title","rich_text": return plainText(p[kind])
 case "url": return strings.TrimSpace(value(p["url"]))
 case "select","status": return strings.TrimSpace(value(object(p[kind])["name"]))
 case "number":
  if n,ok:=p["number"].(float64);ok {return fmt.Sprintf("%g",n)}
 case "formula":
  f:=object(p["formula"])
  if value(f["type"])=="string" {return value(f["string"])}
 }
 return ""
}

func Normalize(pages []map[string]any) []Policy {
 out:=make([]Policy,0,len(pages))
 for _,page:=range pages {
  if page["archived"]==true || page["in_trash"]==true {continue}
  props:=object(page["properties"])
  manual:=field(props["Manual"])
  if manual=="" {
   for _,v:=range slice(object(props["Manual"])["multi_select"]){
    n:=strings.TrimSpace(value(object(v)["name"]))
    if n!="" {if manual!="" {manual+=", "};manual+=n}
   }
  }
  keywords:=make([]string,0)
  kp:=object(props["Keywords"])
  if value(kp["type"])=="multi_select" {
   for _,v:=range slice(kp["multi_select"]){
    if n:=strings.TrimSpace(value(object(v)["name"]));n!="" {keywords=append(keywords,n)}
   }
  }else{
   for _,n:=range strings.Split(field(kp),",") {
    if n=strings.TrimSpace(n);n!="" {keywords=append(keywords,n)}
   }
  }
  out=append(out,Policy{
   Title:field(props["Name"]),Number:field(props["Number"]),
   Manual:manual,DeepLink:field(props["Deep Link"]),
   Keywords:keywords,NotionPageID:value(page["id"]),
  })
 }
 return out
}
func slice(v any) []any {r,_:=v.([]any);return r}
