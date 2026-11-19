"""Self-contained, scope-isolated Interact HTML fragment and local preview."""
from collections import Counter
from html import escape


STYLE = """
@import url('https://fonts.googleapis.com/css2?family=Montserrat:wght@400;500;600;700;800&display=swap');
/* Design tokens and 1440px runtime viewport adapted from Property Details. */
.policies-page{
 --policies-bg:#f4f6f8;--policies-surface:#ffffff;--policies-soft:#f8fafb;
 --policies-ink:#17212b;--policies-muted:#66717c;--policies-edge:#dfe5ea;
 --policies-edge-strong:#cbd4dc;--policies-accent:#1f5f5b;
 --policies-accent-strong:#174945;--policies-accent-soft:#e9f2f1;
 --policies-shadow:0 18px 45px rgba(28,42,53,.08);
 --policies-max-width:1440px;
 width:min(calc(100% - 32px),var(--policies-max-width));
 max-width:none;margin:32px 0 64px;padding:28px;
 color:var(--policies-ink);font:15px 'Montserrat',Arial,sans-serif;
 background:var(--policies-bg);border-radius:20px;box-sizing:border-box;
}
.policies-page,.policies-page *{box-sizing:border-box}
.policies-page .policies-inner{width:100%;max-width:none;min-width:0;margin:0 auto}
.policies-page h1{font-size:clamp(1.7rem,3vw,2.4rem);letter-spacing:-.025em;line-height:1.1;margin:0 0 10px;color:var(--policies-ink);font-weight:800}
.policies-page .policies-intro{color:var(--policies-muted);line-height:1.55;margin:0}
.policies-page .policies-filters{display:flex;flex-wrap:wrap;gap:12px;margin:24px 0 16px}
.policies-page .policies-input,.policies-page .policies-select{
 font:inherit;font-size:.9rem;color:var(--policies-ink);
 border:1px solid var(--policies-edge-strong);border-radius:10px;
 background:var(--policies-surface);padding:12px 14px;min-height:48px;min-width:210px;
}
.policies-page .policies-input{flex:2}.policies-page .policies-select{flex:1}
.policies-page .policies-input:focus,.policies-page .policies-select:focus{outline:none;border-color:var(--policies-accent);box-shadow:0 0 0 4px rgba(31,95,91,.12)}
.policies-page .policies-count{color:var(--policies-muted);font-size:.82rem;font-weight:600;margin-bottom:12px}
.policies-page .policies-list{border:1px solid var(--policies-edge);background:var(--policies-surface);border-radius:14px;overflow:hidden;box-shadow:0 8px 26px rgba(28,42,53,.04)}
.policies-page .policies-record{padding:18px 20px;display:flex;align-items:center;justify-content:space-between;gap:22px;border-bottom:1px solid var(--policies-edge);transition:background 150ms ease}
.policies-page .policies-record:hover{background:var(--policies-soft)}
.policies-page .policies-record:last-child{border-bottom:0}
.policies-page .policies-name{font-weight:750;margin-bottom:7px}
.policies-page .policies-meta{font-size:.78rem;color:var(--policies-muted);display:flex;gap:8px;flex-wrap:wrap}
.policies-page .policies-record a{color:var(--policies-accent-strong);font-size:.82rem;font-weight:750;white-space:nowrap;text-decoration:none}
.policies-page .policies-record a:hover{color:var(--policies-accent);text-decoration:underline}
.policies-page .policies-record a:focus-visible{outline:3px solid #72a9a4;outline-offset:4px}
.policies-page .policies-hidden{display:none!important}
.policies-page .policies-empty{padding:26px;color:var(--policies-muted)}

/* Dark navy/cyan presentation reused from the final Property Details overrides.
   The existing Policies search/list hierarchy remains unchanged. */
.policies-page{
 --policies-bg:#0a1929;--policies-surface:#102c43;--policies-soft:rgba(255,255,255,.05);
 --policies-ink:#ffffff;--policies-muted:#b6c7d6;
 --policies-edge:rgba(44,177,204,.3);--policies-edge-strong:rgba(44,177,204,.4);
 --policies-accent:#2cb1cc;--policies-accent-strong:#59d0e4;
 --policies-accent-soft:rgba(44,177,204,.15);
 --policies-shadow:0 16px 36px rgba(0,0,0,.18);
 background:linear-gradient(135deg,#0a1929 0%,#1a365d 50%,#0a1929 100%);
 color:var(--policies-ink);
}
.policies-page,.policies-page :is(h1,p,div,span,a,input,select,option,article){
 font-family:'Montserrat',Arial,sans-serif;
}
.policies-page h1{color:var(--policies-accent);font-weight:800}
.policies-page .policies-intro{color:rgba(255,255,255,.9)}
.policies-page .policies-input,.policies-page .policies-select{
 border:1px solid var(--policies-edge);border-radius:8px;
 background:rgba(12,41,60,.85);color:#fff;color-scheme:dark;
}
.policies-page .policies-input::placeholder{color:#b6c7d6;opacity:.85}
.policies-page .policies-input:focus,.policies-page .policies-select:focus{
 border-color:var(--policies-accent);outline:2px solid rgba(44,177,204,.6);outline-offset:2px;box-shadow:none;
}
.policies-page .policies-list{
 border-color:var(--policies-edge);
 background:linear-gradient(135deg,rgba(0,63,95,.7),rgba(12,41,60,.8));
 box-shadow:var(--policies-shadow);
}
.policies-page .policies-record{border-bottom-color:rgba(44,177,204,.2)}
.policies-page .policies-record:hover{background:rgba(44,177,204,.1)}
.policies-page .policies-name{color:#fff}
.policies-page .policies-meta,.policies-page .policies-count,.policies-page .policies-empty{color:var(--policies-muted)}
.policies-page .policies-record a{color:var(--policies-accent-strong)}
.policies-page .policies-record a:hover{color:#fff}
.policies-page .policies-record a:focus-visible{outline-color:var(--policies-accent)}

@media(max-width:640px){
 .policies-page{width:min(calc(100% - 20px),var(--policies-max-width));margin:10px 0 30px;padding:20px 14px;border-radius:14px}
 .policies-page .policies-record{align-items:flex-start;flex-direction:column;gap:8px}
 .policies-page .policies-input,.policies-page .policies-select{width:100%;min-width:0}
}
"""

