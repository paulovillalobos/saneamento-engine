"""LoRA rounds of the saneamento reader: AMALIA-9B-0626-DPO base + an adapter trained on the data sets of the round
(training/data/<set>/train.jsonl, written by generator/*.py from the law and the generated expedientes; no model answer inside).
Copied from ccp-engine/training/train_lora.py; only the app, the volume, the rounds and the system prompt are ours.

    ~/Downloads/foaap-core/.venv-modal/bin/modal run modal/train_lora.py --run r1

Mixture (proportional per task, capped): every train example of every task, except escolha_passagem, which is cut to at
most the sum of the other tasks (so it is never more than 50 % of the mix); the cut is deterministic (sha256 of the
example id). Format: chat, the reader's system prompt (readers/leitor_a_modal.py SYSTEM), the example's prompt as the
user turn, its answer (compact JSON) as the assistant turn; the loss is on the answer tokens only and the vocabulary
projection is applied only at those positions. Micro-batches of length-sorted examples (<= TOKENS_PER_BATCH tokens with
padding), gradient accumulation to EFFECTIVE_BATCH examples, AdamW, linear warm-up then linear decay, bf16, gradient
checkpointing, LoRA r=16 / alpha 32 / dropout 0.05 on every projection (q, k, v, o, gate, up, down).

Writes the adapter to the Modal volume amalia-saneamento-lora as amalia-saneamento-<run> (never touches any other adapter there) and
training/runs/<run>/MANIFEST.json here: sha256 of training/data/INDEX.json, the mixture, the hyper-parameters, the repo
commit, start and end instants, the loss log, the adapter files' sha256 and the Modal app id (the cost in USD is read
from Modal's billing report afterwards: training/runs/<run>/COST.json, `modal billing report`).
"""
import hashlib
import json
import subprocess
import time
from pathlib import Path

import modal

MODEL = "amalia-llm/AMALIA-9B-0626-DPO"
REVISION = "c4614b9b5c7b4fe303fa20902e692fc7dface640"
SYSTEM = ("És o leitor de saneamento de expedientes urbanísticos de um município português. Respondes só com o objeto JSON pedido, "
          "sem texto antes nem depois. Toda a citação é copiada letra a letra da lei; se não sabes, respondes {\"resposta\": \"nao_sei\"}.")  # = modal/reader.py SYSTEM
ADAPTER = "amalia-saneamento-r1"
# rounds (docs/DECISIONS.md D4): each round retrains from the base on the cumulative mix of the sets it names; sealed/ never enters
RUNS = {"r1": {"adapter": "amalia-saneamento-r1", "data": ["training/data"], "sets": ["d0"], "repeat": {}},   # D0 v1 (10 % passages held out: measured memorisation of unseen text = nothing)
        "r1b": {"adapter": "amalia-saneamento-r1b", "data": ["training/data"], "sets": ["d0"], "repeat": {}},  # D0 v2: every passage, held-out phrasings, nao_sei probes
        "r2": {"adapter": "amalia-saneamento-r2", "data": ["training/data"], "sets": ["d0", "d1", "d2"], "repeat": {}},   # cumulative from the start: r1 showed D0 alone raises invented facts on D2
        "r3": {"adapter": "amalia-saneamento-r3", "data": ["training/data"], "sets": ["d0", "d1", "d2"], "repeat": {"d2": 2}},
        "r4": {"adapter": "amalia-saneamento-r4", "data": ["training/data"], "sets": ["d0", "d1", "d2"], "repeat": {}},
        "r5": {"adapter": "amalia-saneamento-r5", "data": ["training/data"], "sets": ["d0", "d1", "d2"], "repeat": {}},   # r5: memórias with cover+index / ofício-reply headers, minuta preamble on termos, one-word-per-line augmentation (stranger failures of r4)
        "r6": {"adapter": "amalia-saneamento-r6", "data": ["training/data"], "sets": ["d0", "d1", "d2"], "repeat": {}}}   # r6: file names made uninformative on 40 % of D1 rows + 50 % of augmented rows (probe showed the reader decided by the name)   # D0 v4 (scope, rule, no base_legal), D1 v3 (long memórias, new noise, augmentation), 80 expedientes
HP = {"lora_r": 16, "lora_alpha": 32, "lora_dropout": 0.05, "target_modules": ["q_proj", "k_proj", "v_proj", "o_proj", "gate_proj", "up_proj", "down_proj"],
      "epochs": 2, "lr": 1e-4, "warmup_steps": 20, "effective_batch": 16, "tokens_per_batch": 24000, "max_len": 8192,
      "optimizer": "AdamW (weight_decay 0)", "schedule": "linear warm-up, linear decay to 0", "precision": "bf16", "grad_clip": 1.0, "seed": 0,
      "gpu": "H100"}
ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "training/data"

