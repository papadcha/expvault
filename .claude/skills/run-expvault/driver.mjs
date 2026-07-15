// Driver για launch + έλεγχο του ExpVault Electron app, χωρίς tmux/xvfb —
// τρέχει σαν ένα one-shot script πάνω σε πραγματικά Windows με οθόνη
// (matches το πρόχειρο raw-CDP πείραμα που έγινε στο χέρι στις 2026-07-11
// για να επιβεβαιωθεί ένα encoding fix, τυποποιημένο εδώ ώστε να μην
// ξαναγραφτεί από την αρχή).
//
// Usage:
//   node driver.mjs dev|installed '<JSON array εντολών>'
//
// Κάθε εντολή: {"cmd":"<name>","args":<οτιδήποτε>}. Εκτελούνται σειριακά,
// το αποτέλεσμα κάθε μιας τυπώνεται σε NDJSON στο stdout.
//
// Διαθέσιμες εντολές:
//   launch                 — ανοίγει την εφαρμογή (dev: node_modules/electron
//                             + repo dir· installed: το πραγματικό .exe)
//   nav <data-page>        — κλικ στο sidebar item με το αντίστοιχο data-page
//                             (π.χ. "adeies", "kiniseis", "apothemata")
//   click <css-sel>        — DOM click μέσω evaluate (όχι coordinates)
//   click-text <text>      — κλικ σε button/a που περιέχει το text
//   ss <name>              — screenshot -> SHOT_DIR/<name>.png
//   eval <js-expr>         — page.evaluate, τυπώνει το JSON αποτέλεσμα
//   text <css-sel>         — innerText του selector (ή του body)
//   wait <css-sel>         — περιμένει μέχρι 10s να εμφανιστεί
//   quit                   — κλείνει την εφαρμογή
//
// Παράδειγμα — έλεγχος της οθόνης Άδειες στην εγκατεστημένη εφαρμογή:
//   node driver.mjs installed '[{"cmd":"launch"},{"cmd":"nav","args":"adeies"},{"cmd":"ss","args":"adeies"},{"cmd":"quit"}]'

import { _electron as electron } from 'playwright-core';
import * as fs from 'node:fs';
import * as path from 'node:path';

const APP_DIR = path.resolve(import.meta.dirname, '..', '..', '..');
const SHOT_DIR = process.env.SCREENSHOT_DIR || path.join(APP_DIR, '.claude', 'skills', 'run-expvault', 'shots');
fs.mkdirSync(SHOT_DIR, { recursive: true });

const [, , mode, actionsJson] = process.argv;
if (!mode || !actionsJson) {
  console.error('Usage: node driver.mjs dev|installed \'<JSON array εντολών>\'');
  process.exit(1);
}
const actions = JSON.parse(actionsJson);

let app = null;
let page = null;

async function launch() {
  if (mode === 'installed') {
    const exePath = 'C:/Program Files/ExpVault/ExpVault.exe';
    if (!fs.existsSync(exePath)) throw new Error(`δεν βρέθηκε: ${exePath}`);
    app = await electron.launch({ executablePath: exePath, args: [], timeout: 30_000 });
  } else {
    const electronBin = path.join(APP_DIR, 'node_modules', 'electron', 'dist', 'electron.exe');
    app = await electron.launch({ executablePath: electronBin, args: [APP_DIR], timeout: 30_000 });
  }
  await new Promise((r) => setTimeout(r, 2_000));
  // Το splash window (splash.html, ειδοποίηση λήξης άδειας) ανοίγει παράλληλα
  // με το κύριο παράθυρο και μπορεί να είναι πρώτο στη λίστα — αγνόησέ το.
  page = app.windows().find((w) => w.url().includes('index.html'))
    ?? app.windows().find((w) => !w.url().startsWith('devtools://') && !w.url().includes('splash.html'))
    ?? await app.firstWindow();
  return { windows: app.windows().length };
}

const RUN = {
  async launch() { return launch(); },

  async nav(dataPage) {
    if (!page) throw new Error('launch πρώτα');
    return page.evaluate((dp) => {
      const el = document.querySelector(`.nav-item[data-page="${dp}"]`);
      if (!el) return 'NOT_FOUND';
      el.click();
      return 'OK';
    }, dataPage);
  },

  async click(sel) {
    if (!page) throw new Error('launch πρώτα');
    return page.evaluate((s) => {
      const el = document.querySelector(s);
      if (!el) return 'NOT_FOUND';
      el.click();
      return 'OK';
    }, sel);
  },

  async 'click-text'(text) {
    if (!page) throw new Error('launch πρώτα');
    return page.evaluate((t) => {
      const els = [...document.querySelectorAll('button, a, [role="button"], .nav-item')];
      const el = els.find((e) => e.textContent?.trim() === t) ?? els.find((e) => e.textContent?.includes(t));
      if (!el) return 'NOT_FOUND';
      el.click();
      return 'OK: ' + el.tagName;
    }, text);
  },

  async ss(name) {
    if (!page) throw new Error('launch πρώτα');
    const f = path.join(SHOT_DIR, (name || `ss-${Date.now()}`) + '.png');
    await page.screenshot({ path: f });
    return f;
  },

  async eval(expr) {
    if (!page) throw new Error('launch πρώτα');
    return page.evaluate(expr);
  },

  async text(sel) {
    if (!page) throw new Error('launch πρώτα');
    return page.evaluate((s) => (s ? document.querySelector(s) : document.body)?.innerText ?? null, sel || null);
  },

  async wait(sel) {
    if (!page) throw new Error('launch πρώτα');
    try { await page.waitForSelector(sel, { timeout: 10_000 }); return 'found'; }
    catch { return 'TIMEOUT'; }
  },

  async quit() {
    if (app) await app.close().catch(() => {});
    app = null; page = null;
    return 'OK';
  },
};

for (const { cmd, args } of actions) {
  const fn = RUN[cmd];
  if (!fn) {
    console.log(JSON.stringify({ cmd, error: `unknown command: ${cmd}` }));
    continue;
  }
  try {
    const result = await fn(args);
    console.log(JSON.stringify({ cmd, args, result }));
  } catch (e) {
    console.log(JSON.stringify({ cmd, args, error: e.message }));
  }
}

if (app) await RUN.quit();
