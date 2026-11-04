"""Text of a PDF, page by page, with OCR for the pages that have none (scans, image-only covers, drawings with text as pixels).

    from ocr import pages_text
    pages = pages_text("sources/real/wave3/x.pdf")          # list[str], one per page, OCR applied where pypdf found < MIN_CHARS

    python -I generator/ocr.py sources/real                  # report: files, pages without text, what OCR recovered

How: pypdf first. If any page has fewer than MIN_CHARS characters of text, the whole file goes once through `ocrmypdf
--skip-text -l por` (pages that already have text are left alone; only the empty ones get a text layer), the result is
cached under sources/.ocr-cache/<sha256 of the file>.pdf, and the text is read again from the cached copy. No tool
installed → the pypdf text is returned unchanged and `pages_text.last_note` says so. The reader never sees pixels; it sees
the words tesseract read, marked as such in the page block so a technician can tell OCR text from born-digital text.
"""
import hashlib
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CACHE = ROOT / "sources" / ".ocr-cache"
MIN_CHARS = 80
OCR_MARK = "[texto OCR]"


def _pypdf_pages(path):
    from pypdf import PdfReader
    return [(p.extract_text() or "").strip() for p in PdfReader(str(path)).pages]


def tool():
    return shutil.which("ocrmypdf")


def ocr_copy(path):
    """The cached OCR'd copy of path (made with ocrmypdf --skip-text -l por), or None when the tool is missing or fails."""
    path = Path(path)
    if not tool():
        return None
    CACHE.mkdir(parents=True, exist_ok=True)
    out = CACHE / (hashlib.sha256(path.read_bytes()).hexdigest()[:24] + ".pdf")
    if out.exists():
        return out
    r = subprocess.run([tool(), "--skip-text", "-l", "por", "--quiet", str(path), str(out)], capture_output=True, text=True, timeout=1800)
    if r.returncode not in (0, 6):          # 6 = every page already had text (nothing to do); ocrmypdf still writes the output
        pages_text.last_note = f"ocrmypdf failed ({r.returncode}): {r.stderr.strip()[-200:]}"
        return None
    return out if out.exists() else None


def pages_text(path):
    """One string per page; OCR text for the pages pypdf left (almost) empty, each such page prefixed with OCR_MARK."""
    pages_text.last_note = ""
    pages = _pypdf_pages(path)
    empty = [i for i, t in enumerate(pages) if len(t) < MIN_CHARS]
    if not empty:
        return pages
    if not tool():
        pages_text.last_note = f"{len(empty)} page(s) without text; ocrmypdf not installed, returned as is"
        return pages
    copy = ocr_copy(path)
    if copy is None:
        pages_text.last_note = pages_text.last_note or f"{len(empty)} page(s) without text; OCR produced nothing"
        return pages
    ocr = _pypdf_pages(copy)
    got = 0
    for i in empty:
        if i < len(ocr) and len(ocr[i]) >= MIN_CHARS:
            pages[i] = f"{OCR_MARK}\n{ocr[i]}"; got += 1
    pages_text.last_note = f"{len(empty)} page(s) without text; OCR recovered {got}"
    return pages


pages_text.last_note = ""


def report(folder):
    files = sorted(Path(folder).rglob("*.pdf"))
    n_empty = n_got = 0
    for f in files:
        pages = pages_text(f)
        if pages_text.last_note:
            n_empty += int(pages_text.last_note.split()[0])
            if "recovered" in pages_text.last_note:
                n_got += int(pages_text.last_note.split()[-1])
            marks = [i + 1 for i, t in enumerate(pages) if t.startswith(OCR_MARK)]
            sample = next((pages[i - 1][len(OCR_MARK):].strip().replace("\n", " ")[:90] for i in marks), "")
            print(f"{f.relative_to(folder)}: {pages_text.last_note}; pages {marks}; «{sample}»")
    print(f"{len(files)} files; pages without text {n_empty}; recovered by OCR {n_got}; tool: {tool() or 'none'}")


if __name__ == "__main__":
    report(sys.argv[1] if len(sys.argv) > 1 else ROOT / "sources" / "real")
