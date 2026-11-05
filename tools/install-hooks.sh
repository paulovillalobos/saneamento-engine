#!/bin/zsh
# A pre-commit hook that runs tools/check.sh; a red check refuses the commit.
cd "$(dirname "$0")/.."
printf '#!/bin/zsh\nexec tools/check.sh\n' > .git/hooks/pre-commit && chmod +x .git/hooks/pre-commit && echo "pre-commit hook installed"
