---
name: run-expvault
description: Launch and drive the ExpVault Electron desktop app (dev or installed build) for visual verification — screenshot a screen, click through the UI, read back rendered text. Use when asked to run ExpVault, check a UI fix on screen, or confirm a change works in the real app.
---

Το ExpVault είναι Electron app σε πραγματικά Windows (όχι headless/xvfb —
τρέχει με πραγματική οθόνη), οπότε ο driver είναι ένα απλό one-shot script
πάνω σε `playwright-core`'s `_electron`, όχι REPL μέσα σε tmux.

## Χρήση

```bash
node .claude/skills/run-expvault/driver.mjs dev|installed '<JSON array εντολών>'
```

- `dev` — ανοίγει από το repo (`node_modules/electron` + `.`), χρησιμοποιεί
  τη dev βάση (`backend/expvault.db`).
- `installed` — ανοίγει το πραγματικό `C:\Program Files\ExpVault\ExpVault.exe`,
  χρησιμοποιεί την πραγματική βάση χρήστη (`%APPDATA%\expvault\expvault.db`).
  Οποιαδήποτε αλλαγή δεδομένων εδώ είναι ΠΡΑΓΜΑΤΙΚΗ — καθάρισε ό,τι test
  δεδομένα προσθέσεις (βλ. παράδειγμα Ελέγχου Άδειας παρακάτω, `set_adeia_katigoria`
  αλλά με reversible actions· generic πρόσθεσε/διάγραψε μέσω `add_*`/`delete_*`).

Κάθε εντολή στο array: `{"cmd":"<name>","args":<οτιδήποτε>}`, εκτελούνται
σειριακά, το αποτέλεσμα κάθε μιας τυπώνεται σε NDJSON.

### Εντολές

| εντολή | τι κάνει |
|---|---|
| `launch` | ανοίγει την εφαρμογή, περιμένει ~2s |
| `nav <data-page>` | κλικ στο sidebar item — `adeies`, `kiniseis`, `apothemata`, `ylika`, `promitheftes`, `backup`, κλπ. (βλ. `data-page` attributes στο index.html) |
| `click <css-sel>` | DOM click μέσω evaluate (όχι coordinates) |
| `click-text <text>` | κλικ σε button/a/nav-item που περιέχει το text |
| `wait <css-sel>` | περιμένει μέχρι 10s να εμφανιστεί το selector |
| `eval <js-expr>` | page.evaluate, τυπώνει το JSON αποτέλεσμα |
| `text [css-sel]` | innerText του selector (ή όλου του body) |
| `ss [name]` | screenshot → `.claude/skills/run-expvault/shots/<name>.png` (gitignored) |
| `quit` | κλείνει την εφαρμογή |

### Παράδειγμα — έλεγχος οθόνης Άδειες στην εγκατεστημένη εφαρμογή

```bash
node .claude/skills/run-expvault/driver.mjs installed '[
  {"cmd":"launch"},
  {"cmd":"nav","args":"adeies"},
  {"cmd":"wait","args":"#adeia-body tr"},
  {"cmd":"eval","args":"[...document.querySelectorAll(\"#adeia-body tr\")].find(tr=>tr.textContent.includes(\"40935\"))?.click()"},
  {"cmd":"ss","args":"adeies-40935"},
  {"cmd":"eval","args":"document.getElementById(\"adeia-ylika-body\").innerText"},
  {"cmd":"quit"}
]'
```

## Gotchas

- **Race condition μετά από `nav`:** τα δεδομένα κάθε σελίδας φορτώνονται
  ασύγχρονα μέσω IPC (`py()` στο index.html) αφού γίνει το SPA navigation.
  Ένα `eval` που ψάχνει σε πίνακα (π.χ. `#adeia-body tr`) αμέσως μετά το
  `nav` συχνά βρίσκει άδειο πίνακα. Πάντα `wait` για ένα selector μέσα
  στον πίνακα πριν κάνεις click/eval πάνω του.
- **`installed` mode αλλάζει πραγματικά δεδομένα.** Δεν υπάρχει sandbox
  DB όπως στο `scripts/smoke-test-bridge.mjs` — αν κάνεις add/set/delete
  για δοκιμή, καθάρισέ το στο ίδιο session (matching `add_*` → `delete_*`).
- **CDP/remote-debugging όχι απαραίτητο.** Νωρίτερα (2026-07-11) έγινε
  χειροκίνητα raw WebSocket σε CDP endpoint (`--remote-debugging-port`)
  επειδή δεν υπήρχε αυτό το driver· τώρα το `_electron.launch()` της
  playwright-core καλύπτει το ίδιο χωρίς χειροκίνητο port management.
