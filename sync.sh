#!/bin/bash
set -euo pipefail

echo "🔄 Auto-syncing project with GitHub..."

# Remove stale lock files if they exist
rm -f .git/index.lock .git/config.lock

# Set git identity via environment variables
export GIT_AUTHOR_NAME="Replit Bot"
export GIT_AUTHOR_EMAIL="replit-bot@replit.com"
export GIT_COMMITTER_NAME="Replit Bot"
export GIT_COMMITTER_EMAIL="replit-bot@replit.com"

git pull origin main --allow-unrelated-histories

git add .

# Attempt commit and handle "nothing to commit" gracefully
if git commit -m "auto-sync from Replit on $(date '+%Y-%m-%d %H:%M:%S')"; then
  echo "Changes committed successfully."
else
  # Check if it's because there are no changes
  if git diff-index --quiet HEAD --; then
    echo "No changes to commit."
  else
    echo "❌ Commit failed with error"
    exit 1
  fi
fi

git push origin main
echo "✅ GitHub sync complete."
