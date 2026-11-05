"""The reader with GPU memory snapshots (D25), on Modal's own vLLM pattern: `vllm serve` as a subprocess with sleep mode, warmed
up and put to sleep before the snapshot, woken up after the restore. Same model, revision, adapter, sampling and guard as
modal/reader.py; the service calls `Reader.answer` exactly as before. Deployed as app «saneamento-reader-warm».

    modal deploy modal/reader_warm.py            # snapshots work only on a deployed app; the speed-up appears after a few cold starts

Why a subprocess: the in-process LLM object spawns vLLM's engine in a child process that a snapshot does not carry; the served
model with --enable-sleep-mode is what Modal snapshots (docs/examples/lfm_snapshot). LoRA fixed per deployment (SANEAMENTO_LORA).
"""
import json
import os
import subprocess
import sys
import time
from pathlib import Path

import modal

MODEL = "amalia-llm/AMALIA-9B-0626-DPO"
REVISION = "c4614b9b5c7b4fe303fa20902e692fc7dface640"
WINDOW, MAX_TOKENS, PORT = 32768, 1200, 8000
LORA = os.environ.get("SANEAMENTO_LORA", "r11")
SCALEDOWN = int(os.environ.get("SANEAMENTO_SCALEDOWN", "600"))
SYSTEM = ("És o leitor de saneamento de expedientes urbanísticos de um município português. Respondes só com o objeto JSON pedido, "
          "sem texto antes nem depois. Toda a citação é copiada letra a letra da lei; se não sabes, respondes {\"resposta\": \"nao_sei\"}.")
S = {"type": "string"}
SCHEMAS = {
    "transcreve": {"type": "object", "properties": {"passagem": S, "citacao": S}, "required": ["passagem", "citacao"], "additionalProperties": False},
    "localiza": {"type": "object", "properties": {"passagem": S, "citacao": S}, "required": ["passagem", "citacao"], "additionalProperties": False},
    "alinea_de": {"type": "object", "properties": {"passagem": S, "citacao": S}, "required": ["passagem", "citacao"], "additionalProperties": False},
    "elemento_doc": {"type": "object", "properties": {"passagem": S, "citacao": S, "tipo": {"enum": ["obrigatorio", "condicional", "facultativo", "previsto", "sem_base", "em_falta", "proibido", "sem_veredicto"]}},
                     "required": ["passagem", "citacao", "tipo"], "additionalProperties": False},
    "exigencia": {"type": "object", "properties": {"exigido": {"enum": ["sempre", "condicional", "nao"]}, "condicao": S, "passagem": S, "citacao": S, "nota": S},
                  "required": ["exigido", "condicao", "passagem", "citacao"], "additionalProperties": False},
    "proibido": {"type": "object", "properties": {"resposta": {"enum": ["sim", "nao"]}, "passagem": S, "citacao": S}, "required": ["resposta", "passagem", "citacao"], "additionalProperties": False},
    "d1_elemento": {"type": "object", "properties": {"elemento": {"type": ["string", "null"]}, "citacao": S, "tipo": {"enum": ["escrito", "desenhado", "nao_e_elemento", "ilegivel"]}},
                    "required": ["elemento", "citacao", "tipo"], "additionalProperties": False},
    "d2_facto": {"type": "object", "properties": {"valor": {"type": ["string", "null"]}, "pagina": {"type": ["integer", "null"]}, "citacao": S},
                 "required": ["valor", "pagina", "citacao"], "additionalProperties": False},
}
NS = {"type": "object", "properties": {"resposta": {"enum": ["nao_sei"]}}, "required": ["resposta"], "additionalProperties": False}
for _t in ("transcreve", "localiza", "alinea_de", "elemento_doc", "exigencia", "proibido"):
    SCHEMAS[_t] = {"anyOf": [SCHEMAS[_t], NS]}

image = (modal.Image.from_registry("nvidia/cuda:12.9.1-devel-ubuntu22.04", add_python="3.12")
         .pip_install("vllm==0.30.0", "huggingface_hub[hf_transfer]", "requests")
         .env({"HF_HUB_ENABLE_HF_TRANSFER": "1", "VLLM_USE_FLASHINFER_SAMPLER": "0", "VLLM_SERVER_DEV_MODE": "1", "SANEAMENTO_LORA": LORA}))
weights = modal.Volume.from_name("amalia-weights", create_if_missing=True)
adapters = modal.Volume.from_name("amalia-saneamento-lora", create_if_missing=True)
app = modal.App("saneamento-reader-warm", image=image)

with image.imports():
    import requests


