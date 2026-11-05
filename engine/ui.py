"""The técnico's screens (D21, D22), copied from two Palantir Foundry layouts the founder chose (build.palantir.com) and drawn with
Palantir's open-source design system, Blueprint (CSS from a CDN; no framework, no build):

    lei(inline=None)      «Pergunte à lei» — the "Request" layout: header band with an icon tile, title and one-line subtitle; left
                          column = the question card (textarea + one blue button), the answer card, the retrieved-passages card with a
                          pager; right column = the configuration panel (scope, reader on/off, examples).
    app(pdf_base, back)   one expediente — the "full object view, high density" layout: identity rail with icon + name + three sections,
                          tabbed content (Deficiências · Revisão · Elementos · Factos · Ficheiros · Convite), the document preview pane
                          on the right (the PDF at the quoted page).
    inbox(rows, muni)     the expedientes as an inbox: one row per expediente with state, assignee, counters, one-click state.

Content is ours; the air, the cards with one title and one subtitle, the single accent, the grey page are theirs. Type weight 500
minimum, no grey text (DESIGN_SYSTEM): Blueprint's muted text is overridden to full ink.
"""
import html
import json

BP = ('<link rel="stylesheet" href="https://unpkg.com/normalize.css@8.0.1/normalize.css">'
      '<link rel="stylesheet" href="https://unpkg.com/@blueprintjs/core@5.10.5/lib/css/blueprint.css">'
      '<link rel="stylesheet" href="https://unpkg.com/@blueprintjs/icons@5.9.0/lib/css/blueprint-icons.css">'
      '<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Source+Sans+3:wght@500;600;700&display=swap">')

