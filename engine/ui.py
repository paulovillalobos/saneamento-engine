"""The técnico's screens (D21), plain HTML + JS over verdict.json, no framework. Two pages:

    inbox(rows)                  the expedientes as an inbox: state, assignee, counters; one click to take or close one
    app(pdf_base, back="/expedientes")   the three-pane object view of one expediente: rail (identity, sections) · content (Elementos /
                                 Factos / Convite / Ficheiros) · document pane (the PDF opened at the quoted page); a drawer for
                                 «não avaliado», «para revisão», «não lido». Reads verdict.json and convite.md next to the page.

Layout after Palantir's "full object view, high density" (build.palantir.com): identity rail left, tabbed content middle, document
preview right, secondary context in a drawer. Type: weight 500 minimum, no grey text (DESIGN_SYSTEM). Portuguese.
"""
import html
import json

CSS = """
:root{--ink:#111;--bg:#f6f6f4;--line:#d6d6d2;--panel:#fff;--bad:#a40000;--bad-bg:#fbe9e7;--good:#0a6b2d;--good-bg:#e6f4ea;--warn:#8a5a00;--warn-bg:#fff4d6;--accent:#2b4acb;--dark:#15171c}
*{box-sizing:border-box}body{margin:0;font:500 14px/1.45 "IBM Plex Sans",system-ui,sans-serif;color:var(--ink);background:var(--bg)}
a{color:var(--accent)}button{font:inherit;font-weight:600;padding:6px 12px;border:1px solid var(--line);background:#fff;border-radius:6px;cursor:pointer}
button.primary{background:var(--dark);color:#fff;border-color:var(--dark)}button.small{padding:3px 8px;font-size:12px}
.strip{background:var(--dark);color:#fff;padding:14px 20px;display:flex;gap:28px;align-items:flex-end;flex-wrap:wrap}
.strip h1{margin:0;font-size:20px;font-weight:700}.strip .k{font-size:11px;letter-spacing:.06em;text-transform:uppercase;font-weight:600;color:#fff;opacity:.85}
.strip .v{font-size:15px;font-weight:600}.strip .count{font-size:22px;font-weight:700}.strip .count.bad{color:#ff8a80}.strip .count.good{color:#8ce0a6}
.layout{display:grid;grid-template-columns:240px minmax(420px,1fr) minmax(380px,46%);height:calc(100vh - 78px)}
.rail{border-right:1px solid var(--line);background:var(--panel);padding:14px;overflow:auto}.rail h2{font-size:12px;letter-spacing:.06em;text-transform:uppercase;margin:14px 0 6px}
.rail .nav a{display:block;padding:7px 10px;border-radius:6px;color:var(--ink);text-decoration:none;font-weight:600}.rail .nav a.on{background:#e8ecfb;color:var(--accent)}
.rail dl{margin:0}.rail dt{font-size:11px;text-transform:uppercase;letter-spacing:.05em;margin-top:8px}.rail dd{margin:0;font-weight:600}
.content{overflow:auto;padding:0 18px 18px}.tabs{position:sticky;top:0;background:var(--bg);padding:12px 0 8px;display:flex;gap:6px;border-bottom:1px solid var(--line);margin-bottom:10px}
.tabs button.on{background:var(--dark);color:#fff;border-color:var(--dark)}
table{border-collapse:collapse;width:100%;background:var(--panel)}th,td{border-bottom:1px solid var(--line);padding:6px 8px;text-align:left;vertical-align:top}th{font-size:12px;text-transform:uppercase;letter-spacing:.04em}
tr.row{cursor:pointer}tr.row:hover{background:#eef1fb}tr.sel{outline:2px solid var(--accent);outline-offset:-2px}
.pill{display:inline-block;padding:1px 8px;border-radius:999px;font-size:12px;font-weight:700}.pill.bad{background:var(--bad-bg);color:var(--bad)}.pill.good{background:var(--good-bg);color:var(--good)}.pill.warn{background:var(--warn-bg);color:var(--warn)}.pill.off{background:#e9e9e6;color:var(--ink)}
.doc{border-left:1px solid var(--line);background:#2a2d33;display:flex;flex-direction:column}.doc .bar{padding:8px 12px;color:#fff;font-weight:600;display:flex;justify-content:space-between;align-items:center;gap:8px}
.doc iframe{flex:1;border:0;background:#fff}.doc .empty{flex:1;display:flex;align-items:center;justify-content:center;color:#fff;font-weight:600}
q{quotes:"«" "»"}.quote{font-weight:500;background:#fffbe6;border-left:3px solid var(--warn);padding:4px 8px;margin:4px 0;font-family:"IBM Plex Mono",ui-monospace,monospace;font-size:12.5px}
.law{font-size:12.5px;margin-top:4px}details.law summary{cursor:pointer;font-weight:600}details.law q{display:block;margin-top:4px}.drawer{border-top:1px solid var(--line);margin-top:18px;padding-top:10px}.drawer h3{font-size:13px;text-transform:uppercase;letter-spacing:.05em;margin:12px 0 6px}
textarea{width:100%;min-height:60vh;font:500 13px/1.5 "IBM Plex Mono",ui-monospace,monospace;padding:10px;border:1px solid var(--line);border-radius:6px}
.inbox{max-width:1200px;margin:0 auto;padding:18px}.card{background:var(--panel);border:1px solid var(--line);border-radius:8px;padding:12px 14px;margin:10px 0;display:grid;grid-template-columns:1fr auto;gap:8px;align-items:center}
.card .t{font-size:16px;font-weight:700}.card .m{font-weight:500}.card .acts{display:flex;gap:6px;align-items:center;flex-wrap:wrap}.state{font-size:12px;font-weight:700;padding:2px 8px;border-radius:999px;background:#e9e9e6}
.state.novo{background:#e8ecfb;color:var(--accent)}.state.em_analise{background:var(--warn-bg);color:var(--warn)}.state.convite_enviado{background:var(--bad-bg);color:var(--bad)}.state.saneado{background:var(--good-bg);color:var(--good)}
@media(max-width:1100px){.layout{grid-template-columns:200px 1fr;grid-template-rows:1fr 46vh;height:auto}.doc{grid-column:1/3;border-left:0;border-top:1px solid var(--line);min-height:46vh}}
"""

