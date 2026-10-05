#!/usr/bin/env bash
# Render a week's graphics, commit, push, and print verified raw URLs (pinned to the commit).
# Usage: tools/publish.sh spec.json
set -euo pipefail
cd "$(dirname "$0")/.."
SPEC="$1"
WEEK=$(python3 -c "import json,sys;print(json.load(open('$SPEC'))['week'])")
python3 tools/render.py "$SPEC" > /tmp/rendered.txt
cp "$SPEC" "weekly/$WEEK/spec.json"
git add "weekly/$WEEK"
git diff --cached --quiet || git commit -qm "Social graphics for week of $WEEK"
GIT_TERMINAL_PROMPT=0 git push -q origin main 2>&1 | sed 's/github_pat_[A-Za-z0-9_]*/[redacted]/g'
SHA=$(git rev-parse HEAD)
while read -r f; do
  url="https://raw.githubusercontent.com/ForeSiteSolutions/social-assets/$SHA/$f"
  code=$(curl -s -o /dev/null -w "%{http_code}" "$url")
  echo "$code $url"
done < /tmp/rendered.txt