CSS = """
<style>
:root{--ink:#1c2127;--page:#f6f7f9;--line:#d3d8de;--blue:#2d72d2;--blue-bg:#e1ebfa;--purple:#7961db;--purple-bg:#eae6f8;--green:#238551;--red:#cd4246;--red-bg:#fbe9e9;--orange:#c87619;--orange-bg:#fdf1e2}
html,body{height:100%}body{margin:0;background:var(--page);color:var(--ink);font:500 15px/1.5 "Source Sans 3","Source Sans Pro",system-ui,sans-serif}
.bp5-text-muted,.muted{color:var(--ink)!important}h1,h2,h3,h4{margin:0;font-weight:700}a{color:var(--blue)}
.frame{max-width:1440px;margin:0 auto;padding:20px 24px}
.card{background:#fff;border:1px solid var(--line);border-radius:4px;box-shadow:0 1px 1px rgba(17,20,24,.06)}
.card .hd{display:flex;align-items:center;gap:14px;padding:16px 20px;border-bottom:1px solid var(--line)}
.tile{width:40px;height:40px;border-radius:6px;display:flex;align-items:center;justify-content:center;color:#fff;font-size:20px;flex:none}
.tile.purple{background:var(--purple)}.tile.blue{background:var(--blue)}.tile.green{background:var(--green)}.tile.grey{background:#8f99a8}
.hd h2{font-size:20px}.hd .sub{font-size:14px;font-weight:500;margin-top:2px}.hd .right{margin-left:auto;font-weight:600;color:var(--blue)}
.band{background:#e8e4f3}
.body{padding:18px 20px}
.btn{display:inline-flex;align-items:center;gap:8px;border:1px solid var(--line);background:#f6f7f9;color:var(--ink);font:600 15px "Source Sans 3",sans-serif;padding:9px 16px;border-radius:3px;cursor:pointer}
.btn.blue{background:var(--blue);border-color:var(--blue);color:#fff}.btn.green{background:var(--green);border-color:var(--green);color:#fff;width:100%;justify-content:center}.btn.sm{padding:4px 10px;font-size:13px}
textarea.q{width:100%;min-height:150px;border:1px solid var(--line);border-radius:3px;padding:12px 14px;font:500 16px/1.5 "Source Sans 3",sans-serif;resize:vertical}
.two{display:grid;grid-template-columns:minmax(380px,1fr) minmax(380px,1fr);gap:22px;align-items:start}
.section{padding:14px 20px}.section h3{font-size:16px}.section .sub{font-weight:500;font-size:14px}
.empty{padding:56px 20px;text-align:center;font-weight:700;font-size:20px}.empty .ic{font-size:44px;display:block;margin-bottom:12px;color:#8f99a8}
.kv{display:grid;grid-template-columns:150px 1fr;gap:6px 14px;padding:12px 16px;border:1px solid var(--line);border-radius:3px;margin:10px 0}
.kv .k{font-weight:600}.kv .v{font-weight:500}
.pass{border:1px solid var(--line);border-radius:3px;padding:14px 16px;margin:10px 0;background:#fff}.pass .lbl{font-weight:700;font-size:15px}.pass .act{font-weight:600;font-size:13px}
.pass q{display:block;margin:8px 0;font-weight:500;font-size:15px;quotes:"«" "»"}
.tag{display:inline-block;padding:2px 10px;border-radius:3px;font-weight:700;font-size:12.5px;letter-spacing:.02em}
.tag.sempre{background:#e3f2e9;color:var(--green)}.tag.condicional{background:var(--orange-bg);color:var(--orange)}.tag.nao{background:var(--red-bg);color:var(--red)}.tag.n{background:#edeff2;color:var(--ink)}.tag.blue{background:var(--blue-bg);color:var(--blue)}
.pager{margin-left:auto;display:flex;align-items:center;gap:10px;font-weight:600}.pager b{color:var(--blue);border-bottom:3px solid var(--blue);padding-bottom:2px}
.pick{border-color:var(--blue);box-shadow:0 0 0 2px var(--blue-bg)}
.ov{display:grid;grid-template-columns:296px 1fr;gap:0;border:1px solid var(--line);background:#fff;border-radius:4px;min-height:calc(100vh - 150px)}
.rail{border-right:1px solid var(--line)}.rail .who{display:flex;align-items:center;gap:12px;padding:16px 18px;border-bottom:1px solid var(--line);font-size:19px;font-weight:700}
.rail .who .ic{width:34px;height:34px;border-radius:6px;background:#edeff2;display:flex;align-items:center;justify-content:center;font-size:18px}
.rail a.item{display:flex;align-items:center;gap:12px;padding:13px 18px;color:var(--ink);text-decoration:none;font-weight:600;font-size:16px}.rail a.item.on{background:var(--blue);color:#fff}
.rail .facts{padding:14px 18px;border-top:1px solid var(--line);font-size:14px}.rail .facts .k{font-weight:700;font-size:12px;letter-spacing:.06em;text-transform:uppercase;margin-top:10px}
.main{display:grid;grid-template-rows:auto 1fr}.tabs{display:flex;gap:6px;padding:10px 12px;border-bottom:1px solid var(--line);flex-wrap:wrap}
.tabs a{display:inline-flex;align-items:center;gap:8px;padding:8px 14px;border-radius:3px;color:var(--ink);text-decoration:none;font-weight:600;font-size:15px}.tabs a.on{background:var(--blue-bg);color:var(--blue)}
.split{display:grid;grid-template-columns:minmax(420px,1fr) minmax(380px,40%)}
.content{padding:16px 20px;overflow:auto;max-height:calc(100vh - 210px)}.preview{border-left:1px solid var(--line);display:flex;flex-direction:column}
.preview .bar{display:flex;justify-content:space-between;align-items:center;padding:12px 16px;border-bottom:1px solid var(--line);font-weight:700;font-size:16px}
.preview iframe{flex:1;border:0;min-height:60vh;background:#fff}.preview .empty{flex:1;display:flex;flex-direction:column;align-items:center;justify-content:center}
table.t{border-collapse:collapse;width:100%}.t th,.t td{border-bottom:1px solid var(--line);padding:9px 10px;text-align:left;vertical-align:top;font-size:14.5px}.t th{font-size:12.5px;text-transform:uppercase;letter-spacing:.05em}
.t tr.row{cursor:pointer}.t tr.row:hover{background:#f6f7f9}.t tr.sel td{background:var(--blue-bg)}
.q{display:block;margin:6px 0;padding:8px 10px;background:#fbf8ec;border-left:3px solid var(--orange);font-weight:500;cursor:pointer}
details.law summary{cursor:pointer;font-weight:600;color:var(--blue)}details.law q{display:block;margin-top:6px;font-weight:500}
.strip{display:flex;gap:26px;align-items:flex-end;padding:0 4px 14px;flex-wrap:wrap}.strip .n{font-size:26px;font-weight:700;line-height:1}.strip .n.red{color:var(--red)}.strip .n.green{color:var(--green)}.strip .k{font-size:12px;font-weight:700;letter-spacing:.06em;text-transform:uppercase;margin-bottom:4px}
textarea.conv{width:100%;min-height:58vh;border:1px solid var(--line);border-radius:3px;padding:12px;font:500 14px/1.55 ui-monospace,Menlo,monospace}
.inbox .row2{display:grid;grid-template-columns:1fr auto;gap:12px;align-items:center;padding:14px 20px;border-bottom:1px solid var(--line)}
.inbox .row2 .t{font-size:17px;font-weight:700}.inbox .row2 .m{font-size:14px;font-weight:500;margin-top:2px}
.state{display:inline-block;padding:2px 10px;border-radius:3px;font-weight:700;font-size:12.5px;margin-left:8px}.state.novo{background:var(--blue-bg);color:var(--blue)}.state.em_analise{background:var(--orange-bg);color:var(--orange)}.state.convite_enviado{background:var(--red-bg);color:var(--red)}.state.saneado{background:#e3f2e9;color:var(--green)}
@media(max-width:1100px){.two{grid-template-columns:1fr}.ov{grid-template-columns:1fr}.rail{border-right:0;border-bottom:1px solid var(--line)}.split{grid-template-columns:1fr}.preview{border-left:0;border-top:1px solid var(--line)}}
</style>"""

