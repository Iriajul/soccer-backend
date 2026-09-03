#!/bin/bash
# Commit everything and push main → GitHub Actions tests then deploys to the VPS.
# Usage: ./ship.sh "your commit message"
set -e

GREEN='\033[0;32m'; YELLOW='\033[1;33m'; NC='\033[0m'
log()  { echo -e "${GREEN}✓ $1${NC}"; }
warn() { echo -e "${YELLOW}→ $1${NC}"; }

MSG="$1"
if [ -z "$MSG" ]; then
    echo -e "${YELLOW}Usage: ./ship.sh \"your commit message\"${NC}"
    exit 1
fi

CURRENT=$(git branch --show-current)
if [ "$CURRENT" != "main" ]; then
    warn "Switching to main..."
    git checkout main
fi

warn "Staging changes..."
git add .

if git diff --cached --quiet; then
    warn "Nothing to commit — pushing existing commits..."
else
    warn "Committing: $MSG"
    git commit -m "$MSG"
fi

warn "Pushing main..."
git push origin main
log "Pushed. GitHub Actions is testing then deploying to the VPS now."
