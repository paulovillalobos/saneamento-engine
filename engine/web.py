"""The hosted service's pure parts (D23): id and path rules, the zip intake, the listing, the work state, the reader's hourly budget.
No Modal, no FastAPI here, so tests run them with the standard library. modal/service.py is the thin HTTP layer over these.
"""
import hashlib
import io
import json
import re
import time
import zipfile
from datetime import datetime, timezone
from pathlib import Path

ID = re.compile(r"[0-9]{8}-[0-9]{6}-[0-9a-f]{6}")
NAME = re.compile(r"[\w .()\-–]+")
MAX_FILE = 60 * 1024 * 1024


def new_id(seed):
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    return f"{stamp}-{hashlib.sha256(f'{seed}{time.time()}'.encode()).hexdigest()[:6]}"


def safe_id(eid):
    """An expediente or question id as the service minted it, else None (never a path)."""
    return eid if ID.fullmatch(eid or "") else None


def unzip_to(data, files_dir):
    """The zip's files, flattened to their base names, into files_dir; hidden, macOS and oversize entries and odd names are skipped.
    Returns the count written. Raises zipfile.BadZipFile."""
    files_dir = Path(files_dir)
    files_dir.mkdir(parents=True, exist_ok=True)
    n = 0
    with zipfile.ZipFile(io.BytesIO(data)) as z:
        for info in z.infolist():
            name = Path(info.filename).name
            if info.is_dir() or not name or name.startswith(".") or "__MACOSX" in info.filename or info.file_size > MAX_FILE or not NAME.fullmatch(name):
                continue
            (files_dir / name).write_bytes(z.read(info))
            n += 1
    return n


def listing(root):
    """One row per expediente folder under root, newest first: meta.json when done, else the error or the pending marker."""
    rows = []
    root = Path(root)
    if not root.is_dir():
        return rows
    for d in sorted(root.iterdir(), reverse=True):
        if (d / "meta.json").exists():
            rows.append(json.loads((d / "meta.json").read_text(encoding="utf-8")))
        elif (d / "error.json").exists():
            e = json.loads((d / "error.json").read_text(encoding="utf-8"))
            rows.append({"id": d.name, "label": f"ERRO — {e['erro'][:60]}", "at": e["at"], "files": 0, "counts": {"finding": 0, "not_assessed": 0}, "reader": None, "seconds": "", "estado": "erro"})
        elif (d / "pending.json").exists():
            p = json.loads((d / "pending.json").read_text(encoding="utf-8"))
            rows.append({"id": d.name, "label": f"{p['label']} — a processar", "at": p["at"], "files": 0, "counts": {"finding": 0, "not_assessed": 0}, "reader": None, "seconds": "", "estado": "a_processar"})
    return rows


def status_of(base):
    base = Path(base)
    if (base / "meta.json").exists():
        meta = json.loads((base / "meta.json").read_text(encoding="utf-8"))
        return {**meta, "trabalho": meta.get("estado"), "estado": "pronto"}  # the processing state wins the key; the work state moves to «trabalho»
    if (base / "error.json").exists():
        return {"estado": "erro", **json.loads((base / "error.json").read_text(encoding="utf-8"))}
    if (base / "pending.json").exists():
        return {"estado": "a processar", **json.loads((base / "pending.json").read_text(encoding="utf-8"))}
    return None


def set_work(meta_path, body, states):
    """The técnico's work state on an expediente (estado, responsável) into meta.json, with a dated history. Returns the meta or
    raises ValueError on an unknown state."""
    meta_path = Path(meta_path)
    meta = json.loads(meta_path.read_text(encoding="utf-8"))
    if "estado" in body:
        if body["estado"] not in dict(states):
            raise ValueError("estado desconhecido")
        meta["estado"] = body["estado"]
    if "responsavel" in body:
        meta["responsavel"] = str(body["responsavel"])[:80]
    meta.setdefault("historico", []).append({"at": datetime.now(timezone.utc).isoformat(timespec="seconds"), **{k: body[k] for k in ("estado", "responsavel") if k in body}})
    meta_path.write_text(json.dumps(meta, ensure_ascii=False), encoding="utf-8")
    return meta


def take_budget(dir_path, limit, now=None):
    """One unit of the reader's hourly budget from a counter file in the shared volume (one file per hour, all containers see it).
    True when granted."""
    dir_path = Path(dir_path)
    dir_path.mkdir(parents=True, exist_ok=True)
    hour = int((now or time.time()) // 3600)
    f = dir_path / f"budget-{hour}.json"
    n = json.loads(f.read_text(encoding="utf-8"))["n"] if f.exists() else 0
    if n >= limit:
        return False
    f.write_text(json.dumps({"n": n + 1}), encoding="utf-8")
    return True