STATES = [("novo", "Novo"), ("em_analise", "Em análise"), ("convite_enviado", "Convite enviado"), ("saneado", "Saneado")]
EXAMPLES = ["Preciso de projeto de gás numa moradia unifamiliar?", "O levantamento topográfico é sempre obrigatório?", "A planta de implantação tem de ir em DWG?",
            "Quando é que preciso de pareceres de entidades externas?", "Qual é o prazo do convite ao aperfeiçoamento?", "Fotografias do terreno são obrigatórias?"]


def head(title):
    return f'<!doctype html><html lang="pt"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>{html.escape(title)}</title>{BP}{CSS}</head>'


def lei(inline=None):
    """The "Request" screen. inline = a pre-computed answer {pergunta, passagens, escolhida, leitor} for a preview without a server."""
    data = json.dumps(inline, ensure_ascii=False) if inline else "null"
    ex = "".join(f'<div class="kv"><div class="k">Exemplo</div><div class="v"><a href="#" onclick="event.preventDefault();ask({json.dumps(e)})">{html.escape(e)}</a></div></div>' for e in EXAMPLES)
    return head("Pergunte à lei") + f"""<body><div class="frame">
<div class="card"><div class="hd band"><div class="tile purple"><span class="bp5-icon-standard bp5-icon-help"></span></div><div><h2>Pergunte à lei</h2><div class="sub">A pergunta de um técnico, nas suas palavras; a resposta são as passagens da lei, citadas letra a letra, e a condição em que se aplicam.</div></div>
<div class="right"><span class="bp5-icon-standard bp5-icon-cog"></span> Portaria n.º 320/2026/1 · RJUE</div></div>
<div class="body"><div class="two">
<div>
  <div class="section" style="padding-left:0;padding-top:0"><h3><span class="bp5-icon-standard bp5-icon-chat"></span> Pergunta do técnico</h3><div class="sub">Escreva como falaria com um colega. O motor procura nas passagens da lei decomposta; AMALIA escolhe a passagem; o código diz se é exigido sempre, só em certa condição, ou não.</div></div>
  <div class="card" style="padding:16px 18px"><textarea class="q" id="q" placeholder="Ex.: preciso de projeto de gás numa moradia unifamiliar?"></textarea>
    <div style="display:flex;justify-content:flex-end;margin-top:12px"><button class="btn blue" onclick="ask()"><span class="bp5-icon-standard bp5-icon-arrow-right"></span> Submeter</button></div></div>
  <div class="section" style="padding-left:0;margin-top:10px"><h3><span class="bp5-icon-standard bp5-icon-lightning"></span> Resposta</h3></div>
  <div class="card" id="answer"><div class="empty"><span class="ic bp5-icon-large bp5-icon-help"></span>Escreva uma pergunta e carregue em «Submeter».</div></div>
  <div class="card" style="margin-top:18px"><div class="hd"><div class="tile grey"><span class="bp5-icon-standard bp5-icon-book"></span></div><div><h2 style="font-size:17px">Passagens encontradas</h2><div class="sub">As passagens da lei mais próximas da pergunta</div></div><div class="pager" id="pager"></div></div>
    <div class="body" id="passages"><div class="empty"><span class="ic bp5-icon-large bp5-icon-refresh"></span>Nenhuma passagem ainda.</div></div></div>
</div>
<div class="card"><div class="hd"><div class="tile purple"><span class="bp5-icon-standard bp5-icon-lightbulb"></span></div><div><h2 style="font-size:19px">Configuração</h2><div class="sub">O que conta como exigido, e quem responde.</div></div></div>
  <div class="body">
   <div class="section" style="padding:0 0 6px"><h3><span class="bp5-icon-standard bp5-icon-user"></span> Pedido</h3><div class="sub">A lista do Anexo V que conta para este pedido.</div></div>
   <div class="kv"><div class="k">Procedimento</div><div class="v">Comunicação prévia de obras de edificação (CP/CPEDI)</div><div class="k">Conta</div><div class="v">Anexo V n.º 27 + elementos comuns n.os 5 a 17; Anexo VI e VII; RJUE</div></div>
   <div class="section" style="padding:8px 0 6px"><h3><span class="bp5-icon-standard bp5-icon-globe"></span> Quem responde</h3><div class="sub">O código decide; o leitor escolhe a passagem.</div></div>
   <div class="kv"><div class="k">Passagens</div><div class="v">pesquisa no texto decomposto (Portaria 320/2026/1 e RJUE)</div><div class="k">Exigido</div><div class="v">lido pelo código da própria passagem (regra do pacote cp-edificacao)</div><div class="k">AMALIA</div><div class="v"><label><input type="checkbox" id="leitor" checked> confirma a passagem (só pode citar uma das candidatas)</label></div></div>
   <div class="section" style="padding:8px 0 6px"><h3><span class="bp5-icon-standard bp5-icon-manual"></span> Exemplos</h3></div>{ex}
   <button class="btn green" style="margin-top:8px" onclick="ask($('q').value)"><span class="bp5-icon-standard bp5-icon-plus"></span> Perguntar</button>
  </div></div>
</div></div></div>
<p style="margin:14px 4px"><b>O leitor lê, o código decide, o técnico assina.</b> Nada aqui é parecer jurídico: são as palavras da lei e a condição que elas próprias põem. · <a href="/expedientes">expedientes</a></p>
</div>
<script>
const INLINE={data};const $=id=>document.getElementById(id);const esc=s=>String(s??"").replace(/[&<>"]/g,c=>({{"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;"}}[c]));
const TAG={{sempre:["Exigido sempre","sempre"],condicional:["Exigido em certa condição","condicional"],nao:["Não exigido neste pedido","nao"],"—":["Não é um elemento: lê-se","n"]}};
let page=0,R=null;
function pass(c,picked){{const [t,k]=TAG[c.exigido]||[c.exigido,"n"];return `<div class="pass ${{picked?"pick":""}}"><div style="display:flex;gap:10px;align-items:center;flex-wrap:wrap"><span class="lbl">${{esc(c.label)}}</span><span class="act">${{esc(c.act)}}</span><span class="tag ${{k}}">${{t}}</span>${{picked?'<span class="tag blue">escolhida por AMALIA</span>':''}}</div><q>${{esc(c.text)}}</q>${{c.condicao?`<div><b>Condição:</b> «${{esc(c.condicao)}}»</div>`:""}}<div style="font-size:13px">${{esc(c.porque)}}</div></div>`}}
function render(){{const ps=R.passagens||[];const per=3,n=Math.max(1,Math.ceil(ps.length/per));page=Math.min(page,n-1);
 $('pager').innerHTML=`<a href="#" onclick="event.preventDefault();page=Math.max(0,page-1);render()">‹</a> <b>${{page+1}}</b> / ${{n}} <a href="#" onclick="event.preventDefault();page=Math.min(${{n-1}},page+1);render()">›</a>`;
 $('passages').innerHTML=ps.length?ps.slice(page*per,page*per+per).map(c=>pass(c,R.escolhida&&R.escolhida.id===c.id)).join(""):'<div class="empty"><span class="ic bp5-icon-large bp5-icon-refresh"></span>Nenhuma passagem encontrada.</div>';
 const top=R.escolhida||ps[0];
 $('answer').innerHTML=top?`<div class="body"><div style="display:flex;gap:10px;align-items:center;flex-wrap:wrap;margin-bottom:8px"><span class="tag ${{(TAG[top.exigido]||["","n"])[1]}}" style="font-size:15px;padding:5px 12px">${{(TAG[top.exigido]||[top.exigido])[0]}}</span>${{R.escolhida?'<span class="tag blue">passagem confirmada por AMALIA</span>':(R.leitor==="a confirmar"?'<span class="tag n">AMALIA a confirmar…</span>':(R.leitor?'<span class="tag n">'+esc(R.leitor)+'</span>':''))}}</div>
  <div style="font-size:17px;font-weight:700">${{esc(top.label)}} <span style="font-weight:500">· ${{esc(top.act)}}</span></div><q style="display:block;margin:10px 0;font-size:16px;font-weight:500">«${{esc(top.text)}}»</q>${{top.condicao?`<div><b>Condição:</b> «${{esc(top.condicao)}}»</div>`:""}}<div style="margin-top:8px;font-size:13.5px">${{esc(top.porque)}}</div></div>`:'<div class="empty">Sem resposta.</div>'}}
async function poll(id){{for(let i=0;i<60;i++){{await new Promise(z=>setTimeout(z,5000));const r=await fetch('/v1/lei/'+id);if(!r.ok)return;const j=await r.json();if(j.leitor!=="a confirmar"){{R=j;render();return}}}}}}
async function ask(q){{q=q||$('q').value.trim();if(!q)return;$('q').value=q;$('answer').innerHTML='<div class="empty">a procurar…</div>';
 if(INLINE){{R=INLINE;render();return}}
 const r=await fetch('/v1/lei',{{method:'POST',headers:{{'Content-Type':'application/json'}},body:JSON.stringify({{pergunta:q,leitor:$('leitor').checked}})}});
 if(!r.ok){{$('answer').innerHTML='<div class="empty">erro '+r.status+'</div>';return}}R=await r.json();page=0;render();if(R.leitor==="a confirmar")poll(R.id)}}
if(INLINE){{$('q').value=INLINE.pergunta;R=INLINE;render()}}
</script></body></html>"""