image = (modal.Image.from_registry("nvidia/cuda:12.9.1-devel-ubuntu22.04", add_python="3.12")
         .pip_install("vllm==0.30.0", "huggingface_hub[hf_transfer]", "peft==0.21.2")
         .env({"HF_HUB_ENABLE_HF_TRANSFER": "1", "VLLM_USE_FLASHINFER_SAMPLER": "0"}))
weights = modal.Volume.from_name("amalia-weights", create_if_missing=True)
adapters = modal.Volume.from_name("amalia-saneamento-lora", create_if_missing=True)
app = modal.App("saneamento-train", image=image)


def mixture(run="r1"):
    by_task = {}
    for d in RUNS[run]["data"]:
        for f in sorted((ROOT / d).glob("*/train.jsonl")):
            if f.parent.name not in RUNS[run]["sets"]:
                continue
            rows = [json.loads(l) for l in f.read_text(encoding="utf-8").splitlines() if l.strip()]
            by_task[f.parent.name] = rows * RUNS[run]["repeat"].get(f.parent.name, 1)
    mix = [{"id": r["id"], "task": r["task"], "prompt": r["prompt"], "answer": r["answer"]} for k in sorted(by_task) for r in by_task[k]]
    return mix, {k: len(v) for k, v in sorted(by_task.items())}


@app.function(gpu="H100", volumes={"/weights": weights, "/lora": adapters}, timeout=6 * 3600)
def train_remote(rows: list[dict], hp: dict, adapter: str = ADAPTER) -> dict:
    import math
    import random

    import torch
    from huggingface_hub import snapshot_download
    from peft import LoraConfig, get_peft_model
    from transformers import AutoModelForCausalLM, AutoTokenizer

    out_dir = Path("/lora") / adapter
    if out_dir.exists():
        raise SystemExit(f"{out_dir} exists: an adapter is never overwritten")
    path = snapshot_download(MODEL, revision=REVISION, cache_dir="/weights")
    tok = AutoTokenizer.from_pretrained(path)
    pad = tok.pad_token_id if tok.pad_token_id is not None else tok.eos_token_id
    examples, dropped = [], 0
    for r in rows:
        head = [{"role": "system", "content": SYSTEM}, {"role": "user", "content": r["prompt"]}]
        p_txt = tok.apply_chat_template(head, add_generation_prompt=True, tokenize=False)
        f_txt = tok.apply_chat_template(head + [{"role": "assistant", "content": r["answer"]}], tokenize=False)
        if not f_txt.startswith(p_txt):
            dropped += 1
            continue
        p_ids = tok(p_txt, add_special_tokens=False)["input_ids"]
        a_ids = tok(f_txt[len(p_txt):], add_special_tokens=False)["input_ids"]
        if len(p_ids) + len(a_ids) > hp["max_len"]:
            dropped += 1
            continue
        examples.append((p_ids + a_ids, len(p_ids)))
    if len(examples) < 0.95 * len(rows):
        raise SystemExit(f"{len(rows) - len(examples)} of {len(rows)} examples dropped")
    total_tokens = sum(len(e[0]) for e in examples)

    def batches(seed):
        r = random.Random(seed)
        order = sorted(range(len(examples)), key=lambda i: (len(examples[i][0]), r.random()))
        out, cur, cur_max = [], [], 0
        for i in order:
            n = len(examples[i][0])
            if cur and max(cur_max, n) * (len(cur) + 1) > hp["tokens_per_batch"]:
                out.append(cur); cur, cur_max = [], 0
            cur.append(i); cur_max = max(cur_max, n)
        if cur:
            out.append(cur)
        r.shuffle(out)
        return out

    model = AutoModelForCausalLM.from_pretrained(path, torch_dtype=torch.bfloat16, attn_implementation="sdpa").cuda()
    model.config.use_cache = False
    model.gradient_checkpointing_enable(gradient_checkpointing_kwargs={"use_reentrant": False})
    model.enable_input_require_grads()
    model = get_peft_model(model, LoraConfig(r=hp["lora_r"], lora_alpha=hp["lora_alpha"], lora_dropout=hp["lora_dropout"],
                                             task_type="CAUSAL_LM", target_modules=hp["target_modules"]))
    trainable = sum(p.numel() for p in model.parameters() if p.requires_grad)
    inner = model.base_model.model
    torch.manual_seed(hp["seed"])
    epochs = [batches(hp["seed"] + e) for e in range(hp["epochs"])]
    steps = math.ceil(sum(len(b) for ep in epochs for b in ep) / hp["effective_batch"])
    opt = torch.optim.AdamW([p for p in model.parameters() if p.requires_grad], lr=hp["lr"], weight_decay=0.0)
    sched = torch.optim.lr_scheduler.LambdaLR(opt, lambda s: min(1.0, (s + 1) / hp["warmup_steps"]) * max(0.0, 1 - s / steps))
    model.train()
    log, t0, seen, run_loss, run_n, step = [], time.time(), 0, 0.0, 0, 0
    for ep, ep_batches in enumerate(epochs):
        for b in ep_batches:
            L = max(len(examples[i][0]) for i in b)
            ids = torch.full((len(b), L), pad, dtype=torch.long)
            att = torch.zeros((len(b), L), dtype=torch.long)
            sel = torch.zeros((len(b), L), dtype=torch.bool)  # positions whose next token is an answer token
            for row, i in enumerate(b):
                seq, plen = examples[i]
                ids[row, :len(seq)] = torch.tensor(seq)
                att[row, :len(seq)] = 1
                sel[row, plen - 1:len(seq) - 1] = True
            ids, att, sel = ids.cuda(), att.cuda(), sel.cuda()
            hidden = inner.model(input_ids=ids, attention_mask=att).last_hidden_state
            logits = inner.lm_head(hidden[sel]).float()
            targets = ids[:, 1:][sel[:, :-1]]
            loss = torch.nn.functional.cross_entropy(logits, targets)
            (loss * len(b) / hp["effective_batch"]).backward()
            run_loss += loss.item() * len(b); run_n += len(b); seen += len(b)
            if run_n >= hp["effective_batch"]:
                torch.nn.utils.clip_grad_norm_(model.parameters(), hp["grad_clip"])
                opt.step(); sched.step(); opt.zero_grad(set_to_none=True); step += 1
                if step % 10 == 0 or step == 1:
                    log.append({"step": step, "epoch": ep + 1, "loss": round(run_loss / run_n, 4), "seen": seen, "seconds": round(time.time() - t0, 1)})
                    print(log[-1], flush=True)
                if step % 100 == 0:  # checkpoint: r6 died at step 1010/1017 before the final save ("Runner terminated"), 3.4 h lost
                    model.save_pretrained(str(out_dir)); adapters.commit()
                    print({"checkpoint": step}, flush=True)
                run_loss, run_n = 0.0, 0
    if run_n:
        torch.nn.utils.clip_grad_norm_(model.parameters(), hp["grad_clip"])
        opt.step(); opt.zero_grad(set_to_none=True); step += 1
    model.save_pretrained(str(out_dir))
    files = {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(out_dir.iterdir()) if p.is_file()}
    adapters.commit()
    return {"examples": len(examples), "dropped": dropped, "tokens": total_tokens, "trainable_params": trainable, "steps": step,
            "seconds": round(time.time() - t0, 1), "log": log, "adapter_files": files}


