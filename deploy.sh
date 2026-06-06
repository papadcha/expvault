#!/bin/bash
# deploy.sh — αντιγράφει τα αρχεία από το ~/Downloads και κάνει push στο git
# Χρήση: ./deploy.sh "μήνυμα commit"

REPO="$HOME/expvault"
DOWNLOADS="$HOME/Downloads"
MSG="${1:-update}"

echo "📁 Αντιγραφή αρχείων..."

[ -f "$DOWNLOADS/main.js"       ] && cp "$DOWNLOADS/main.js"       "$REPO/main.js"                          && echo "  ✓ main.js"
[ -f "$DOWNLOADS/preload.js"    ] && cp "$DOWNLOADS/preload.js"     "$REPO/preload.js"                       && echo "  ✓ preload.js"
[ -f "$DOWNLOADS/bridge.py"     ] && cp "$DOWNLOADS/bridge.py"      "$REPO/backend/bridge.py"                && echo "  ✓ bridge.py"
[ -f "$DOWNLOADS/database.py"   ] && cp "$DOWNLOADS/database.py"    "$REPO/backend/database.py"              && echo "  ✓ database.py"
[ -f "$DOWNLOADS/exports.py"    ] && cp "$DOWNLOADS/exports.py"     "$REPO/backend/exports.py"               && echo "  ✓ exports.py"
[ -f "$DOWNLOADS/pdf_parser.py" ] && cp "$DOWNLOADS/pdf_parser.py"  "$REPO/backend/pdf_parser.py"            && echo "  ✓ pdf_parser.py"
[ -f "$DOWNLOADS/index.html"    ] && cp "$DOWNLOADS/index.html"     "$REPO/backend/templates/index.html"     && echo "  ✓ index.html"
[ -f "$DOWNLOADS/package.json"  ] && cp "$DOWNLOADS/package.json"   "$REPO/package.json"                     && echo "  ✓ package.json"
[ -f "$DOWNLOADS/README.md"     ] && cp "$DOWNLOADS/README.md"      "$REPO/README.md"                        && echo "  ✓ README.md"

echo ""
echo "📝 Git status:"
cd "$REPO" && git status --short

echo ""
read -p "Συνέχεια με commit '$MSG'; (y/n): " confirm
if [ "$confirm" = "y" ]; then
  git add -A
  git commit -m "$MSG"
  git push
  echo "✅ Έγινε push!"

  echo ""
  echo "🧹 Καθαρισμός Downloads..."
  for f in main.js preload.js bridge.py database.py exports.py pdf_parser.py \
            index.html package.json README.md; do
    [ -f "$DOWNLOADS/$f" ] && rm "$DOWNLOADS/$f" && echo "  ✓ $f"
  done
else
  echo "⏸ Ακυρώθηκε — τα αρχεία αντιγράφηκαν αλλά δεν έγινε commit."
fi