def app(pdf_base="ficheiros/", back="/expedientes", inline=None):
    """The "full object view, high density" screen for one expediente. inline embeds {"verdict","convite"} for a preview without a server."""
    data = f"const INLINE={json.dumps(inline, ensure_ascii=False)};" if inline else "const INLINE=null;"
    return head("Expediente") + f"""<body><div class="frame">
<div class="strip" id="strip"><div><div class="k">Expediente</div><h1 id="h1" style="font-size:24px">a carregar…</h1></div></div>
<div class="ov">
 <aside class="rail"><div class="who"><span class="ic bp5-icon-standard bp5-icon-id-number"></span><span id="who">—</span></div>
  <a class="item on" href="#" data-t="deficiencias" onclick="event.preventDefault();show('deficiencias')"><span class="bp5-icon-standard bp5-icon-issue"></span> Deficiências</a>
  <a class="item" href="#" data-t="elementos" onclick="event.preventDefault();show('elementos')"><span class="bp5-icon-standard bp5-icon-form"></span> Elementos</a>
  <a class="item" href="#" data-t="ficheiros" onclick="event.preventDefault();show('ficheiros')"><span class="bp5-icon-standard bp5-icon-document"></span> Documentos</a>
  <div class="facts" id="facts"></div>
  <div class="facts"><a href="{html.escape(back)}"><span class="bp5-icon-standard bp5-icon-arrow-left"></span> expedientes</a> · <a href="verdict.json">JSON</a> · <a href="/lei">pergunte à lei</a></div></aside>
 <section class="main"><nav class="tabs" id="tabs">
   <a href="#" class="on" data-t="deficiencias" onclick="event.preventDefault();show('deficiencias')"><span class="bp5-icon-standard bp5-icon-endorsed"></span> Deficiências</a>
   <a href="#" data-t="revisao" onclick="event.preventDefault();show('revisao')"><span class="bp5-icon-standard bp5-icon-bookmark"></span> Revisão</a>
   <a href="#" data-t="elementos" onclick="event.preventDefault();show('elementos')"><span class="bp5-icon-standard bp5-icon-form"></span> Elementos</a>
   <a href="#" data-t="factos" onclick="event.preventDefault();show('factos')"><span class="bp5-icon-standard bp5-icon-numerical"></span> Factos</a>
   <a href="#" data-t="ficheiros" onclick="event.preventDefault();show('ficheiros')"><span class="bp5-icon-standard bp5-icon-document"></span> Ficheiros</a>
   <a href="#" data-t="convite" onclick="event.preventDefault();show('convite')"><span class="bp5-icon-standard bp5-icon-envelope"></span> Convite</a></nav>
  <div class="split"><div class="content" id="pane"></div>
   <aside class="preview"><div class="bar"><span>Pré-visualização do documento</span><span id="docname" style="font-weight:500"></span></div>
    <div class="empty" id="docempty"><span class="bp5-icon-large bp5-icon-document" style="font-size:44px;color:#8f99a8"></span><div style="font-weight:700;font-size:18px;margin-top:10px">Pré-visualização do documento</div><div>Clique numa deficiência, numa citação ou num ficheiro.</div></div>
    <iframe id="pdf" style="display:none"></iframe></aside></div></section>
</div></div>
<script>
{data}const PDF="{html.escape(pdf_base)}";const $=s=>document.querySelector(s);let V=null,CONV="";
const TYPES={{missing_required:"Elemento em falta",missing_complement:"Complemento em falta",not_pdf:"Não é PDF",not_pdfa:"Sem PDF/A",unsigned:"Sem assinatura",template_wording_missing:"Sem redação do Anexo VII",value_mismatch:"Valores divergentes",impossible_value:"Valor impossível",wrong_site:"Local divergente",expired_insurance:"Seguro caducado",wrong_signer:"Assinatura de outra pessoa"}};
const STATE={{present:["sim","sempre"],missing:["FALTA","nao"],not_assessed:["não avaliado","condicional"],satisfied_by:["sim, via outro","sempre"],optional:["facultativo","n"],not_required_here:["n/a","n"]}};
const esc=s=>String(s??"").replace(/[&<>"]/g,c=>({{"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;"}}[c]));
function showPdf(file,page){{if(!file)return;const src=PDF+encodeURIComponent(file)+(page?("#page="+page):"");$("#pdf").src=src;$("#pdf").style.display="block";$("#docempty").style.display="none";$("#docname").textContent=file+(page?(" · p."+page):"")}}
function tag(st){{const [t,k]=STATE[st]||[st,"n"];return `<span class="tag ${{k}}">${{esc(t)}}</span>`}}
function law(f){{return f.law?`<details class="law" onclick="event.stopPropagation()"><summary>Anexo ${{esc(f.law.ref)}} · ver o texto da lei</summary><q>«${{esc(f.law.quote)}}»</q></details>`:""}}
function evid(f){{return (f.evidence||[]).map(e=>`<span class="q" onclick="event.stopPropagation();showPdf(${{JSON.stringify(e.file)}},${{e.page||1}})">${{esc(e.file)}} · p.${{esc(e.page)}} — «${{esc(e.quote)}}»</span>`).join("")}}
function table(list){{if(!list.length)return '<div class="empty"><span class="ic bp5-icon-large bp5-icon-tick-circle" style="color:var(--green)"></span>Sem deficiências.</div>';return `<table class="t"><tr><th>#</th><th>Deficiência</th><th>Onde</th><th>Evidência e lei</th></tr>`+list.map((f,i)=>`<tr class="row" onclick="sel(this);showPdf(${{JSON.stringify(f.file||'')}},${{(f.evidence&&f.evidence[0]&&f.evidence[0].page)||1}})"><td>${{i+1}}</td><td><span class="tag nao">${{esc(TYPES[f.type]||f.type)}}</span><div style="margin-top:4px">${{esc(f.detail||"")}}</div></td><td><b>${{esc(f.slot||"")}}</b><br>${{esc(f.file||f.rule||"")}}</td><td>${{evid(f)}}${{law(f)}}</td></tr>`).join("")+"</table>"}}
function sel(tr){{document.querySelectorAll("tr.sel").forEach(e=>e.classList.remove("sel"));tr.classList.add("sel")}}
const P={{
 deficiencias:()=>`<h3 style="font-size:17px;margin-bottom:10px">Deficiências (${{V.findings.length}}) — vão no convite</h3>`+table(V.findings),
 revisao:()=>{{const na=V.not_assessed||[],rv=V.review||[],nr=V.not_read||[],ab=V.absent||[];return `<h3 style="font-size:17px">Para revisão do técnico (${{rv.length}})</h3><p>O leitor e o campo discordam; nunca entra no convite sem o técnico.</p>${{rv.map(i=>`<div class="pass"><b><a href="#" onclick="event.preventDefault();showPdf(${{JSON.stringify(i.file)}},1)">${{esc(i.file)}}</a></b> — ${{esc(i.detail)}}${{i.element?" <span class='tag n'>"+esc(i.element)+"</span>":""}}</div>`).join("")||"<p>nenhum</p>"}}
  <h3 style="font-size:17px;margin-top:18px">Não avaliado (${{na.length}})</h3><p>Depende de factos que o expediente não traz.</p>${{na.map(i=>`<div class="pass"><b>${{esc(i.rule||i.type)}}</b>${{i.slot?" · "+esc(i.slot):""}} <span class="tag condicional">não avaliado</span><div>${{esc(i.condition||"")}}</div></div>`).join("")||"<p>nenhum</p>"}}
  <h3 style="font-size:17px;margin-top:18px">Não lido (${{nr.length}}) · sem valor no documento (${{ab.length}})</h3>${{nr.map(i=>`<div class="pass">${{esc(i.file)}} · ${{esc(i.field||i.type)}} — ${{esc(i.detail)}}</div>`).join("")||"<p>nenhum</p>"}}`}},
 elementos:()=>`<h3 style="font-size:17px;margin-bottom:10px">Elementos do Anexo V (${{V.elements.length}})</h3><table class="t"><tr><th>Elemento</th><th>Campos</th><th>Estado</th><th>Ficheiros</th></tr>`+V.elements.map(e=>`<tr class="row" onclick="sel(this);showPdf(${{JSON.stringify(e.files[0]||'')}},1)"><td><b>${{esc(e.element)}}</b></td><td>${{esc(e.slots.join(", "))}}</td><td>${{tag(e.state)}}</td><td>${{e.files.map(n=>esc(n)).join("<br>")}}</td></tr>`).join("")+"</table>",
 factos:()=>{{const F=V.facts||{{}};const keys=Object.keys(F);const fx=V.findings.filter(f=>["value_mismatch","impossible_value","expired_insurance"].includes(f.type));return `<h3 style="font-size:17px;margin-bottom:10px">Factos divergentes (${{fx.length}})</h3>`+table(fx)+`<h3 style="font-size:17px;margin:18px 0 10px">Factos lidos</h3><table class="t"><tr><th>Facto</th><th>Valor</th><th>Onde</th><th>Citação</th></tr>`+keys.map(k=>F[k].map(v=>`<tr class="row" onclick="sel(this);showPdf(${{JSON.stringify(v.file)}},${{v.page||1}})"><td><b>${{esc(k)}}</b></td><td>${{esc(v.value)}}</td><td>${{esc(v.slot)}} · p.${{esc(v.page)}}</td><td>«${{esc(v.quote)}}»</td></tr>`).join("")).join("")+"</table>"}},
 ficheiros:()=>`<h3 style="font-size:17px;margin-bottom:10px">Ficheiros (${{V.files.length}})</h3><table class="t"><tr><th>Ficheiro</th><th>Campo</th><th>PDF</th><th>PDF/A</th><th>Assinado</th><th>Pág.</th><th>Elemento lido</th></tr>`+V.files.map(f=>{{const ok=(V.elements_ok||[]).find(x=>x.file===f.file);const rv=(V.review||[]).find(x=>x.file===f.file);return `<tr class="row" onclick="sel(this);showPdf(${{JSON.stringify(f.file)}},1)"><td>${{esc(f.file)}}</td><td>${{esc(f.slot||f.slot_raw||"")}}</td><td>${{f.is_pdf?"sim":'<span class="tag nao">não</span>'}}</td><td>${{f.pdfa?"sim":(f.is_pdf?'<span class="tag nao">não</span>':"")}}</td><td>${{f.signed?("sim"+(f.signer?" · "+esc(f.signer.cn):"")):(f.is_pdf?'<span class="tag condicional">não</span>':"")}}</td><td>${{f.n||""}}</td><td>${{ok?esc(ok.element):(rv?'<span class="tag condicional">revisão</span>':"")}}</td></tr>`}}).join("")+"</table>",
 convite:()=>`<h3 style="font-size:17px">Convite ao aperfeiçoamento — rascunho</h3><p>Editável. Copie para o ofício da câmara e assine. <button class="btn sm" onclick="navigator.clipboard.writeText($('#conv').value)">copiar</button> <a href="convite.md" download>descarregar .md</a></p><textarea class="conv" id="conv">${{esc(CONV)}}</textarea>`}};
function show(t){{document.querySelectorAll("[data-t]").forEach(a=>a.classList.toggle("on",a.dataset.t===t));$("#pane").innerHTML=P[t]()}}
async function load(){{if(INLINE){{V=INLINE.verdict;CONV=INLINE.convite}}else{{V=await (await fetch("verdict.json")).json();try{{CONV=await (await fetch("convite.md")).text()}}catch(e){{CONV=""}}}}
 const c=V.counts||{{}};$("#h1").textContent=V.label||V.expediente;$("#who").textContent=V.applicant||V.expediente;
 $("#strip").insertAdjacentHTML("beforeend",`<div><div class="k">deficiências</div><div class="n ${{c.finding?"red":"green"}}">${{c.finding||0}}</div></div><div><div class="k">não avaliado</div><div class="n">${{c.not_assessed||0}}</div></div><div><div class="k">revisão</div><div class="n">${{c.review||0}}</div></div><div><div class="k">elementos confirmados</div><div class="n green">${{c.ok||0}}</div></div><div><div class="k">leitor</div><div style="font-weight:600">${{esc((V.reader&&V.reader.adapter)||"sem leituras")}}</div></div>`);
 $("#facts").innerHTML=[["operação",V.operation],["requerente",V.applicant],["verificado",(V.checked_at||"").slice(0,16).replace("T"," ")+" UTC"],["ficheiros",V.files.length],["lei",V.law]].map(([k,v])=>`<div class="k">${{k}}</div><div>${{esc(v||"—")}}</div>`).join("");
 show("deficiencias");const f=V.findings.find(x=>x.file);if(f)showPdf(f.file,(f.evidence&&f.evidence[0]&&f.evidence[0].page)||1)}}
load();
</script></body></html>"""


