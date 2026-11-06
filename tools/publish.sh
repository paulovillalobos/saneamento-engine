#!/bin/zsh
# Publish this repository to GitHub as the public copy: a fresh clone with the two things GitHub refuses or we never publish removed
# from history (the 112 MB plain d1 training set; the exam's test private keys) and neutral commit messages, force-pushed to
# paulovillalobos/saneamento-engine. The working repository's history is never rewritten; run tools/check.sh first (the pre-commit
# hook already does). Needs git-filter-repo in the Modal venv and the gh CLI logged in.
#   tools/publish.sh
set -eo pipefail
cd "$(dirname "$0")/.."
FR=/Users/baphomet/Downloads/foaap-core/.venv-modal/bin/git-filter-repo
OUT=${TMPDIR:-/tmp}/saneamento-engine-public-$$
git clone -q --no-local . "$OUT"
cd "$OUT"
printf 'Claude Opus 5.5 reads the 106 stranger rows whole==>A large general-purpose model reads the 106 stranger rows whole\nClaude Opus 5.5==>a general-purpose model\nClaude Opus==>a general-purpose model\nclaude-opus-5.5==>the reviewer\nCodex==>the second reviewer\n' > /tmp/replace-messages-$$.txt
"$FR" --path training/data/d1/train.jsonl --path-glob 'exam/pki/*.key' --invert-paths --replace-message /tmp/replace-messages-$$.txt --force >/dev/null
big=$(git rev-list --objects --all | git cat-file --batch-check='%(objecttype) %(objectsize)' | awk '$1=="blob" && $2>100000000' | wc -l | tr -d ' ')
names=$(git grep -i -w 'claude\|opus\|codex\|fable\|anthropic\|chatgpt\|openai' -- ':!*.pdf' ':!*.jsonl' ':!*.gz' ':!*.pem' | wc -l | tr -d ' ')
msgs=$(git log --format='%s%n%b' | grep -ci 'claude\|opus\|codex\|fable\|anthropic' || true)
[ "$big" = 0 ] && [ "$names" = 0 ] && [ "$msgs" = 0 ] || { echo "refused: blobs>100MB=$big names=$names messages=$msgs"; exit 1; }
git remote add origin https://github.com/paulovillalobos/saneamento-engine.git
git branch -M main
git push --force origin main
echo "published $(git rev-parse --short HEAD) ($(git log --oneline | wc -l | tr -d ' ') commits) → https://github.com/paulovillalobos/saneamento-engine"
rm -rf "$OUT" /tmp/replace-messages-$$.txt
