"""Self-contained, scope-isolated Interact HTML fragment and local preview."""
from collections import Counter
from html import escape


STYLE = """
.policies-page{--policies-navy:#123c55;--policies-edge:#dce4e8;--policies-ink:#22323b;--policies-muted:#5c717d;--policies-bg:#f6f8f9;color:var(--policies-ink);font:15px system-ui,-apple-system,Segoe UI,sans-serif;box-sizing:border-box;padding:28px 18px;background:var(--policies-bg);width:100%}
.policies-page *{box-sizing:border-box}
.policies-page .policies-inner{max-width:1100px;margin:auto}
.policies-page h1{font-size:30px;letter-spacing:-.025em;margin:0 0 6px}
.policies-page .policies-intro{color:var(--policies-muted);margin:0}
.policies-page .policies-filters{display:flex;flex-wrap:wrap;gap:12px;margin:24px 0 16px}
.policies-page .policies-input,.policies-page .policies-select{font:inherit;color:var(--policies-ink);border:1px solid var(--policies-edge);border-radius:8px;background:white;padding:12px 14px;min-width:210px}
.policies-page .policies-input{flex:2}.policies-page .policies-select{flex:1}
.policies-page .policies-count{color:var(--policies-muted);font-size:13px;margin-bottom:12px}
.policies-page .policies-list{border:1px solid var(--policies-edge);background:white;border-radius:12px;overflow:hidden}
.policies-page .policies-record{padding:17px 20px;display:flex;align-items:center;justify-content:space-between;gap:22px;border-bottom:1px solid var(--policies-edge)}
.policies-page .policies-record:last-child{border-bottom:0}
.policies-page .policies-name{font-weight:650;margin-bottom:7px}
.policies-page .policies-meta{font-size:12px;color:var(--policies-muted);display:flex;gap:8px;flex-wrap:wrap}
.policies-page .policies-record a{color:var(--policies-navy);font-size:13px;font-weight:650;white-space:nowrap;text-decoration:none}
.policies-page .policies-record a:hover{text-decoration:underline}
.policies-page .policies-record a:focus-visible{outline:2px solid var(--policies-navy);outline-offset:4px}
.policies-page .policies-hidden{display:none!important}
.policies-page .policies-empty{padding:26px;color:var(--policies-muted)}
@media(max-width:550px){.policies-page{padding:20px 12px}.policies-page .policies-record{align-items:flex-start;flex-direction:column;gap:8px}.policies-page .policies-input,.policies-page .policies-select{width:100%}}
"""

SCRIPT = """
(function(){
  function init(root){
    if(root.dataset.policiesInitialized==='true')return;
    root.dataset.policiesInitialized='true';
    const search=root.querySelector('[data-policies-search]');
    const manual=root.querySelector('[data-policies-manual]');
    const records=Array.from(root.querySelectorAll('[data-policy-record]'));
    const count=root.querySelector('[data-policies-count]');
    const empty=root.querySelector('[data-policies-empty]');
    if(!search||!manual||!count||!empty)return;
    function filter(){
      const term=search.value.trim().toLocaleLowerCase();
      const selected=manual.value;
      let visible=0;
      for(const record of records){
        const show=(!selected||record.dataset.manual===selected)&&record.dataset.search.includes(term);
        record.classList.toggle('policies-hidden',!show);
        if(show)visible++;
      }
      count.textContent=visible+' of '+records.length+' policies';
      empty.classList.toggle('policies-hidden',visible!==0);
    }
    search.addEventListener('input',filter);
    manual.addEventListener('change',filter);
    filter();
  }
  document.querySelectorAll('[data-policies-page="true"]').forEach(init);
})();
"""


def render_directory(policies):
    """Return an Interact-compatible fragment without html/head/body or global CSS."""
    if not policies:
        raise ValueError("Refusing to render an empty policy directory")
    policies = sorted(policies, key=lambda p: (
        p.manual.casefold(), p.number.casefold(), p.title.casefold()
    ))
    counts = Counter(p.manual for p in policies)
    options = "\n".join(
        '<option value="' + escape(manual, quote=True) + '">' +
        escape(manual) + ' (' + str(count) + ')</option>'
        for manual, count in sorted(counts.items())
    )
    cards = []
    for p in policies:
        search_text = " ".join([p.title, p.number, p.manual, *p.keywords]).casefold()
        cards.append(
            '<article class="policies-record" data-policy-record="true" data-manual="' +
            escape(p.manual, quote=True) + '" data-search="' +
            escape(search_text, quote=True) + '">' +
            '<div class="policies-record-main"><div class="policies-name">' +
            escape(p.title) + '</div><div class="policies-meta"><span>' +
            escape(p.number) + '</span><span>·</span><span>' +
            escape(p.manual) + '</span></div></div><a href="' +
            escape(p.deep_link, quote=True) +
            '" target="_blank" rel="noopener noreferrer" aria-label="Open ' +
            escape(p.title, quote=True) + ' in Grace Hill">Open policy ↗</a></article>'
        )
    return (
        '<div class="policies-page" data-policies-page="true">'
        '<style>' + STYLE + '</style>'
        '<div class="policies-inner"><header><h1>Policy Library</h1>'
        '<p class="policies-intro">Browse Birchstone policies and procedures. '
        'Documents open in Grace Hill.</p></header>'
        '<div class="policies-filters"><input class="policies-input" '
        'data-policies-search type="search" placeholder="Search titles, numbers, or keywords" '
        'aria-label="Search policies"><select class="policies-select" '
        'data-policies-manual aria-label="Filter by manual"><option value="">'
        'All manuals</option>' + options + '</select></div>'
        '<div class="policies-count" data-policies-count aria-live="polite"></div>'
        '<section class="policies-list">' + "\n".join(cards) +
        '<p class="policies-empty policies-hidden" data-policies-empty>'
        'No policies match your search.</p></section></div>'
        '<script>' + SCRIPT + '</script></div>'
    )


def render_preview_document(fragment):
    """Wrap the exact publish fragment for local browser review."""
    return (
        '<!doctype html><html lang="en"><head><meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width, initial-scale=1">'
        '<title>Birchstone Policy Library Preview</title></head><body>' +
        fragment + '</body></html>'
    )
