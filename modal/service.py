"""The verdict layer as a hosted service (D20): nothing runs on a laptop. One Modal app with a web endpoint (FastAPI), a volume for
the expedientes and their verdicts, and the reader (app saneamento-reader, deployed) called as a function.

    modal deploy modal/reader.py          # the reader as a persistent app (Function.from_name needs it)
    modal deploy modal/service.py         # this; prints the URL

    GET  /                                upload page (PT): drop a zip, get the verdict; demo buttons for the exam dossiers
    POST /v1/expedientes[?nome=…&leitor=0] X-API-Key; body: the zip (application/zip) or multipart "ficheiro"; -> {"id","url"}
    POST /v1/demo/{A|B|C}                 X-API-Key; the exam dossier as an expediente (simulated, carried in the image)
    GET  /expedientes                     list page (key by header or cookie)
    GET  /expedientes/{id}/               verdict.html; …/verdict.json; …/convite.md; …/ficheiros/{name} the uploaded PDFs
    GET  /v1/saude                        public liveness

Storage: volume saneamento-store, /store/<municipality>/<id>/{files/, reads/, verdict.json, convite.md, verdict.html, meta.json}.
Key: Modal secret saneamento-token (SANEAMENTO_TOKEN); the one key is Celorico de Basto's for now (one municipality = one key).
Processing runs in a worker function (process_expediente.spawn): a web request must answer within Modal's 150 s, the reader loads
in ≈ 2.5 min when cold. POST answers at once with the id; the page polls GET /v1/expedientes/{id}/estado until the verdict exists.
Until a câmara signs a data-processing agreement only simulated expedientes go through here (the engine needs no citizen data,
the files carry it). The image carries engine/, generator/, law/, structure/, celorico/ and exam/dossiers/; no training data.
"""
import hashlib
import hmac
import html
import io
import json
import os
import re
import shutil
import sys
import time
import zipfile
from datetime import datetime, timezone
from pathlib import Path

import modal

ROOT = Path(__file__).resolve().parent.parent
REMOTE = "/root/app"
MUNICIPALITY = "celorico-de-basto"
LORA = os.environ.get("SANEAMENTO_LORA", "r11")

image = (modal.Image.debian_slim(python_version="3.12").apt_install("openssl").pip_install("fastapi[standard]==0.115.12", "python-multipart==0.0.20", "pypdf==6.1.3")
         .add_local_dir(ROOT / "engine", f"{REMOTE}/engine", ignore=["reads/**", "verdicts/**", "__pycache__/**"])
         .add_local_dir(ROOT / "generator", f"{REMOTE}/generator", ignore=["__pycache__/**"])
         .add_local_dir(ROOT / "law", f"{REMOTE}/law").add_local_dir(ROOT / "structure", f"{REMOTE}/structure")
         .add_local_dir(ROOT / "celorico", f"{REMOTE}/celorico").add_local_dir(ROOT / "exam" / "dossiers", f"{REMOTE}/exam/dossiers"))
store = modal.Volume.from_name("saneamento-store", create_if_missing=True)
app = modal.App("saneamento-service", image=image)