def inbox(rows, municipality):
    esc = html.escape
    out = []
    for r in rows:
        c = r.get("counts") or {}
        st = r.get("estado") or ("novo" if r.get("files") else "")
        pend = not r.get("files")
        out.append(f"""<div class="row2"><div><div class="t"><a href="/expedientes/{esc(r['id'])}/">{esc(r['label'])}</a><span class="state {esc(st)}">{esc(dict(STATES).get(st, st))}</span></div>
 <div class="m">{esc((r.get('at') or '')[:16].replace('T', ' '))} UTC · {r.get('files', 0)} ficheiros · leitor {esc(r.get('reader') or '—')}{(' · responsável <b>' + esc(r['responsavel']) + '</b>') if r.get('responsavel') else ''}
 {'' if pend else f" · <span class='tag {'nao' if c.get('finding') else 'sempre'}'>{c.get('finding', 0)} deficiência(s)</span> <span class='tag condicional'>{c.get('not_assessed', 0)} não avaliado</span>"}</div></div>
 <div>{'' if pend else ''.join(f'<button class="btn sm" onclick="setState(this,{json.dumps(r["id"])},{json.dumps(k)})">{esc(v)}</button> ' for k, v in STATES if k != st)}{'' if pend else f'<button class="btn sm" onclick="assign(this,{json.dumps(r["id"])})">assumir</button>'}</div></div>""")
    n_bad = sum(1 for r in rows if (r.get("counts") or {}).get("finding"))
    return head(f"Expedientes · {municipality}") + f"""<body><div class="frame">
<div class="card"><div class="hd"><div class="tile blue"><span class="bp5-icon-standard bp5-icon-inbox"></span></div><div><h2>Expedientes · {esc(municipality)}</h2><div class="sub">Comunicação prévia de obras de edificação · {len(rows)} expedientes · {n_bad} com deficiências · {len(rows) - n_bad} limpos</div></div><div class="right"><a href="/">+ novo expediente</a> · <a href="/lei">pergunte à lei</a></div></div>
<div class="inbox">{''.join(out) or '<div class="empty">Nenhum expediente ainda.</div>'}</div></div>
<p style="margin:14px 4px"><b>O leitor lê, o código decide, o técnico assina.</b> Estados: novo → em análise → convite enviado → saneado.</p></div>
<script>
async function setState(b,id,st){{b.disabled=true;const r=await fetch('/v1/expedientes/'+id+'/trabalho',{{method:'POST',headers:{{'Content-Type':'application/json'}},body:JSON.stringify({{estado:st}})}});if(r.ok)location.reload();else{{b.disabled=false;alert('erro '+r.status)}}}}
async function assign(b,id){{const n=prompt('Nome do técnico responsável');if(!n)return;b.disabled=true;const r=await fetch('/v1/expedientes/'+id+'/trabalho',{{method:'POST',headers:{{'Content-Type':'application/json'}},body:JSON.stringify({{responsavel:n,estado:'em_analise'}})}});if(r.ok)location.reload();else{{b.disabled=false;alert('erro '+r.status)}}}}
</script></body></html>"""
