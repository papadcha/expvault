// Guards against the class of bug behind bridge.exe v1.0.4: bridge.spec's
// PyInstaller `excludes` silently drops a package a bundled dependency
// actually needs (PIL, required by reportlab 5.x), or a code path has a
// NameError that only fires at runtime — both invisible to `pip`/`node`
// and to a plain "does it launch" check. This spawns the freshly-built
// bridge.exe exactly like main.js does, against a throwaway fresh DB
// (also exercises the new-install migration path), and fires the exact
// commands that broke last time: Greek round-trip via stdin, and every
// document-export format. Run after PyInstaller, before packaging.
import { spawn } from 'node:child_process';
import { mkdtempSync, rmSync, existsSync, statSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join } from 'node:path';

const BRIDGE_EXE = process.argv[2] || join(import.meta.dirname, '..', 'backend', 'dist', 'bridge', 'bridge.exe');

if (!existsSync(BRIDGE_EXE)) {
  console.error(`smoke-test-bridge: δεν βρέθηκε το bridge.exe στο ${BRIDGE_EXE}`);
  process.exit(1);
}

const dataDir = mkdtempSync(join(tmpdir(), 'expvault-smoke-'));
const outDir  = mkdtempSync(join(tmpdir(), 'expvault-smoke-out-'));

const proc = spawn(BRIDGE_EXE, [], {
  stdio: ['pipe', 'pipe', 'pipe'],
  env: { ...process.env, EXPVAULT_DATA_DIR: dataDir },
});

let buffer = '';
const pending = new Map();
let reqId = 1;
let readyResolve;
const readyPromise = new Promise((r) => { readyResolve = r; });

let stderrBuf = '';
proc.stderr.on('data', (d) => { stderrBuf += d.toString('utf8'); });

proc.stdout.on('data', (data) => {
  buffer += data.toString('utf8');
  let idx;
  while ((idx = buffer.indexOf('\n')) >= 0) {
    const line = buffer.slice(0, idx).trim();
    buffer = buffer.slice(idx + 1);
    if (!line) continue;
    const msg = JSON.parse(line);
    if (msg.ready) { readyResolve(); continue; }
    const p = pending.get(msg.id);
    if (p) { pending.delete(msg.id); p(msg); }
  }
});

function call(cmd, payload = {}) {
  return new Promise((resolve, reject) => {
    const id = reqId++;
    pending.set(id, resolve);
    proc.stdin.write(JSON.stringify({ id, cmd, payload }) + '\n');
    setTimeout(() => { if (pending.has(id)) { pending.delete(id); reject(new Error(`timeout: ${cmd}`)); } }, 10_000);
  });
}

const failures = [];
function check(label, cond) {
  if (!cond) failures.push(label);
  console.log(`  ${cond ? 'OK  ' : 'FAIL'} ${label}`);
}

try {
  const bootTimeout = setTimeout(() => { throw new Error('bridge δεν έστειλε {"ready":true} μέσα σε 10s — δες stderr:\n' + stderrBuf); }, 10_000);
  await readyPromise;
  clearTimeout(bootTimeout);
  console.log('bridge ready (νέα, άδεια βάση — δοκιμή του migration path σε "νέα εγκατάσταση")');

  // 1. Βασικό read σε άδεια βάση — πιάνει crashes στο migration path.
  const ylika = await call('get_ylika');
  check('get_ylika σε νέα βάση', !ylika.error);

  // 2. Ελληνικό round-trip μέσω stdin — bug: αλλοιωμένο κείμενο (cp1252 misdecode).
  const GREEK = 'ΔΟΚΙΜΗ Ζελατοδυναμίτιδα ΧΑΛΚΙΔΙΚΗΣ — Ωμέγα';
  const add = await call('add_promitheftis', { onoma: GREEK, syntomografia: 'SMOKE' });
  check('add_promitheftis (ελληνικό κείμενο)', !add.error);
  const proms = await call('get_promitheftes');
  const found = proms.result?.find((p) => p.syntomografia === 'SMOKE');
  check('ελληνικό κείμενο round-trip χωρίς αλλοίωση', found?.onoma === GREEK);
  if (found) await call('delete_promitheftis', { id: found.id });

  // 3. Κάθε μορφή εξαγωγής εγγράφου — bug: ModuleNotFoundError / NameError
  //    μόνο στο packaged exe, αόρατο σε dev mode ή σε static analysis.
  const exportChecks = [
    ['export_excel', 'x.xlsx'],
    ['export_docx', 'x.docx'],
    ['export_lista_agores', 'x.pdf'],
    ['export_deltio_drastiriotitas_excel', 'x-deltio.xlsx'],
    ['export_deltio_drastiriotitas_pdf', 'x-deltio.pdf'],
  ];
  for (const [cmd, fname] of exportChecks) {
    const out_path = join(outDir, fname);
    const r = await call(cmd, { out_path });
    const ok = !r.error && existsSync(out_path) && statSync(out_path).size > 0;
    check(`${cmd} παράγει έγκυρο αρχείο`, ok);
    if (r.error) console.log(`       error: ${r.error}`);
  }
} catch (e) {
  console.error('smoke-test-bridge: εξαίρεση:', e.message);
  failures.push(e.message);
} finally {
  proc.kill();
  rmSync(dataDir, { recursive: true, force: true });
  rmSync(outDir, { recursive: true, force: true });
}

if (failures.length > 0) {
  console.error(`\nsmoke-test-bridge: ${failures.length} αποτυχία/ες — το bridge.exe ΔΕΝ είναι έτοιμο για installer:`);
  for (const f of failures) console.error(`  - ${f}`);
  process.exit(1);
}
console.log('\nsmoke-test-bridge: όλοι οι έλεγχοι πέρασαν.');