STATES = [("novo", "Novo"), ("em_analise", "Em análise"), ("convite_enviado", "Convite enviado"), ("saneado", "Saneado")]


def inbox(rows, municipality):
    esc = html.escape
    cards = []
    for r in rows:
        c = r.get("counts") or {}
        st = r.get("estado") or ("novo" if r.get("files") else "")
        label = dict(STATES).get(st, st)
        pend = not r.get("files")
        cards.append(f"""<div class="card" data-id="{esc(r['id'])}">
  <div><div class="t"><a href="/expedientes/{esc(r['id'])}/">{esc(r['label'])}</a> <span class="state {esc(st)}">{esc(label)}</span></div>
    <div class="m">{esc((r.get('at') or '')[:16].replace('T', ' '))} UTC · {r.get('files', 0)} ficheiros · leitor {esc(r.get('reader') or '—')}{(' · ' + str(r.get('seconds')) + ' s') if r.get('seconds') else ''}
    {'' if pend else f" · <span class='pill {'bad' if c.get('finding') else 'good'}'>{c.get('finding', 0)} deficiência(s)</span> <span class='pill warn'>{c.get('not_assessed', 0)} não avaliado</span> <span class='pill off'>{c.get('review', 0)} revisão · {c.get('not_read', 0)} não lido</span>"}
    {('· responsável <b>' + esc(r['responsavel']) + '</b>') if r.get('responsavel') else ''}</div></div>
  <div class="acts">{'' if pend else ''.join(f'<button class="small" onclick="setState(this, {json.dumps(r["id"])}, {json.dumps(k)})">{esc(v)}</button>' for k, v in STATES if k != st)}
    {'' if pend else f'<button class="small" onclick="assign(this, {json.dumps(r["id"])})">assumir</button>'}</div></div>""")
    return f"""<!doctype html><html lang="pt"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Expedientes · {esc(municipality)}</title><style>{CSS}</style></head><body>
<div class="strip"><div><h1>Expedientes · {esc(municipality)}</h1><div class="k">comunicação prévia de obras de edificação · Portaria 320/2026/1</div></div>
<div><div class="k">total</div><div class="count">{len(rows)}</div></div>
<div><div class="k">com deficiências</div><div class="count bad">{sum(1 for r in rows if (r.get('counts') or {}).get('finding'))}</div></div>
<div><div class="k">limpos</div><div class="count good">{sum(1 for r in rows if r.get('files') and not (r.get('counts') or {}).get('finding'))}</div></div>
<div style="margin-left:auto"><a href="/" style="color:#fff">+ novo expediente</a></div></div>
<div class="inbox">{''.join(cards) or '<p>Nenhum expediente ainda. <a href="/">Verificar o primeiro.</a></p>'}
<p><small>O leitor lê, o código decide, o técnico assina. Estados: novo → em análise → convite enviado → saneado.</small></p></div>
<script>
async function setState(b,id,st){{b.disabled=true;const r=await fetch('/v1/expedientes/'+id+'/trabalho',{{method:'POST',headers:{{'Content-Type':'application/json'}},body:JSON.stringify({{estado:st}})}});if(r.ok)location.reload();else{{b.disabled=false;alert('erro '+r.status)}}}}
async function assign(b,id){{const n=prompt('Nome do técnico responsável');if(!n)return;b.disabled=true;const r=await fetch('/v1/expedientes/'+id+'/trabalho',{{method:'POST',headers:{{'Content-Type':'application/json'}},body:JSON.stringify({{responsavel:n,estado:'em_analise'}})}});if(r.ok)location.reload();else{{b.disabled=false;alert('erro '+r.status)}}}}
</script></body></html>"""