def _wait_ready(proc, timeout=900):
    deadline = time.time() + timeout
    while time.time() < deadline:
        if proc.poll() is not None:
            raise RuntimeError(f"vllm serve exited with {proc.returncode}")
        try:
            requests.get(f"http://127.0.0.1:{PORT}/health").raise_for_status()
            return
        except (requests.exceptions.ConnectionError, requests.exceptions.HTTPError):
            time.sleep(3)
    raise TimeoutError("vLLM server not ready")


def _chat(prompt, extra, model):
    body = {"model": model, "messages": [{"role": "system", "content": SYSTEM}, {"role": "user", "content": prompt}], "max_tokens": MAX_TOKENS, "temperature": 0, "seed": 0}
    body.update(extra)
    r = requests.post(f"http://127.0.0.1:{PORT}/v1/chat/completions", json=body, timeout=600)
    r.raise_for_status()
    return r.json()


@app.cls(gpu="L40S", volumes={"/weights": weights, "/lora": adapters}, timeout=3600, scaledown_window=SCALEDOWN, startup_timeout=900,
         enable_memory_snapshot=True, experimental_options={"enable_gpu_snapshot": True})
class Reader:
    @modal.enter(snap=True)
    def startup(self):
        from huggingface_hub import snapshot_download
        t0 = time.time()
        path = snapshot_download(MODEL, revision=REVISION, cache_dir="/weights")
        adapter = Path("/lora") / f"amalia-saneamento-{LORA}"
        if not adapter.exists():
            raise SystemExit(f"{adapter} missing in the volume amalia-saneamento-lora")
        cmd = ["vllm", "serve", path, "--served-model-name", "llm", "--host", "127.0.0.1", "--port", str(PORT), "--dtype", "bfloat16",
               "--max-model-len", str(WINDOW), "--gpu-memory-utilization", "0.9", "--enable-prefix-caching", "--seed", "0",
               "--enable-lora", "--max-lora-rank", "16", "--lora-modules", f"amalia-saneamento-{LORA}={adapter}",
               "--structured-outputs-config", json.dumps({"backend": "xgrammar", "disable_any_whitespace": False}), "--enable-sleep-mode"]
        print(*cmd, flush=True)
        self.proc = subprocess.Popen(cmd)
        _wait_ready(self.proc)
        for _ in range(3):
            _chat("Responde {\"resposta\": \"nao_sei\"}.", {"structured_outputs": {"json": NS}}, f"amalia-saneamento-{LORA}")
        requests.post(f"http://127.0.0.1:{PORT}/sleep?level=1").raise_for_status()
        self.load_seconds = round(time.time() - t0, 1)

    @modal.enter(snap=False)
    def restore(self):
        t0 = time.time()
        requests.post(f"http://127.0.0.1:{PORT}/wake_up").raise_for_status()
        self.wake_seconds = round(time.time() - t0, 1)

    @modal.exit()
    def stop(self):
        self.proc.terminate()

    @modal.method()
    def answer(self, prompts: list[dict], lora: str = "", guard: bool = False) -> list[dict]:
        if lora and lora != LORA:
            raise ValueError(f"this reader carries {LORA}; asked for {lora}")
        model = f"amalia-saneamento-{LORA}"
        t1 = time.time()
        from concurrent.futures import ThreadPoolExecutor

        def one(p):
            extra = {"structured_outputs": {"grammar": p["grammar"]}} if p.get("grammar") else {"structured_outputs": {"json": SCHEMAS[p["task"]]}}
            try:
                r = _chat(p["prompt"], extra, model)
            except requests.exceptions.HTTPError as e:
                if e.response is not None and e.response.status_code == 400 and "maximum context length" in e.response.text:
                    return {"key": p["key"], "task": p["task"], "skipped": "window"}
                raise
            c = r["choices"][0]
            return {"key": p["key"], "task": p["task"], "prompt_tokens": r["usage"]["prompt_tokens"], "completion_tokens": r["usage"]["completion_tokens"],
                    "finish_reason": c["finish_reason"], "text": c["message"]["content"]}
        with ThreadPoolExecutor(max_workers=16) as ex:   # vLLM batches concurrent requests; one at a time was ≈ 2 s a prompt
            out = list(ex.map(one, prompts))
        meta = {"model": f"{MODEL}@{REVISION[:12]}", "adapter": model, "runtime": "vllm 0.30.0 serve, bf16, L40S, prefix caching, sleep mode + GPU snapshot, guided JSON per task",
                "temperature": 0, "max_tokens": MAX_TOKENS, "guard": "grammar" if guard else None, "load_seconds": self.load_seconds, "wake_seconds": getattr(self, "wake_seconds", None),
                "generate_seconds": round(time.time() - t1, 1), "answered": sum(1 for o in out if "text" in o), "skipped": sum(1 for o in out if "skipped" in o)}
        return [{"meta": meta}] + out
