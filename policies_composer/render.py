"""Static searchable directory: sanitized HTML, no credentials or API requests."""
from collections import Counter
from html import escape


STYLE = """
:root{--navy:#123c55;--edge:#dce4e8;--ink:#22323b;--muted:#5c717d;--bg:#f6f8f9}
*{box-sizing:border-box}body{font:15px system-ui,-apple-system,Segoe UI,sans-serif;color:var(--ink);margin:0;background:var(--bg)}
main{max-width:1050px;margin:auto;padding:34px 24px}header{margin-bottom:24px}
h1{font-size:30px;letter-spacing:-.025em;margin:0 0 6px}header p{color:var(--muted);margin:0}
.filters{display:flex;flex-wrap:wrap;gap:12px;margin:24px 0 16px}
input,select{font:inherit;border:1px solid var(--edge);border-radius:8px;background:white;padding:12px 14px;min-width:210px}
input{flex:2}select{flex:1}
#count{color:var(--muted);font-size:13px;margin-bottom:12px}
.list{border:1px solid var(--edge);background:white;border-radius:12px;overflow:hidden}
.policy{padding:17px 20px;display:flex;align-items:center;justify-content:space-between;gap:22px;border-bottom:1px solid var(--edge)}
.policy:last-child{border:0}.policy-name{font-weight:650;margin-bottom:7px}
.policy-meta{font-size:12px;color:var(--muted);display:flex;gap:8px}
.policy a{color:var(--navy);font-size:13px;font-weight:650;white-space:nowrap;text-decoration:none}
.policy a:hover{text-decoration:underline}.policy a:focus-visible{outline:2px solid var(--navy);outline-offset:4px}
.hidden{display:none}.empty{padding:26px;color:var(--muted)}
@media(max-width:550px){main{padding:20px 12px}.policy{align-items:flex-start;flex-direction:column;gap:8px}input,select{width:100%}}
"""

SCRIPT = """
(() => {
  const search = document.querySelector('#search');
  const manual = document.querySelector('#manual');
  const cards = [...document.querySelectorAll('.policy')];
  const count = document.querySelector('#count');
  const empty = document.querySelector('#empty');
  function filter() {
    const term = search.value.trim().toLocaleLowerCase();
    const selected = manual.value;
    let visible = 0;
    for (const card of cards) {
      const show = (!selected || card.dataset.manual === selected) && card.dataset.search.includes(term);
      card.classList.toggle('hidden', !show);
      visible += Number(show);
    }
    count.textContent = visible + ' of ' + cards.length + ' policies';
    empty.classList.toggle('hidden', visible !== 0);
  }
  search.addEventListener('input', filter);
  manual.addEventListener('change', filter);
  filter();
})();
"""


def render_directory(policies):
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
            '<article class="policy" data-manual="' + escape(p.manual, quote=True) +
            '" data-search="' + escape(search_text, quote=True) + '">' +
            '<div class="policy-main"><div class="policy-name">' + escape(p.title) +
            '</div><div class="policy-meta"><span>' + escape(p.number) +
            '</span><span class="dot">·</span><span>' + escape(p.manual) +
            '</span></div></div><a href="' + escape(p.deep_link, quote=True) +
            '" target="_blank" rel="noopener noreferrer" aria-label="Open ' +
            escape(p.title, quote=True) + ' in Grace Hill">Open policy ↗</a></article>'
        )
    return (
        '<!doctype html><html lang="en"><head><meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width, initial-scale=1">'
        '<title>Birchstone Policy Library</title><style>' + STYLE +
        '</style></head><body><main><header><h1>Policy Library</h1>'
        '<p>Browse Birchstone policies and procedures. Documents open in Grace Hill.</p>'
        '</header><div class="filters"><input id="search" type="search"'
        ' placeholder="Search titles, numbers, or keywords" aria-label="Search policies">'
        '<select id="manual" aria-label="Filter by manual"><option value="">'
        'All manuals</option>' + options + '</select></div>'
        '<div id="count" aria-live="polite"></div><section class="list" id="list">' +
        "\n".join(cards) +
        '<p class="empty hidden" id="empty">No policies match your search.</p>'
        '</section></main><script>' + SCRIPT + '</script></body></html>'
    )
