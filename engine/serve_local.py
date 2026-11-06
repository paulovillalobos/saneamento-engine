"""The service on localhost, for Safari (D24): the same screens and routes as modal/service.py, standard library HTTP, no key
(bound to 127.0.0.1 only), the expedientes and questions stored under engine/store_local/. The reader is the deployed Modal
function when the Modal client and token are on this machine (saneamento-reader must be deployed); without them every
verification runs code-only and the law page answers from the code alone.

    .venv-modal/bin/python -I engine/serve_local.py [--port 5340]        then open http://127.0.0.1:5340/

Routes: / (inbox)  /?novo=1 (intake)  /lei  /expedientes  /expedientes/<id>/  …/verdict.json  …/convite.md  …/ficheiros/<name>
        POST /v1/expedientes (zip)  POST /v1/demo/{A|B|C}  GET /v1/expedientes  GET /v1/expedientes/<id>/estado
        POST /v1/expedientes/<id>/trabalho  POST /v1/lei  GET /v1/lei/<id>  GET /v1/saude
Processing runs in a thread per expediente so the page can poll, exactly as on Modal.
"""
import argparse
import html
import json
import shutil
import sys
import threading
import traceback
import zipfile
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, unquote, urlsplit

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "generator"))
from engine import application as A  # noqa: E402
from engine import law_search, read as R, ui, web as W  # noqa: E402

STORE = ROOT / "engine" / "store_local"
MUNI = "celorico-de-basto"
LORA = "r11"
def reader():
    try:
        import modal
        return modal.Function.from_name("saneamento-reader", "answer")
    except Exception:
        return None


def process(eid, use_reader, label):
    base = STORE / MUNI / eid
    files = base / "files"
    try:
        reads = None
        fn = reader() if use_reader else None
        if fn is not None:
            reads = R.read_with(files, LORA, lambda items, lora, guard: fn.remote(items, lora, guard))
            (base / "reads").mkdir(exist_ok=True)
            (base / "reads" / "prompts.jsonl").write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in reads["prompt_rows"]), encoding="utf-8")
            (base / "reads" / "answers-checked.json").write_text(json.dumps(reads["checked"], ensure_ascii=False), encoding="utf-8")
        v = A.verdict(files, reads if reads is not None else {"meta": None, "rows": {}, "answers": {}})
        v["id"], v["municipality"], v["label"] = eid, MUNI, label
        v["seconds"] = 0
        (base / "verdict.json").write_text(json.dumps(v, ensure_ascii=False, indent=1), encoding="utf-8")
        (base / "convite.md").write_text(A.convite(v), encoding="utf-8")
        (base / "meta.json").write_text(json.dumps({"id": eid, "municipality": MUNI, "label": label, "at": v["checked_at"], "counts": v["counts"], "files": len(v["files"]),
                                                     "reader": (v.get("reader") or {}).get("adapter"), "seconds": v["seconds"], "estado": "novo"}, ensure_ascii=False), encoding="utf-8")
        (base / "pending.json").unlink(missing_ok=True)
    except Exception as e:
        traceback.print_exc()
        (base / "error.json").write_text(json.dumps({"id": eid, "erro": f"{type(e).__name__}: {e}"[:500], "at": A.datetime.now(A.timezone.utc).isoformat(timespec="seconds")}, ensure_ascii=False), encoding="utf-8")


def answer_law(qid):
    f = STORE / "_lei" / f"{qid}.json"
    r = json.loads(f.read_text(encoding="utf-8"))
    try:
        fn = reader()
        if fn is None:
            r["leitor"] = "sem leitor nesta máquina (resposta do código)"
        else:
            L = law_search.law()
            out = fn.remote([{"key": qid, "task": "exigencia", "prompt": L.prompt(r["pergunta"], r["passagens"])}], LORA, False)
            text = next((o.get("text") for o in out[1:] if o.get("key") == qid), None)
            pick, why = L.check(text, r["passagens"]) if text else (None, "sem resposta")
            r["escolhida"], r["leitor"] = pick, "confirmada" if pick else f"sem confirmação ({why})"
    except Exception as e:
        r["leitor"] = f"erro do leitor ({type(e).__name__})"
    f.write_text(json.dumps(r, ensure_ascii=False), encoding="utf-8")