def _process(muni, eid, files_dir, use_reader, label):
    """The verdict of one stored expediente: reader (optional) → application.verdict → files next to the PDFs. Runs in the worker."""
    sys.path.insert(0, REMOTE)
    from engine import application as A
    from engine import read as R
    t0 = time.time()
    reads = None
    if use_reader:
        reader = modal.Function.from_name("saneamento-reader", "answer")
        reads = R.read_with(files_dir, LORA, lambda items, lora, guard: reader.remote(items, lora, guard))
        rd = files_dir.parent / "reads"
        rd.mkdir(exist_ok=True)
        (rd / "prompts.jsonl").write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in reads["prompt_rows"]), encoding="utf-8")
        (rd / "answers-checked.json").write_text(json.dumps(reads["checked"], ensure_ascii=False), encoding="utf-8")
    v = A.verdict(files_dir, reads if reads is not None else {"meta": None, "rows": {}, "answers": {}})
    v["id"], v["municipality"], v["label"] = eid, muni, label or v["expediente"]
    v["seconds"] = round(time.time() - t0, 1)
    out = files_dir.parent
    (out / "verdict.json").write_text(json.dumps(v, ensure_ascii=False, indent=1), encoding="utf-8")
    (out / "convite.md").write_text(A.convite(v), encoding="utf-8")
    (out / "verdict.html").write_text(A.page(v).replace("</h1>", "</h1><p><a href='/expedientes'>← expedientes</a> · <a href='convite.md'>convite.md</a> · <a href='verdict.json'>verdict.json</a></p>", 1), encoding="utf-8")
    meta = {"id": eid, "municipality": muni, "label": v["label"], "at": v["checked_at"], "counts": v["counts"], "files": len(v["files"]),
            "reader": (v.get("reader") or {}).get("adapter"), "seconds": v["seconds"]}
    (out / "meta.json").write_text(json.dumps(meta, ensure_ascii=False), encoding="utf-8")
    return meta


@app.function(volumes={"/store": store}, timeout=900)
def answer_law(qid: str):
    """AMALIA picks the passage among the code's candidates (D0 «exigencia» task); the pick counts only if the checker accepts it."""
    sys.path.insert(0, REMOTE)
    from engine import law_search
    store.reload()
    f = Path("/store") / "_lei" / f"{qid}.json"
    r = json.loads(f.read_text(encoding="utf-8"))
    try:
        L = law_search.law()
        cands = r["passagens"]
        prompt = L.prompt(r["pergunta"], cands)
        reader = modal.Function.from_name("saneamento-reader", "answer")
        out = reader.remote([{"key": qid, "task": "exigencia", "prompt": prompt}], LORA, False)
        text = next((o.get("text") for o in out[1:] if o.get("key") == qid), None)
        pick, why = L.check(text, cands) if text else (None, "sem resposta")
        r["escolhida"] = pick
        r["leitor"] = "confirmada" if pick else f"sem confirmação ({why})"
        r["leitor_meta"] = {"adapter": out[0]["meta"].get("adapter"), "seconds": out[0]["meta"].get("generate_seconds")}
    except Exception as e:
        r["leitor"] = f"erro do leitor ({type(e).__name__})"
    f.write_text(json.dumps(r, ensure_ascii=False), encoding="utf-8")
    store.commit()
    return r["leitor"]


@app.function(volumes={"/store": store}, timeout=1800)
def process_expediente(muni: str, eid: str, use_reader: bool, label: str):
    store.reload()
    base = Path("/store") / muni / eid
    try:
        meta = _process(muni, eid, base / "files", use_reader, label)
    except Exception as e:  # the técnico sees why, the stack stays in the logs
        (base / "error.json").write_text(json.dumps({"id": eid, "erro": f"{type(e).__name__}: {e}"[:500], "at": datetime.now(timezone.utc).isoformat(timespec="seconds")}, ensure_ascii=False), encoding="utf-8")
        store.commit()
        raise
    store.commit()
    return meta