SCRIPT = """
(function(){
  /* Based on birchstone-interact-customization's Property Details Interact helpers.
     Only run page-chrome adjustments on the Policies document page, ID 2194. */
  function isPoliciesDocumentPage(){
    return /\\/Interact\\/Pages\\/Content\\/Document\\.aspx$/i.test(window.location.pathname) &&
      new URLSearchParams(window.location.search).get('id')==='2194';
  }

  function hideNativePreviewMessage(root){
    if(!isPoliciesDocumentPage())return;
    const previewButton=document.getElementById('body_btnBEPreview');
    if(!previewButton)return;
    const heading=[...document.querySelectorAll('b, strong')].find(
      el=>(el.textContent||'').trim()==='Would you like an improved page viewing experience?'
    );
    if(!heading)return;
    let container=previewButton.parentElement;
    for(let depth=0;container&&depth<5;depth++,container=container.parentElement){
      if(!container.contains(heading))continue;
      if(container!==document.body&&container!==document.documentElement&&
         !container.contains(root)&&container.querySelectorAll('button, a').length<=2){
        container.style.setProperty('display','none','important');
      }
      break;
    }
  }

  function closePageDetailsPane(){
    const direct=[...document.querySelectorAll(
      '[title*="Hide page details" i], [aria-label*="Hide page details" i], [data-original-title*="Hide page details" i]'
    )].filter(el=>el.getBoundingClientRect().width>0);
    if(direct.length){direct[0].click();return true;}
    const heading=[...document.querySelectorAll('body *')].find(
      el=>!el.children.length&&(el.textContent||'').trim().toLowerCase()==='details'
    );
    if(!heading)return false;
    const rect=heading.getBoundingClientRect();
    const candidates=[...document.querySelectorAll('button, a, [role="button"]')].filter(el=>{
      const b=el.getBoundingClientRect();
      return b.width>0&&b.height>0&&b.top>=55&&b.top<=190&&
        b.left>=rect.left&&b.width<=80&&b.height<=80;
    });
    if(!candidates.length)return false;
    candidates.sort((a,b)=>b.getBoundingClientRect().left-a.getBoundingClientRect().left);
    candidates[0].click();return true;
  }

  function hideDetailsPaneFallback(root){
    /* Interact versions without an accessible pane-toggle label may not expose
       a clickable close control. Hide only the independently identified
       right-hand Details section, never the document/article or our app. */
    const headings=[...document.querySelectorAll('body *')].filter(el=>
      el.children.length===0&&['details','keywords & topics','interact recommends']
        .includes((el.textContent||'').trim().toLowerCase())
    );
    const heading=headings.find(el=>(el.textContent||'').trim().toLowerCase()==='details');
    const keyword=headings.find(el=>(el.textContent||'').trim().toLowerCase()==='keywords & topics');
    if(!heading||!keyword)return false;
    let pane=keyword.parentElement;
    while(pane&&pane!==document.body&&pane!==document.documentElement){
      if(pane.contains(heading))break;
      pane=pane.parentElement;
    }
    if(!pane||pane===document.body||pane===document.documentElement||pane.contains(root))return false;
    const bounds=pane.getBoundingClientRect();
    if(bounds.width<140||bounds.width>480||bounds.height<80)return false;
    pane.style.setProperty('display','none','important');
    return true;
  }

  function expandPolicies(root){
    if(!isPoliciesDocumentPage())return;
    /* Identical 1440px sizing and centering algorithm to Property Details. */
    const relaxAncestorClipping=()=>{
      let node=root.parentElement,depth=0;
      while(node&&node!==document.body&&depth<16){
        node.style.setProperty('overflow','visible','important');
        node.style.setProperty('overflow-x','visible','important');
        node.style.setProperty('overflow-y','visible','important');
        node.style.setProperty('max-width','none','important');
        node=node.parentElement;depth++;
      }
    };
    const applyWidth=()=>{
      relaxAncestorClipping();
      root.style.setProperty('margin-left','0px','important');
      const naturalLeft=root.getBoundingClientRect().left;
      const anchor=document.getElementById('document')||root.parentElement;
      const bounds=anchor.getBoundingClientRect();
      const gutter=32;
      const target=Math.min(1440,Math.max(0,window.innerWidth-2*gutter));
      const idealLeft=bounds.left+(bounds.width-target)/2;
      const centeredLeft=Math.max(gutter,Math.min(idealLeft,window.innerWidth-gutter-target));
      root.style.setProperty('width',target+'px','important');
      root.style.setProperty('max-width','none','important');
      root.style.setProperty('margin-left',centeredLeft-naturalLeft+'px','important');
    };
    applyWidth();
    let attempts=0;
    const tryClose=()=>{
      attempts++;
      if(closePageDetailsPane()){window.setTimeout(applyWidth,450);return;}
      if(attempts<20){window.setTimeout(tryClose,250);return;}
      if(hideDetailsPaneFallback(root))window.requestAnimationFrame(applyWidth);
    };
    tryClose();
    window.addEventListener('resize',()=>window.requestAnimationFrame(applyWidth));
    hideNativePreviewMessage(root);
    /* The native Interact preview banner may be inserted after the HTML script executes. */
    if(document.body){
      const observer=new MutationObserver(()=>hideNativePreviewMessage(root));
      observer.observe(document.body,{childList:true,subtree:true});
    }
  }

  function init(root){
    if(root.dataset.policiesInitialized==='true')return;
    root.dataset.policiesInitialized='true';
    expandPolicies(root);
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