class H(BaseHTTPRequestHandler):
    def send(self, code, body, ctype="text/html; charset=utf-8"):
        data = body if isinstance(body, bytes) else body.encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def js(self, code, obj):
        self.send(code, json.dumps(obj, ensure_ascii=False), "application/json")

    def log_message(self, fmt, *args):
        sys.stderr.write("%s %s\n" % (self.command, self.path))

    def do_GET(self):
        u = urlsplit(self.path)
        p = u.path
        if p == "/" and parse_qs(u.query).get("novo") == ["1"]:
            return self.send(200, ui.home(local=True))
        if p == "/lei":
            return self.send(200, ui.lei())
        if p == "/v1/saude":
            return self.js(200, {"ok": True, "leitor": f"amalia-saneamento-{LORA}", "municipio": MUNI, "local": True})
        if p in ("/", "/expedientes"):
            return self.send(200, ui.inbox())
        if p == "/v1/expedientes":
            return self.js(200, {"municipio": MUNI, "expedientes": W.listing(STORE / MUNI)})
        parts = p.strip("/").split("/")
        if parts[:1] == ["expedientes"] and len(parts) >= 2 and W.safe_id(parts[1]):
            base = STORE / MUNI / parts[1]
            if len(parts) == 2:
                if (base / "verdict.json").exists():
                    return self.send(200, ui.app())
                if (base / "error.json").exists():
                    return self.send(200, f'<!doctype html><meta charset="utf-8"><pre style="margin:40px">{html.escape((base / "error.json").read_text(encoding="utf-8"))}</pre>')
                if (base / "pending.json").exists():
                    return self.send(200, f'<!doctype html><meta charset="utf-8"><meta http-equiv="refresh" content="8"><p style="font:600 18px system-ui;margin:40px">a processar… (o leitor pode demorar 2–3 minutos a carregar; esta página atualiza-se)</p><p style="margin:0 40px"><a href="/expedientes">← expedientes</a></p>')
            if len(parts) == 3 and parts[2] in ("verdict.json", "convite.md") and (base / parts[2]).exists():
                return self.send(200, (base / parts[2]).read_bytes(), "application/json" if parts[2].endswith("json") else "text/markdown; charset=utf-8")
            if len(parts) == 4 and parts[2] == "ficheiros":
                f = base / "files" / Path(unquote(parts[3])).name
                if f.exists():
                    return self.send(200, f.read_bytes(), "application/pdf" if f.read_bytes()[:4] == b"%PDF" else "application/octet-stream")
        if parts[:2] == ["v1", "expedientes"] and len(parts) == 4 and parts[3] == "estado" and W.safe_id(parts[2]):
            st = W.status_of(STORE / MUNI / parts[2])
            return self.js(200, {**st, "url": f"/expedientes/{parts[2]}/"} if st and st["estado"] == "pronto" else (st or {"estado": "desconhecido"}))
        if parts[:2] == ["v1", "lei"] and len(parts) == 3 and W.safe_id(parts[2]):
            f = STORE / "_lei" / f"{parts[2]}.json"
            return self.js(200, json.loads(f.read_text(encoding="utf-8"))) if f.exists() else self.js(404, {"erro": "pergunta desconhecida"})
        return self.send(404, "<p>404</p>")

    def do_POST(self):
        u = urlsplit(self.path)
        q = parse_qs(u.query)
        p = u.path
        length = int(self.headers.get("Content-Length", "0"))
        body = self.rfile.read(length) if length else b""
        parts = p.strip("/").split("/")
        if p == "/v1/sessao":
            return self.js(200, {"ok": True})
        if p == "/v1/lei":
            try:
                b = json.loads(body or b"{}")
            except json.JSONDecodeError:
                return self.js(400, {"erro": "JSON inválido"})
            qs = str(b.get("pergunta", "")).strip()[:600]
            if len(qs) < 4:
                return self.js(400, {"erro": "pergunta demasiado curta"})
            cands = law_search.law().search(qs)
            qid = W.new_id(qs)
            r = {"id": qid, "pergunta": qs, "passagens": cands, "escolhida": None, "leitor": None}
            if b.get("leitor") and cands:
                r["leitor"] = "a confirmar"
                (STORE / "_lei").mkdir(parents=True, exist_ok=True)
                (STORE / "_lei" / f"{qid}.json").write_text(json.dumps(r, ensure_ascii=False), encoding="utf-8")
                threading.Thread(target=answer_law, args=(qid,), daemon=True).start()
            return self.js(200, r)
        if parts[:2] == ["v1", "demo"] and len(parts) == 3 and parts[2] in ("A", "B", "C"):
            eid = W.new_id(parts[2])
            base = STORE / MUNI / eid
            shutil.copytree(ROOT / "exam" / "dossiers" / parts[2], base / "files")
            return self.start(eid, q.get("leitor", ["1"])[0] != "0", f"exame {parts[2]} (simulado)")
        if p == "/v1/expedientes":
            label = q.get("nome", ["expediente"])[0]
            eid = W.new_id(label)
            base = STORE / MUNI / eid
            try:
                n = W.unzip_to(body, base / "files")
            except zipfile.BadZipFile:
                shutil.rmtree(base, ignore_errors=True)
                return self.js(400, {"erro": "o corpo não é um zip"})
            if n == 0:
                shutil.rmtree(base, ignore_errors=True)
                return self.js(400, {"erro": "zip sem ficheiros"})
            return self.start(eid, q.get("leitor", ["1"])[0] != "0", label, n)
        if parts[:2] == ["v1", "expedientes"] and len(parts) == 4 and parts[3] == "trabalho" and W.safe_id(parts[2]):
            m = STORE / MUNI / parts[2] / "meta.json"
            if not m.exists():
                return self.js(404, {"erro": "expediente desconhecido"})
            try:
                meta = W.set_work(m, json.loads(body or b"{}"), ui.STATES)
            except ValueError as e:
                return self.js(422, {"erro": str(e)})
            return self.js(200, {"ok": True, "estado": meta.get("estado"), "responsavel": meta.get("responsavel")})
        return self.send(404, "<p>404</p>")

    def start(self, eid, use_reader, label, n=None):
        base = STORE / MUNI / eid
        (base / "pending.json").write_text(json.dumps({"id": eid, "label": label, "at": A.datetime.now(A.timezone.utc).isoformat(timespec="seconds"), "leitor": use_reader}), encoding="utf-8")
        threading.Thread(target=process, args=(eid, use_reader, label), daemon=True).start()
        out = {"id": eid, "url": f"/expedientes/{eid}/", "estado": "a processar", "estado_url": f"/v1/expedientes/{eid}/estado"}
        if n is not None:
            out["ficheiros"] = n
        return self.js(200, out)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", type=int, default=5340)
    a = ap.parse_args()
    (STORE / MUNI).mkdir(parents=True, exist_ok=True)
    srv = ThreadingHTTPServer(("127.0.0.1", a.port), H)
    print(f"saneamento-engine local: http://127.0.0.1:{a.port}/  (store {STORE}, reader {'modal' if reader() else 'none, code-only'})", flush=True)
    srv.serve_forever()


if __name__ == "__main__":
    main()
