# Ceiling reader — instructions for one batch

You are the reader in a measurement. Each prompt file under `prompts/` is a complete task in Portuguese: a question, a document
(every page, marked `[página n]`), and the exact JSON shape the answer must have. Your batch is one list of ids in `batches.json`.

For every id in your batch:

1. Read `prompts/<id with ":" replaced by "-">.txt` in full.
2. Answer the task yourself, from the document text only, exactly in the JSON shape the prompt asks for. One JSON object, nothing else.
   - `d1_elemento` prompts: `{"elemento": <id from the printed list or null>, "citacao": <that list line's text, letter by letter, or "">, "tipo": <"escrito" | "desenhado" | "nao_e_elemento" | "ilegivel">}`.
     The file IS the element only when it is the instructing piece itself (the memória, the termo, the planta, the estimativa…), not a document about it, a form, a norm, a list, a guide or an opinion. Follow the rules written in the prompt.
   - `d2_facto` prompts: `{"valor": <the exact text as it appears in the document or null>, "pagina": <the page number where it appears or null>, "citacao": <the line of that page where it appears, copied exactly, or "">}`.
     If the document does not state it, `valor` null, `pagina` null, `citacao` "". Never compute, convert or infer a value; copy it as printed. Only the page where the copied text actually is.
3. Write the answer to `raw/<id with ":" replaced by "-">.json` as `{"text": "<the JSON object as a string>"}`.

Rules:
- Read only files under `prompts/`, plus `batches.json`. Do not open any other file in this repository (there are answer keys elsewhere; the measurement is void if they are seen).
- Do not use subagents, the web, or any tool other than Read and Write.
- Do not skip a prompt because it is long. The point of the measurement is reading the whole document.
- Answer every prompt in your batch, then report: how many files you wrote, and the ids of any you could not answer.