@app.local_entrypoint()
def main(run: str = "r1"):
    out = ROOT / "training/runs" / run
    if (out / "MANIFEST.json").exists():
        raise SystemExit(f"{out}/MANIFEST.json exists: a run is never redone in place")
    rows, mix = mixture(run)
    adapter = RUNS[run]["adapter"]
    indexes = {st: hashlib.sha256((DATA / st / "train.jsonl").read_bytes()).hexdigest() for st in RUNS[run]["sets"]}
    commit = subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT, capture_output=True, text=True).stdout.strip()
    dirty = bool(subprocess.run(["git", "status", "--porcelain", "training/data", "law", "generator"], cwd=ROOT, capture_output=True, text=True).stdout.strip())
    started = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    hp = {**HP, **RUNS[run].get("hp", {})}  # a run may change hyper-parameters (D53: rank 64)
    call = train_remote.spawn(rows, hp, adapter)
    print("modal function call", call.object_id, flush=True)
    res = call.get()
    finished = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    out.mkdir(parents=True, exist_ok=True)
    manifest = {"adapter": adapter, "volume": "amalia-saneamento-lora", "base": {"model": MODEL, "revision": REVISION},
                "sets": RUNS[run]["sets"], "set_sha256": indexes,
                "repeat": RUNS[run]["repeat"], "mixture": mix, "examples_in_mix": len(rows),
                "hyperparameters": hp, "repo_commit": commit, "repo_dirty_training_or_law": dirty, "started": started, "finished": finished,
                "modal_app": app.app_id, "modal_function_call": call.object_id, "result": res, "cost_usd": "see COST.json (modal billing report)"}
    (out / "MANIFEST.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(json.dumps({k: v for k, v in manifest.items() if k != "result"}, indent=1))
    print({k: v for k, v in res.items() if k != "log"})
