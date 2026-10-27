"""AMALIA-9B-0626-DPO as the saneamento reader on Modal: base model or base + a LoRA adapter from the volume
amalia-saneamento-lora, vLLM, temperature 0, guided JSON with one schema per task.

    modal run modal/reader.py --jsonl sealed/d0-test.jsonl --out training/runs/base/d0.json [--lora r1] [--limit N]

Rows are {id, task, prompt, answer}; the answer is the key and is never sent. Output: a JSON list, first item = meta,
then {key, task, prompt_tokens, completion_tokens, finish_reason, text}. Prompts that do not fit the window are skipped, never cut.
"""
import json
from pathlib import Path

import modal

MODEL = "amalia-llm/AMALIA-9B-0626-DPO"
REVISION = "c4614b9b5c7b4fe303fa20902e692fc7dface640"
WINDOW, MAX_TOKENS = 32768, 1200
SYSTEM = ("És o leitor de saneamento de expedientes urbanísticos de um município português. Respondes só com o objeto JSON pedido, "
          "sem texto antes nem depois. Toda a citação é copiada letra a letra da lei; se não sabes, respondes {\"resposta\": \"nao_sei\"}.")
S = {"type": "string"}
SCHEMAS = {
    "transcreve": {"type": "object", "properties": {"passagem": S, "citacao": S}, "required": ["passagem", "citacao"], "additionalProperties": False},
    "localiza": {"type": "object", "properties": {"passagem": S, "citacao": S}, "required": ["passagem", "citacao"], "additionalProperties": False},
    "alinea_de": {"type": "object", "properties": {"passagem": S, "citacao": S}, "required": ["passagem", "citacao"], "additionalProperties": False},
    "elemento_doc": {"type": "object", "properties": {"passagem": S, "citacao": S, "tipo": {"enum": ["obrigatorio", "condicional", "facultativo", "previsto", "sem_base", "em_falta", "proibido", "sem_veredicto"]}, "base_legal": S},
                     "required": ["passagem", "citacao", "tipo", "base_legal"], "additionalProperties": False},
    "exigencia": {"type": "object", "properties": {"exigido": {"enum": ["sempre", "condicional", "nao"]}, "condicao": S, "passagem": S, "citacao": S, "nota": S},
                  "required": ["exigido", "condicao", "passagem", "citacao"], "additionalProperties": False},
    "proibido": {"type": "object", "properties": {"resposta": {"enum": ["sim", "nao"]}, "passagem": S, "citacao": S}, "required": ["resposta", "passagem", "citacao"], "additionalProperties": False},
    "d1_elemento": {"type": "object", "properties": {"elemento": {"type": ["string", "null"]}, "citacao": S, "tipo": {"enum": ["escrito", "desenhado", "nao_e_elemento", "ilegivel"]}},
                    "required": ["elemento", "citacao", "tipo"], "additionalProperties": False},
    "d2_facto": {"type": "object", "properties": {"valor": {"type": ["string", "null"]}, "pagina": {"type": ["integer", "null"]}, "citacao": S},
                 "required": ["valor", "pagina", "citacao"], "additionalProperties": False},
}
image = (modal.Image.from_registry("nvidia/cuda:12.9.1-devel-ubuntu22.04", add_python="3.12")
         .pip_install("vllm==0.30.0", "huggingface_hub[hf_transfer]").env({"HF_HUB_ENABLE_HF_TRANSFER": "1", "VLLM_USE_FLASHINFER_SAMPLER": "0"}))
weights = modal.Volume.from_name("amalia-weights", create_if_missing=True)
adapters = modal.Volume.from_name("amalia-saneamento-lora", create_if_missing=True)
app = modal.App("saneamento-reader", image=image)


@app.function(gpu="L40S", volumes={"/weights": weights, "/lora": adapters}, timeout=3600)
def answer(prompts: list[dict], lora: str = "") -> list[dict]:
    import time
    from huggingface_hub import snapshot_download
    from vllm import LLM, SamplingParams
    from vllm.sampling_params import StructuredOutputsParams
    t0 = time.time()
    path = snapshot_download(MODEL, revision=REVISION, cache_dir="/weights")
    extra = {"enable_lora": True, "max_lora_rank": 16} if lora else {}
    llm = LLM(model=path, max_model_len=WINDOW, enable_prefix_caching=True, gpu_memory_utilization=0.92, seed=0, **extra)
    tok = llm.get_tokenizer()
    request = None
    if lora:
        from vllm.lora.request import LoRARequest
        adapter = Path("/lora") / f"amalia-saneamento-{lora}"
        if not adapter.exists():
            raise SystemExit(f"{adapter} missing in the volume amalia-saneamento-lora")
        request = LoRARequest(f"amalia-saneamento-{lora}", 1, str(adapter))
    load_s = round(time.time() - t0, 1)
    keep, out = [], []
    for p in prompts:
        msgs = [{"role": "system", "content": SYSTEM}, {"role": "user", "content": p["prompt"]}]
        n = len(tok.apply_chat_template(msgs, add_generation_prompt=True, tokenize=True))
        if n + MAX_TOKENS > WINDOW:
            out.append({"key": p["key"], "task": p["task"], "skipped": "window", "prompt_tokens": n})
        else:
            keep.append((p, msgs, n))
    t1 = time.time()
    params = [SamplingParams(temperature=0.0, max_tokens=MAX_TOKENS, seed=0, structured_outputs=StructuredOutputsParams(json=SCHEMAS[k[0]["task"]], disable_any_whitespace=True)) for k in keep]
    res = llm.chat([k[1] for k in keep], params, use_tqdm=False, lora_request=request)
    gen_s = round(time.time() - t1, 1)
    for (p, _, n), r in zip(keep, res):
        o = r.outputs[0]
        out.append({"key": p["key"], "task": p["task"], "prompt_tokens": n, "completion_tokens": len(o.token_ids), "finish_reason": o.finish_reason, "text": o.text})
    meta = {"model": f"{MODEL}@{REVISION[:12]}", "adapter": f"amalia-saneamento-{lora}" if lora else None, "runtime": "vllm 0.30.0, bf16, L40S, prefix caching, guided JSON per task",
            "temperature": 0, "max_tokens": MAX_TOKENS, "load_seconds": load_s, "generate_seconds": gen_s, "answered": len(keep), "skipped": len(prompts) - len(keep)}
    return [{"meta": meta}] + out


@app.local_entrypoint()
def main(jsonl: str, out: str, lora: str = "", limit: int = 0):
    rows = [json.loads(l) for l in open(jsonl, encoding="utf-8") if l.strip()]
    if limit:
        rows = rows[:limit]
    items = [{"key": r["id"], "task": r["task"], "prompt": r["prompt"]} for r in rows]
    result = answer.remote(items, lora)
    Path(out).parent.mkdir(parents=True, exist_ok=True)
    json.dump(result, open(out, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(json.dumps(result[0], indent=1, ensure_ascii=False))
