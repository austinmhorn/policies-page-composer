package policies

import "testing"

func TestNormalizeRetainsComplexNumbersAndKeywords(t *testing.T){
 pages:=[]map[string]any{{"id":"page-1","properties":map[string]any{
  "Name":map[string]any{"type":"title","title":[]any{map[string]any{"plain_text":"Entrata – "},map[string]any{"plain_text":"How To"}}},
  "Number":map[string]any{"type":"rich_text","rich_text":[]any{map[string]any{"plain_text":"1.10 Entrata"}}},
  "Manual":map[string]any{"type":"select","select":map[string]any{"name":"Resource and Forms Library"}},
  "Deep Link":map[string]any{"type":"url","url":"https://example.test/path"},
  "Keywords":map[string]any{"type":"multi_select","multi_select":[]any{map[string]any{"name":"Leasing"},map[string]any{"name":"How To"}}},
 }}}
 got:=Normalize(pages)
 if len(got)!=1 {t.Fatalf("length %d",len(got))}
 if got[0].Title!="Entrata – How To" || got[0].Number!="1.10 Entrata" || len(got[0].Keywords)!=2 || got[0].NotionPageID!="page-1" {t.Fatalf("unexpected policy: %+v",got[0])}
}

func TestArchivedPagesOmitted(t *testing.T){
 got:=Normalize([]map[string]any{{"archived":true},{"in_trash":true}})
 if len(got)!=0 {t.Fatal(got)}
}
