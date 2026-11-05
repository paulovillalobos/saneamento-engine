#!/bin/zsh
# Everything that must be green before a commit: the scaffold's tests, the engine's unit and acceptance tests (exam replayed from the
# stored reads; the sealed set when its PDFs are on this machine), and the two scorers printed for the record.
#   tools/check.sh            (PY=… to pick the interpreter; needs pypdf)
set -eo pipefail
cd "$(dirname "$0")/.."
PY=${PY:-/Users/baphomet/Downloads/rjue-engine/.venv/bin/python}
[ -x "$PY" ] || PY=python3
echo "== scaffold tests";  "$PY" -I generator/test_guard.py
echo "== engine tests";    "$PY" -I -m unittest discover -s tests -t . -q
echo "== exam";            "$PY" -I exam/score.py | tail -1
echo "== sealed";          "$PY" -I engine/score_sealed.py | tail -1
echo "CHECK OK"
