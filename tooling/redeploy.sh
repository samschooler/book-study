#!/usr/bin/env bash
# Step 7: build the Astro site, push to GitHub, and trigger a Coolify deploy.
# Book-agnostic — it rebuilds the whole site (all books in src/data/books/).
#
# Usage:  bash tooling/redeploy.sh "commit message"
#
# Requires ~/repo/skills/coolify-deploy/.env.coolify (COOLIFY_API_URL/TOKEN/DOMAIN).
# The Coolify app uuid for book-study.sam.ink is below; override with APP_UUID=...
set -e
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
APP_UUID="${APP_UUID:-y004o80kccw8w8sos0cog04c}"
MSG="${1:-Update site}"

source ~/repo/skills/coolify-deploy/.env.coolify
BASE="${COOLIFY_API_URL%/}/api/v1"

cd "$ROOT"
npm run build >/tmp/astro-build.log 2>&1 && echo "build OK" || { echo "BUILD FAILED"; tail -20 /tmp/astro-build.log; exit 1; }

git add -A
if git diff --cached --quiet; then
  echo "no changes to commit"
else
  git -c user.name="samschooler" -c user.email="claude.ai@accounts.sam.ink" \
    commit -q -m "$MSG

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
  git push -q origin main && echo "pushed"
fi

DUUID=$(curl -s -H "Authorization: Bearer $COOLIFY_API_TOKEN" "$BASE/deploy?uuid=$APP_UUID" \
  | python3 -c "import sys,json;print(json.load(sys.stdin)['deployments'][0]['deployment_uuid'])")
echo "deployment_uuid=$DUUID"
for i in $(seq 1 45); do
  S=$(curl -s -H "Authorization: Bearer $COOLIFY_API_TOKEN" "$BASE/deployments/$DUUID" \
      | python3 -c "import sys,json;print(json.load(sys.stdin).get('status'))" 2>/dev/null)
  echo "[$i] $S"
  case "$S" in finished) echo DEPLOY_DONE; exit 0;; failed|error|cancelled) echo DEPLOY_FAILED; exit 1;; esac
  sleep 8
done