def app(pdf_base="ficheiros/", back="/expedientes", inline=None):
    """inline: {"verdict": dict, "convite": str} embeds the data (a preview opened from a file, no server)."""
    data = f"const INLINE={json.dumps(inline, ensure_ascii=False)};" if inline else "const INLINE=null;"
    return f"""<!doctype html><html lang="pt"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Expediente</title><style>{CSS}</style></head><body>
<div class="strip" id="strip"><div><h1 id="h1">a carregar…</h1><div class="k" id="sub"></div></div></div>
<div class="layout">
  <nav class="rail"><a href="{html.escape(back)}">← expedientes</a><h2>Expediente</h2><dl id="ident"></dl><h2>Secções</h2><div class="nav" id="nav"></div><h2>Ações</h2><div><button class="primary" onclick="show('convite')">Convite</button> <button onclick="window.open('verdict.json')">JSON</button></div>
  <div id="meta" style="margin-top:14px;font-size:12px"></div></nav>
  <main class="content"><div class="tabs" id="tabs"></div><div id="pane"></div><div class="drawer" id="drawer"></div></main>
  <aside class="doc"><div class="bar"><span id="docname">documento</span><span><button class="small" id="openpdf" style="display:none" onclick="window.open(cur.src)">abrir</button></span></div><div class="empty" id="docempty">Clique numa deficiência ou num ficheiro para ver a página citada.</div><iframe id="pdf" style="display:none"></iframe></aside>
</div>
<script>
{data}
const PDF="{html.escape(pdf_base)}";const $=s=>document.querySelector(s);let V=null,CONV="",tab="elementos",cur={{}};
const TYPES={{missing_required:"Elemento em falta",missing_complement:"Complemento em falta",not_pdf:"Não é PDF",not_pdfa:"Sem PDF/A",unsigned:"Sem assinatura",template_wording_missing:"Sem redação do Anexo VII",value_mismatch:"Valores divergentes",impossible_value:"Valor impossível",wrong_site:"Local divergente",expired_insurance:"Seguro caducado",wrong_signer:"Assinatura de outra pessoa"}};
const STATE={{present:["sim","good"],missing:["FALTA","bad"],not_assessed:["não avaliado","warn"],satisfied_by:["sim, via outro","good"],optional:["facultativo","off"],not_required_here:["n/a","off"]}};
const esc=s=>String(s??"").replace(/[&<>"]/g,c=>({{"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;"}}[c]));
function showPdf(file,page,label){{if(!file)return;cur={{src:PDF+encodeURIComponent(file)+(page?("#page="+page):"")}};$("#pdf").src=cur.src;$("#pdf").style.display="block";$("#docempty").style.display="none";$("#docname").textContent=(label||file)+(page?(" · p."+page):"");$("#openpdf").style.display="inline-block";document.querySelectorAll("tr.sel").forEach(e=>e.classList.remove("sel"))}}
function pill(st){{const [t,c]=STATE[st]||[st,"off"];return `<span class="pill ${{c}}">${{esc(t)}}</span>`}}
function law(f){{return f.law?`<details class="law" onclick="event.stopPropagation()"><summary>Anexo <b>${{esc(f.law.ref)}}</b> · ver texto da lei</summary><q>${{esc(f.law.quote)}}</q></details>`:""}}
function evid(f){{return (f.evidence||[]).map(e=>`<div class="quote" onclick="event.stopPropagation();showPdf(${{JSON.stringify(e.file)}},${{e.page||1}})">${{esc(e.file)}} p.${{esc(e.page)}}: ${{esc(e.quote)}}</div>`).join("")}}
function findingsTable(list){{if(!list.length)return "<p><b>Sem deficiências.</b></p>";return `<table><tr><th>#</th><th>Deficiência</th><th>Onde</th><th>Evidência e lei</th></tr>`+list.map((f,i)=>`<tr class="row" onclick="showPdf(${{JSON.stringify(f.file||'')}},${{(f.evidence&&f.evidence[0]&&f.evidence[0].page)||1}});this.classList.add('sel')"><td>${{i+1}}</td><td><span class="pill bad">${{esc(TYPES[f.type]||f.type)}}</span><div>${{esc(f.detail||"")}}</div></td><td>${{esc(f.slot||"")}}<br>${{esc(f.file||f.rule||"")}}</td><td>${{evid(f)}}${{law(f)}}</td></tr>`).join("")+"</table>"}}
function elementos(){{const byEl={{}};V.findings.forEach(f=>{{if(f.rule)(byEl[f.rule]=byEl[f.rule]||[]).push(f)}});const fileOf=n=>V.files.find(x=>x.file===n);
 return `<h3>Deficiências (${{V.findings.length}}) — vão no convite</h3>`+findingsTable(V.findings)+`<h3 style="margin-top:18px">Elementos do Anexo V (${{V.elements.length}})</h3><table><tr><th>Elemento</th><th>Campos</th><th>Estado</th><th>Ficheiros</th></tr>`+V.elements.map(e=>`<tr class="row ${{e.state==='missing'?'':''}}" onclick="showPdf(${{JSON.stringify(e.files[0]||'')}},1);this.classList.add('sel')"><td><b>${{esc(e.element)}}</b>${{(byEl[e.element]||[]).map(f=>'<div class="law">'+esc(f.detail||'')+'</div>').join('')}}</td><td>${{esc(e.slots.join(", "))}}</td><td>${{pill(e.state)}}</td><td>${{e.files.map(n=>`<a href="#" onclick="event.preventDefault();event.stopPropagation();showPdf(${{JSON.stringify(n)}},1)">${{esc(n)}}</a>`).join("<br>")}}</td></tr>`).join("")+"</table>"}}
function factos(){{const F=V.facts||{{}};const keys=Object.keys(F);const fx=V.findings.filter(f=>["value_mismatch","impossible_value","expired_insurance"].includes(f.type));
 return `<h3>Factos divergentes (${{fx.length}})</h3>`+findingsTable(fx)+`<h3 style="margin-top:18px">Factos lidos (${{keys.reduce((n,k)=>n+F[k].length,0)}})</h3><table><tr><th>Facto</th><th>Valor</th><th>Ficheiro · página</th><th>Citação</th></tr>`+keys.map(k=>F[k].map(v=>`<tr class="row" onclick="showPdf(${{JSON.stringify(v.file)}},${{v.page||1}});this.classList.add('sel')"><td><b>${{esc(k)}}</b></td><td>${{esc(v.value)}}</td><td>${{esc(v.slot)}} · ${{esc(v.file)}} p.${{esc(v.page)}}</td><td class="quote">${{esc(v.quote)}}</td></tr>`).join("")).join("")+"</table>"}}
function convite(){{return `<h3>Convite ao aperfeiçoamento — rascunho</h3><p>Editável. O técnico corrige, copia para o ofício da câmara e assina. <button class="small" onclick="navigator.clipboard.writeText($('#conv').value)">copiar</button> <a href="convite.md" download>descarregar .md</a></p><textarea id="conv">${{esc(CONV)}}</textarea>`}}
function ficheiros(){{return `<h3>Ficheiros (${{V.files.length}})</h3><table><tr><th>Ficheiro</th><th>Campo</th><th>PDF</th><th>PDF/A</th><th>Assinado</th><th>Páginas</th><th>Elemento lido</th></tr>`+V.files.map(f=>{{const ok=(V.elements_ok||[]).find(x=>x.file===f.file);const rv=(V.review||[]).find(x=>x.file===f.file);return `<tr class="row" onclick="showPdf(${{JSON.stringify(f.file)}},1);this.classList.add('sel')"><td>${{esc(f.file)}}</td><td>${{esc(f.slot||f.slot_raw||"")}}</td><td>${{f.is_pdf?"sim":'<span class="pill bad">não</span>'}}</td><td>${{f.pdfa?"sim":(f.is_pdf?'<span class="pill bad">não</span>':"")}}</td><td>${{f.signed?("sim"+(f.signer?" · "+esc(f.signer.cn):"")):(f.is_pdf?'<span class="pill warn">não</span>':"")}}</td><td>${{f.n||""}}</td><td>${{ok?esc(ok.element):(rv?'<span class="pill warn">revisão: '+esc(rv.element||"não é elemento")+'</span>':"")}}</td></tr>`}}).join("")+"</table>"}}
function drawer(){{const na=V.not_assessed||[],rv=V.review||[],nr=V.not_read||[],ab=V.absent||[];return `<h3>Não avaliado (${{na.length}}) — depende de factos fora do expediente</h3><ul>${{na.map(i=>`<li><b>${{esc(i.rule||i.type)}}</b>${{i.slot?" · "+esc(i.slot):""}} — ${{esc(i.condition||"")}}</li>`).join("")||"<li>nenhum</li>"}}</ul>
 <h3>Para revisão do técnico (${{rv.length}})</h3><ul>${{rv.map(i=>`<li><a href="#" onclick="event.preventDefault();showPdf(${{JSON.stringify(i.file)}},1)">${{esc(i.file)}}</a> — ${{esc(i.detail)}}${{i.element?" ("+esc(i.element)+")":""}}</li>`).join("")||"<li>nenhum</li>"}}</ul>
 <h3>Não lido (${{nr.length}}) · sem valor no documento (${{ab.length}})</h3><ul>${{nr.map(i=>`<li>${{esc(i.file)}} · ${{esc(i.field||i.type)}} — ${{esc(i.detail)}}</li>`).join("")||"<li>nenhum</li>"}}</ul>`}}
function show(t){{tab=t;document.querySelectorAll("#tabs button").forEach(b=>b.classList.toggle("on",b.dataset.t===t));document.querySelectorAll("#nav a").forEach(a=>a.classList.toggle("on",a.dataset.t===t));$("#pane").innerHTML=({{elementos,factos,convite,ficheiros}})[t]()}}
async function load(){{if(INLINE){{V=INLINE.verdict;CONV=INLINE.convite}}else{{V=await (await fetch("verdict.json")).json();try{{CONV=await (await fetch("convite.md")).text()}}catch(e){{CONV="(convite indisponível)"}}}}
 const c=V.counts||{{}};$("#h1").textContent=(V.label||V.expediente||"Expediente");$("#sub").textContent=(V.operation||"")+" · "+(V.procedure||"")+" · lei "+(V.law||"");
 $("#strip").insertAdjacentHTML("beforeend",`<div><div class="k">deficiências</div><div class="count ${{c.finding?"bad":"good"}}">${{c.finding||0}}</div></div><div><div class="k">não avaliado</div><div class="count">${{c.not_assessed||0}}</div></div><div><div class="k">revisão</div><div class="count">${{c.review||0}}</div></div><div><div class="k">não lido</div><div class="count">${{c.not_read||0}}</div></div><div><div class="k">elementos confirmados</div><div class="count good">${{c.ok||0}}</div></div><div><div class="k">leitor</div><div class="v">${{esc((V.reader&&V.reader.adapter)||"sem leituras")}}</div></div>`);
 $("#ident").innerHTML=[["expediente",V.expediente],["requerente",V.applicant],["operação",V.operation],["verificado",(V.checked_at||"").slice(0,16).replace("T"," ")+" UTC"],["ficheiros",V.files.length]].map(([k,v])=>`<dt>${{k}}</dt><dd>${{esc(v||"—")}}</dd>`).join("");
 const tabs=[["elementos","Elementos"],["factos","Factos"],["convite","Convite"],["ficheiros","Ficheiros"]];$("#tabs").innerHTML=tabs.map(([t,l])=>`<button data-t="${{t}}" onclick="show('${{t}}')">${{l}}</button>`).join("");$("#nav").innerHTML=tabs.map(([t,l])=>`<a href="#" data-t="${{t}}" onclick="event.preventDefault();show('${{t}}')">${{l}}</a>`).join("");
 $("#meta").innerHTML=`<b>O leitor lê, o código decide, o técnico assina.</b><br>${{V.seconds?V.seconds+" s":""}}`;$("#drawer").innerHTML=drawer();show("elementos");
 const first=V.findings.find(f=>f.file);if(first)showPdf(first.file,(first.evidence&&first.evidence[0]&&first.evidence[0].page)||1)}}
load();
</script></body></html>"""