def _app():
    from fastapi import FastAPI, Header, HTTPException, Request, Response, UploadFile, File
    from fastapi.responses import HTMLResponse, JSONResponse, PlainTextResponse, RedirectResponse

    sys.path.insert(0, REMOTE)
    from engine import application as A
    from engine import read as R
    from engine import ui
    from engine import law_search

    web = FastAPI(title="saneamento-engine", docs_url=None, redoc_url=None)
    STORE = Path("/store")
    TOKEN = os.environ.get("SANEAMENTO_TOKEN", "")
    reader = modal.Function.from_name("saneamento-reader", "answer")

    def authed(request, x_api_key):
        key = x_api_key or request.cookies.get("sk") or ""
        if not TOKEN or not hmac.compare_digest(key, TOKEN):
            raise HTTPException(401, "chave em falta ou inválida (X-API-Key)")
        return MUNICIPALITY

    def new_id(name):
        stamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
        return f"{stamp}-{hashlib.sha256(f'{name}{time.time()}'.encode()).hexdigest()[:6]}"

    def start(muni, eid, use_reader, label):
        (STORE / muni / eid / "pending.json").write_text(json.dumps({"id": eid, "label": label, "at": datetime.now(timezone.utc).isoformat(timespec="seconds"), "leitor": use_reader}), encoding="utf-8")
        store.commit()
        process_expediente.spawn(muni, eid, use_reader, label)
        return {"id": eid, "url": f"/expedientes/{eid}/", "estado": "a processar", "estado_url": f"/v1/expedientes/{eid}/estado"}

    def unzip_to(data, files_dir):
        files_dir.mkdir(parents=True, exist_ok=True)
        n = 0
        with zipfile.ZipFile(io.BytesIO(data)) as z:
            for info in z.infolist():
                name = Path(info.filename).name
                if info.is_dir() or not name or name.startswith(".") or name.startswith("__MACOSX") or info.file_size > 60 * 1024 * 1024:
                    continue
                if not re.fullmatch(r"[\w .()\-–]+", name):
                    continue
                (files_dir / name).write_bytes(z.read(info))
                n += 1
        return n

    @web.get("/v1/saude")
    def saude():
        return {"ok": True, "leitor": f"amalia-saneamento-{LORA}", "municipio": MUNICIPALITY}

    @web.post("/v1/expedientes")
    async def upload(request: Request, nome: str = "", leitor: str = "1", x_api_key: str | None = Header(default=None), ficheiro: UploadFile | None = File(default=None)):
        muni = authed(request, x_api_key)
        data = await ficheiro.read() if ficheiro is not None else await request.body()
        if not data or len(data) > 200 * 1024 * 1024:
            raise HTTPException(400, "zip em falta ou acima de 200 MB")
        label = nome or (ficheiro.filename if ficheiro is not None else "") or "expediente"
        eid = new_id(label)
        base = STORE / muni / eid
        try:
            n = unzip_to(data, base / "files")
        except zipfile.BadZipFile:
            shutil.rmtree(base, ignore_errors=True)
            raise HTTPException(400, "o corpo não é um zip")
        if n == 0:
            shutil.rmtree(base, ignore_errors=True)
            raise HTTPException(400, "zip sem ficheiros")
        return {**start(muni, eid, leitor != "0", label), "ficheiros": n}

    @web.post("/v1/demo/{dossier}")
    def demo(dossier: str, request: Request, leitor: str = "1", x_api_key: str | None = Header(default=None)):
        muni = authed(request, x_api_key)
        src = Path(REMOTE) / "exam" / "dossiers" / dossier
        if dossier not in ("A", "B", "C") or not src.is_dir():
            raise HTTPException(404, "dossier A, B ou C")
        eid = new_id(dossier)
        base = STORE / muni / eid
        shutil.copytree(src, base / "files")
        return start(muni, eid, leitor != "0", f"exame {dossier} (simulado)")

    @web.get("/v1/expedientes/{eid}/estado")
    def estado(eid: str, request: Request, x_api_key: str | None = Header(default=None)):
        muni = authed(request, x_api_key)
        store.reload()
        base = STORE / muni / safe(eid)
        if (base / "meta.json").exists():
            return {"estado": "pronto", **json.loads((base / "meta.json").read_text(encoding="utf-8")), "url": f"/expedientes/{eid}/"}
        if (base / "error.json").exists():
            return {"estado": "erro", **json.loads((base / "error.json").read_text(encoding="utf-8"))}
        if (base / "pending.json").exists():
            return {"estado": "a processar", **json.loads((base / "pending.json").read_text(encoding="utf-8"))}
        raise HTTPException(404, "expediente desconhecido")

    def listing(muni):
        store.reload()
        rows = []
        root = STORE / muni
        if root.is_dir():
            for d in sorted(root.iterdir(), reverse=True):
                if (d / "meta.json").exists():
                    rows.append(json.loads((d / "meta.json").read_text(encoding="utf-8")))
                elif (d / "error.json").exists():
                    e = json.loads((d / "error.json").read_text(encoding="utf-8"))
                    rows.append({"id": d.name, "label": f"ERRO — {e['erro'][:60]}", "at": e["at"], "files": 0, "counts": {"finding": 0, "not_assessed": 0}, "reader": None, "seconds": ""})
                elif (d / "pending.json").exists():
                    p = json.loads((d / "pending.json").read_text(encoding="utf-8"))
                    rows.append({"id": d.name, "label": f"{p['label']} — a processar", "at": p["at"], "files": 0, "counts": {"finding": 0, "not_assessed": 0}, "reader": None, "seconds": ""})
        return rows

    @web.get("/expedientes", response_class=HTMLResponse)
    def expedientes(request: Request, x_api_key: str | None = Header(default=None)):
        muni = authed(request, x_api_key)
        return HTMLResponse(ui.inbox(listing(muni), muni))

    @web.post("/v1/expedientes/{eid}/trabalho")
    async def trabalho(eid: str, request: Request, x_api_key: str | None = Header(default=None)):
        """The técnico's work state on an expediente: estado (novo | em_analise | convite_enviado | saneado) and responsável; kept in meta.json."""
        muni = authed(request, x_api_key)
        body = await request.json()
        store.reload()
        m = STORE / muni / safe(eid) / "meta.json"
        if not m.exists():
            raise HTTPException(404, "expediente desconhecido")
        meta = json.loads(m.read_text(encoding="utf-8"))
        if "estado" in body:
            if body["estado"] not in dict(ui.STATES):
                raise HTTPException(422, "estado desconhecido")
            meta["estado"] = body["estado"]
        if "responsavel" in body:
            meta["responsavel"] = str(body["responsavel"])[:80]
        meta.setdefault("historico", []).append({"at": datetime.now(timezone.utc).isoformat(timespec="seconds"), **{k: body[k] for k in ("estado", "responsavel") if k in body}})
        m.write_text(json.dumps(meta, ensure_ascii=False), encoding="utf-8")
        store.commit()
        return {"ok": True, "estado": meta.get("estado"), "responsavel": meta.get("responsavel")}

    @web.get("/expedientes/{eid}/", response_class=HTMLResponse)
    def verdict_page(eid: str, request: Request, x_api_key: str | None = Header(default=None)):
        muni = authed(request, x_api_key)
        store.reload()
        base = STORE / muni / safe(eid)
        if (base / "verdict.json").exists():
            return HTMLResponse(ui.app())
        f = base / "verdict.html"
        if f.exists():
            return HTMLResponse(f.read_text(encoding="utf-8"))
        if (base / "pending.json").exists() or (base / "error.json").exists():
            return HTMLResponse(f"""<!doctype html><html lang="pt"><head><meta charset="utf-8"><title>A processar</title>{CSS}<meta http-equiv="refresh" content="10"></head><body>
<h1>Expediente {html.escape(eid)}</h1><p id="estado">a processar… (o leitor pode demorar 2–3 minutos a carregar; esta página atualiza-se sozinha)</p>
<p><a href="/expedientes">← expedientes</a></p><script>fetch('/v1/expedientes/{eid}/estado').then(r=>r.json()).then(j=>{{if(j.estado==='erro')document.getElementById('estado').textContent='erro: '+j.erro}})</script></body></html>""")
        raise HTTPException(404, "expediente desconhecido")

    @web.get("/expedientes/{eid}/{name}")
    def artefact(eid: str, name: str, request: Request, x_api_key: str | None = Header(default=None)):
        muni = authed(request, x_api_key)
        if name not in ("verdict.json", "convite.md", "verdict.html"):
            raise HTTPException(404, "verdict.json, convite.md ou verdict.html")
        store.reload()
        f = STORE / muni / safe(eid) / name
        if not f.exists():
            raise HTTPException(404, "expediente desconhecido")
        media = {"json": "application/json", "md": "text/markdown; charset=utf-8", "html": "text/html; charset=utf-8"}[name.rsplit(".", 1)[1]]
        return Response(f.read_bytes(), media_type=media)

    @web.get("/expedientes/{eid}/ficheiros/{name}")
    def pdf(eid: str, name: str, request: Request, x_api_key: str | None = Header(default=None)):
        muni = authed(request, x_api_key)
        store.reload()
        f = STORE / muni / safe(eid) / "files" / Path(name).name
        if not f.exists():
            raise HTTPException(404, "ficheiro desconhecido")
        return Response(f.read_bytes(), media_type="application/pdf" if f.read_bytes()[:4] == b"%PDF" else "application/octet-stream")

    @web.post("/v1/sessao")
    def session(request: Request, x_api_key: str | None = Header(default=None)):
        authed(request, x_api_key)
        r = JSONResponse({"ok": True})
        r.set_cookie("sk", x_api_key, httponly=True, secure=True, samesite="strict", max_age=12 * 3600)
        return r

    @web.get("/", response_class=HTMLResponse)
    def home():
        return HTMLResponse(HOME)

    @web.get("/lei", response_class=HTMLResponse)
    def lei_page():
        return HTMLResponse(ui.lei())

    LAW_BUDGET = {"n": 0, "hour": 0}

    @web.post("/v1/lei")
    async def lei_ask(request: Request):
        """Public: the question → candidate passages now (code); AMALIA's pick in the background when asked, within a per-hour budget."""
        body = await request.json()
        q = str(body.get("pergunta", "")).strip()[:600]
        if len(q) < 4:
            raise HTTPException(400, "pergunta demasiado curta")
        L = law_search.law()
        cands = L.search(q)
        qid = new_id(q)
        r = {"id": qid, "pergunta": q, "passagens": cands, "escolhida": None, "leitor": None, "at": datetime.now(timezone.utc).isoformat(timespec="seconds")}
        hour = int(time.time() // 3600)
        if LAW_BUDGET["hour"] != hour:
            LAW_BUDGET.update(n=0, hour=hour)
        if body.get("leitor") and cands and LAW_BUDGET["n"] < 40:
            LAW_BUDGET["n"] += 1
            r["leitor"] = "a confirmar"
            d = STORE / "_lei"
            d.mkdir(exist_ok=True)
            (d / f"{qid}.json").write_text(json.dumps(r, ensure_ascii=False), encoding="utf-8")
            store.commit()
            answer_law.spawn(qid)
        elif body.get("leitor") and cands:
            r["leitor"] = "limite horário do leitor atingido; resposta do código"
        return r

    @web.get("/v1/lei/{qid}")
    def lei_status(qid: str):
        store.reload()
        f = STORE / "_lei" / f"{safe(qid)}.json"
        if not f.exists():
            raise HTTPException(404, "pergunta desconhecida")
        return json.loads(f.read_text(encoding="utf-8"))

    def safe(eid):
        if not re.fullmatch(r"[0-9]{8}-[0-9]{6}-[0-9a-f]{6}", eid):
            raise HTTPException(404, "expediente desconhecido")
        return eid

    return web


CSS = """<style>body{font:500 15px/1.45 system-ui,sans-serif;margin:24px auto;max-width:1000px;color:#111;padding:0 16px}table{border-collapse:collapse;width:100%}
td,th{border-bottom:1px solid #ddd;padding:6px 8px;text-align:left}td.bad{color:#a40000;font-weight:700}td.good{color:#0a6b2d;font-weight:700}
input,button{font:inherit;padding:8px 12px}button{background:#111;color:#fff;border:0;border-radius:6px;cursor:pointer}button.alt{background:#555}
#estado{margin-top:16px;font-weight:600}.drop{border:2px dashed #888;border-radius:10px;padding:28px;text-align:center;margin:16px 0}small{color:#333}</style>"""

HOME = f"""<!doctype html><html lang="pt"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Saneamento de expedientes</title>{CSS}</head><body>
<h1>Saneamento de expedientes · Celorico de Basto</h1>
<p>Um expediente de comunicação prévia de obras de edificação (o zip que a plataforma exporta) entra; sai, por elemento do Anexo V da
Portaria n.º 320/2026/1, presente / em falta / não avaliado, com o ficheiro, a página, a citação e o artigo, e o rascunho do convite ao
aperfeiçoamento. <b>O leitor lê, o código decide, o técnico assina.</b> Só expedientes simulados até haver acordo de tratamento de dados.</p>
<p><label>Chave de acesso <input id="chave" type="password" autocomplete="off" placeholder="X-API-Key"></label> <button class="alt" onclick="guardar()">guardar</button> <a href="/expedientes">ver expedientes</a></p>
<div class="drop" id="drop">Largue aqui o zip do expediente, ou <input id="zip" type="file" accept=".zip,application/zip"></div>
<p><button onclick="enviar()">Verificar expediente</button> <label><input type="checkbox" id="semleitor"> sem leitor (só código, segundos)</label></p>
<p>Demonstração com os dossiers do exame (simulados): <button class="alt" onclick="demo('A')">A — completo</button> <button class="alt" onclick="demo('B')">B — dois elementos em falta</button> <button class="alt" onclick="demo('C')">C — seis armadilhas</button></p>
<p id="estado"></p>
<p><small>A verificação corre no servidor; a primeira do dia carrega o leitor (≈ 2–3 minutos), as seguintes demoram segundos. Pode fechar a página e voltar à lista. Nada fica num computador pessoal: ficheiros, leituras e veredictos ficam no volume do serviço.</small></p>
<script>
const $=id=>document.getElementById(id);
try{{$('chave').value=localStorage.getItem('sk')||''}}catch(e){{}}
function chave(){{return $('chave').value.trim()}}
async function guardar(){{try{{localStorage.setItem('sk',chave())}}catch(e){{}} const r=await fetch('/v1/sessao',{{method:'POST',headers:{{'X-API-Key':chave()}}}}); $('estado').textContent=r.ok?'chave guardada':'chave inválida'}}
async function correr(url,body,tipo){{
  if(!chave()){{$('estado').textContent='indique a chave';return}}
  await guardar(); const q=$('semleitor').checked?'?leitor=0':''; const t0=Date.now();
  $('estado').textContent='a verificar… (o leitor pode demorar 2–3 minutos a carregar)'; const tick=setInterval(()=>{{$('estado').textContent='a verificar… '+Math.round((Date.now()-t0)/1000)+' s'}},1000);
  try{{const r=await fetch(url+q,{{method:'POST',headers:Object.assign({{'X-API-Key':chave()}},tipo?{{'Content-Type':tipo}}:{{}}),body}}); clearInterval(tick);
    if(!r.ok){{$('estado').textContent='erro '+r.status+': '+(await r.text());return}} const j=await r.json();
    while(true){{await new Promise(z=>setTimeout(z,4000)); const e=await (await fetch(j.estado_url,{{headers:{{'X-API-Key':chave()}}}})).json();
      if(e.estado==='pronto'){{clearInterval(tick);$('estado').innerHTML='pronto em '+e.seconds+' s: <b>'+e.counts.finding+'</b> deficiência(s), '+e.counts.not_assessed+' não avaliado(s) — <a href="'+e.url+'">abrir veredicto</a>'; location.href=e.url; return}}
      if(e.estado==='erro'){{clearInterval(tick);$('estado').textContent='erro: '+e.erro;return}} }} }}
  catch(e){{clearInterval(tick);$('estado').textContent='erro: '+e}}}}
function enviar(){{const f=$('zip').files[0]; if(!f){{$('estado').textContent='escolha um zip';return}} correr('/v1/expedientes?nome='+encodeURIComponent(f.name),f,'application/zip')}}
function demo(d){{correr('/v1/demo/'+d,null,null)}}
const dz=$('drop'); dz.ondragover=e=>{{e.preventDefault();dz.style.background='#eee'}}; dz.ondragleave=()=>dz.style.background=''; dz.ondrop=e=>{{e.preventDefault();dz.style.background='';$('zip').files=e.dataTransfer.files}};
</script></body></html>"""


@app.function(volumes={"/store": store}, secrets=[modal.Secret.from_name("saneamento-token")], timeout=1800, scaledown_window=300)
@modal.concurrent(max_inputs=8)
@modal.asgi_app()
def web():
    return _app()
