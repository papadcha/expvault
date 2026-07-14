#!/bin/bash
# deploy.sh — αντιγράφει τα αρχεία από το ~/Downloads και κάνει push στο git
# Χρήση: ./deploy.sh "μήνυμα commit"
set -euo pipefail

REPO="$HOME/expvault"
DOWNLOADS="$HOME/Downloads"
MSG="${1:-update}"

echo "📁 Αντιγραφή αρχείων..."

FILES=(
  "main.js:$REPO/main.js"
  "preload.js:$REPO/preload.js"
  "bridge.py:$REPO/backend/bridge.py"
  "database.py:$REPO/backend/database.py"
  "exports.py:$REPO/backend/exports.py"
  "pdf_parser.py:$REPO/backend/pdf_parser.py"
  "index.html:$REPO/index.html"
  "package.json:$REPO/package.json"
  "README.md:$REPO/README.md"
)

for entry in "${FILES[@]}"; do
  src="${entry%%:*}"
  dst="${entry#*:}"
  if [ -f "$DOWNLOADS/$src" ]; then
    cp "$DOWNLOADS/$src" "$dst"
    echo "  ✓ $src"
  fi
done

echo ""
echo "📝 Git status:"
cd "$REPO"
git status --short

echo ""
read -p "Συνέχεια με commit '$MSG'; (y/n): " confirm
if [ "$confirm" = "y" ]; then
  git add -A
  git commit -m "$MSG"
  git push
  echo "✅ Έγινε push!"

  echo ""
  echo "🧹 Καθαρισμός Downloads..."
  for entry in "${FILES[@]}"; do
    src="${entry%%:*}"
    if [ -f "$DOWNLOADS/$src" ]; then
      rm "$DOWNLOADS/$src"
      echo "  ✓ $src"
    fi
  done
else
  echo "⏸ Ακυρώθηκε — τα αρχεία αντιγράφηκαν αλλά δεν έγινε commit."
fi
