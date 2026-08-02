// version-check.js — δύο ΞΕΧΩΡΙΣΤΟΥΣ update-check μηχανισμούς, ένα ανά γραμμή
// προϊόντος (βλ. IS_MAIN_LINE, ελέγχει το package.json's name):
//
// - checkVersionNotice() — η γραμμή main/v1.x. Διαβάζει allowed-versions.json
//   από το branch `main`. Παράλληλο, ανεξάρτητο μηχανισμό από το
//   setupAutoUpdater() του main.js (electron-updater / GitHub releases API) —
//   καλύπτει κάτι που το electron-updater δεν ξέρει: "αυτή η έκδοση έχει
//   γνωστό πρόβλημα, μέχρι ποια μπορείς να κάνεις ασφαλές downgrade". ΠΡΟΣΟΧΗ:
//   αν οριστεί notice/χαμηλώσει το latestRecommendedVersion επειδή ένα release
//   αποδείχτηκε προβληματικό, αυτό ΜΟΝΟ ΤΟΥ δεν εμποδίζει το electron-updater
//   να συνεχίσει να κατεβάζει/εγκαθιστά αυτόματα το ίδιο (χαλασμένο) release σε
//   όσους δεν έχουν ενημερωθεί ακόμα — πρέπει ΕΠΙΣΗΣ να γίνει unpublish/draft
//   το ίδιο το GitHub release.
//
// - checkForUpdatesV2() — η γραμμή v2 (ExpVault+). Διαβάζει
//   allowed-versions-v2.json από το branch `v2` (ΟΧΙ `main` — έτσι δεν
//   χρειάζεται να αγγίξουμε το main branch για να έχει το ExpVault+ το δικό
//   του manifest). Δεν χρησιμοποιεί καθόλου electron-updater/GitHub Releases
//   API matching — αντίθετα από το main.js's setupAutoUpdater(), που κοιτάζει
//   "ό,τι το GitHub λέει *latest* σε αυτό το repo" χωρίς να ξέρει τίποτα για
//   appId, άρα δεν είναι ασφαλές να δημοσιευτεί ποτέ ένα πραγματικό ExpVault+
//   GitHub release όσο υπάρχουν v1.x installs με ενεργό setupAutoUpdater() —
//   αυτό ΔΕΝ το λύνει το checkForUpdatesV2() από μόνο του, βλ. συζήτηση.
//   Ίδιο proven-in-production μοτίβο με το lab-galatista's modules/update-check.js
//   (εκεί σε ESM/net.request· εδώ σε CommonJS/https+net, ίδια συμπεριφορά):
//   background auto-download του installer, αλλά ΠΟΤΕ silent auto-install —
//   το τρέξιμο του .exe παραμένει πάντα χειροκίνητο κλικ του χρήστη.
const https = require('https');
const fs = require('fs');
const os = require('os');
const path = require('path');
const { app, ipcMain, shell, net } = require('electron');

const REPO = 'papadcha/expvault';
const UPDATES_DIR = path.join(app.getPath('userData'), 'updates');

// Ίδιο guard με το main.js's IS_MAIN_LINE — το allowed-versions.json εδώ
// περιέχει ΜΟΝΟ v1.x releases/download URLs. Ένα side-by-side build σαν το
// "ExpVault+" δεν πρέπει να δείχνει live rollback-advice/λήψεις για μια
// γραμμή προϊόντος που δεν είναι καν δική του.
const IS_MAIN_LINE = require('./package.json').name === 'expvault';

function _cmpVersion(a, b) {
  const pa = a.split('.').map(Number);
  const pb = b.split('.').map(Number);
  for (let i = 0; i < 3; i++) {
    if ((pa[i] || 0) > (pb[i] || 0)) return 1;
    if ((pa[i] || 0) < (pb[i] || 0)) return -1;
  }
  return 0;
}

function _fetchAllowedVersions() {
  return new Promise((resolve) => {
    const req = https.get({
      hostname: 'raw.githubusercontent.com',
      path: `/${REPO}/main/allowed-versions.json?_=${Date.now()}`,
      headers: { 'User-Agent': 'ExpVault-Updater' },
      timeout: 10000,
    }, (res) => {
      // Συλλογή ως Buffer chunks και αποκωδικοποίηση ΜΙΑ φορά στο τέλος —
      // string concatenation ανά chunk (data += chunk) σπάει πολυ-byte
      // ελληνικούς χαρακτήρες αν ο χαρακτήρας κοπεί ανάμεσα σε δύο network
      // chunks (κάθε chunk γίνεται toString() ξεχωριστά με λάθος αποτέλεσμα).
      const chunks = [];
      res.on('data', (chunk) => chunks.push(chunk));
      res.on('end', () => {
        try { resolve(JSON.parse(Buffer.concat(chunks).toString('utf-8'))); } catch (e) { resolve(null); }
      });
    });
    req.on('error', () => resolve(null));
    req.on('timeout', () => { req.destroy(); resolve(null); });
  });
}

// ── ExpVault+ / v2-line update check ─────────────────────────────────────
// Ίδιο σκεπτικό με checkVersionNotice() παραπάνω, αλλά για τη γραμμή v2
// (ExpVault+): διαβάζει allowed-versions-v2.json από το branch `v2` (όχι
// `main`) — έτσι δεν χρειάζεται να αγγίξουμε καθόλου το `main` για να έχει
// το ExpVault+ το δικό του manifest. Χτίστηκε αντιγράφοντας το αποδεδειγμένο
// (proven in production) μοτίβο του lab-galatista: κατεβάζει τον installer
// στο background χωρίς καμία ενέργεια χρήστη, αλλά το ΤΡΕΞΙΜΟ του installer
// παραμένει πάντα χειροκίνητο — ποτέ silent auto-install.
function _fetchAllowedVersionsV2() {
  return new Promise((resolve) => {
    const req = https.get({
      hostname: 'raw.githubusercontent.com',
      path: `/${REPO}/v2/allowed-versions-v2.json?_=${Date.now()}`,
      headers: { 'User-Agent': 'ExpVault-Updater' },
      timeout: 10000,
    }, (res) => {
      const chunks = [];
      res.on('data', (chunk) => chunks.push(chunk));
      res.on('end', () => {
        try { resolve(JSON.parse(Buffer.concat(chunks).toString('utf-8'))); } catch (e) { resolve(null); }
      });
    });
    req.on('error', () => resolve(null));
    req.on('timeout', () => { req.destroy(); resolve(null); });
  });
}

// net.request (Electron) ακολουθεί redirects αυτόματα — σε αντίθεση με το
// Node's https.get — απαραίτητο εδώ γιατί τα GitHub release assets σχεδόν
// πάντα redirect-άρουν σε S3. Επιβεβαιώνει "MZ" magic bytes πριν γράψει το
// αρχείο, ώστε μια κατεστραμμένη λήψη (π.χ. η HTML σελίδα ενός λάθος URL)
// να μην καταλήξει ποτέ να τρέξει σαν installer.
function _downloadFile(url, destPath, idleTimeoutMs = 20000) {
  return new Promise((resolve, reject) => {
    let settled = false;
    let timer;
    const done = (fn, arg) => { if (!settled) { settled = true; clearTimeout(timer); fn(arg); } };
    const resetTimer = () => {
      clearTimeout(timer);
      timer = setTimeout(() => {
        try { request.abort(); } catch (e) {}
        done(reject, new Error('Timeout λήψης (καμία δραστηριότητα δικτύου)'));
      }, idleTimeoutMs);
    };

    const request = net.request({ method: 'GET', url });
    const chunks = [];
    resetTimer();
    request.on('response', (response) => {
      if (response.statusCode >= 400) {
        done(reject, new Error('HTTP ' + response.statusCode));
        return;
      }
      response.on('data', (chunk) => { resetTimer(); chunks.push(chunk); });
      response.on('end', () => {
        const buf = Buffer.concat(chunks);
        if (buf.length < 2 || buf[0] !== 0x4D || buf[1] !== 0x5A) {
          done(reject, new Error('Το ληφθέν αρχείο δεν είναι έγκυρο installer (.exe)'));
          return;
        }
        try {
          fs.mkdirSync(path.dirname(destPath), { recursive: true });
          fs.writeFileSync(destPath, buf);
          done(resolve);
        } catch (e) { done(reject, e); }
      });
      response.on('error', (e) => done(reject, e));
    });
    request.on('error', (e) => done(reject, e));
    request.end();
  });
}

// Κρατάμε μόνο τον τελευταίο ληφθέντα installer — καθαρισμός ΜΟΝΟ μετά από
// επιτυχή λήψη, ώστε ένας προηγούμενος έγκυρος installer να μην χαθεί αν
// αποτύχει μια επόμενη λήψη.
async function _downloadUpdateInBackground(version, downloadUrl) {
  if (!downloadUrl) return null;
  const fileName = `Setup.${version}.exe`;
  const destPath = path.join(UPDATES_DIR, fileName);
  if (fs.existsSync(destPath)) return destPath; // ήδη κατεβασμένο σε προηγούμενη εκκίνηση

  try {
    await _downloadFile(downloadUrl, destPath);
    if (fs.existsSync(UPDATES_DIR)) {
      for (const f of fs.readdirSync(UPDATES_DIR)) {
        if (f !== fileName) { try { fs.rmSync(path.join(UPDATES_DIR, f), { force: true }); } catch (e) {} }
      }
    }
    return destPath;
  } catch (e) {
    console.log('[Update v2] Αποτυχία background λήψης installer:', e.message);
    try { fs.rmSync(destPath, { force: true }); } catch (e2) {}
    return null;
  }
}

async function checkForUpdatesV2(mainWindow) {
  const currentVersion = app.getVersion();
  const allowed = await _fetchAllowedVersionsV2();
  if (!allowed?.latestRecommendedVersion) return; // offline ή αρχείο λείπει — σιωπηλά

  const recommended = allowed.latestRecommendedVersion;
  const entry = allowed.versions?.find((v) => v.version === recommended);
  const cmp = _cmpVersion(recommended, currentVersion);
  const kind = cmp > 0 ? 'update' : (cmp < 0 && allowed.notice ? 'rollback' : null);
  if (!kind) return;
  if (!mainWindow || mainWindow.isDestroyed()) return;

  const fallbackUrl = entry?.downloadUrl || `https://github.com/${REPO}/releases/tag/v${recommended}`;

  // Το banner εμφανίζεται ΑΜΕΣΩΣ, χωρίς να περιμένει τη λήψη — μια κολλημένη
  // σύνδεση δεν πρέπει ποτέ να κάνει το banner "αόρατο" επ' άπειρον.
  mainWindow.webContents.send('version-notice', {
    kind,
    current: currentVersion,
    latest: recommended,
    url: fallbackUrl,
    localPath: null, // ο installer δεν έχει κατέβει ακόμα — το κουμπί ξεκινά ως "Λήψη"
    notes: kind === 'rollback' ? allowed.notice : (entry?.notes || ''),
  });

  const localPath = await _downloadUpdateInBackground(recommended, entry?.downloadUrl);
  if (localPath && !mainWindow.isDestroyed()) {
    mainWindow.webContents.send('version-notice-ready', { latest: recommended, localPath });
  }
}

// allowed-versions.json — χειροκίνητα συντηρούμενο αρχείο στο GitHub. Δεν
// συμπίπτει απαραίτητα με το τελευταίο release: αν μια έκδοση αποδειχτεί
// προβληματική, το latestRecommendedVersion παραμένει εσκεμμένα πίσω.
async function checkVersionNotice(mainWindow) {
  const currentVersion = app.getVersion();
  const allowed = await _fetchAllowedVersions();
  if (!allowed?.latestRecommendedVersion) return; // offline ή αρχείο λείπει — σιωπηλά

  const recommended = allowed.latestRecommendedVersion;
  const entry = allowed.versions?.find((v) => v.version === recommended);
  const cmp = _cmpVersion(recommended, currentVersion);

  if (!mainWindow || mainWindow.isDestroyed()) return;

  if (cmp > 0) {
    mainWindow.webContents.send('version-notice', {
      kind: 'update',
      current: currentVersion,
      latest: recommended,
      url: entry?.downloadUrl || `https://github.com/${REPO}/releases/tag/v${recommended}`,
      notes: entry?.notes || '',
    });
  } else if (cmp < 0 && allowed.notice) {
    // Η τρέχουσα έκδοση είναι πιο πρόσφατη από την προτεινόμενη ΚΑΙ υπάρχει
    // ρητή σημείωση προβλήματος — δεν εμφανίζουμε ποτέ αυτό το banner μόνο
    // επειδή ξεχάστηκε να ενημερωθεί το latestRecommendedVersion.
    mainWindow.webContents.send('version-notice', {
      kind: 'rollback',
      current: currentVersion,
      latest: recommended,
      url: entry?.downloadUrl || `https://github.com/${REPO}/releases/tag/v${recommended}`,
      notes: allowed.notice,
    });
  }
}

// Γιατί το token είναι embedded (και όχι server-side proxy): η εφαρμογή δεν
// έχει δικό της backend server — μόνο τοπικές εγκαταστάσεις χωρίς κοινή
// υποδομή. Ένα proxy θα σήμαινε να στηθεί/συντηρείται ξεχωριστός server μόνο
// για αυτή τη λειτουργία. Αντ' αυτού, fine-grained PAT scoped ΜΟΝΟ σε
// "Issues: write" στο συγκεκριμένο repo — ακόμα κι αν εξαχθεί από το .exe,
// το χειρότερο δυνατό είναι spam issues, όχι αλλαγή κώδικα/releases/δεδομένων.
//
// Rotation αν ποτέ χρειαστεί: (1) revoke το τρέχον token στο GitHub
// (Settings → Developer settings → Fine-grained tokens), (2) δημιούργησε νέο
// με το ΙΔΙΟ στενό scope (μόνο Issues: write, μόνο papadcha/expvault),
// (3) αντικατέστησε την τιμή στο τοπικό github-token.json (gitignored),
// (4) νέο release — οι ήδη εγκατεστημένες εκδόσεις κρατάνε το παλιό (πλέον
// ανενεργό) token μέχρι να αναβαθμιστούν.
function _loadGithubToken() {
  try {
    const raw = fs.readFileSync(path.join(__dirname, 'github-token.json'), 'utf-8');
    return JSON.parse(raw).token || null;
  } catch (e) {
    return null;
  }
}

function registerVersionIPC() {
  ipcMain.handle('get-app-version', () => app.getVersion());
  // Δοκιμάστηκαν και απορρίφθηκαν 2 πιο "προφανείς" λύσεις πριν αυτή —
  // κρατάω το σχόλιο γιατί το λάθος είναι εύκολο να ξαναγίνει:
  // - require('./package.json').build.productName: δουλεύει σε dev, σκάει σε
  //   packaged build — το electron-builder αφαιρεί εντελώς το "build" key
  //   από το package.json μέσα στο app.asar.
  // - app.getName(): επιστρέφει "expvaultplus" (το "name" field) και στα
  //   ΔΥΟ mode, ΟΧΙ το productName — επαληθεύτηκε live σε packaged build,
  //   όχι θεωρητικά.
  // Λύση: σε packaged build, το ίδιο το εκτελέσιμο ΕΙΝΑΙ ονομασμένο με το
  // productName από το electron-builder (π.χ. "ExpVault+.exe") — το
  // process.execPath είναι το μοναδικό αξιόπιστο σημείο αλήθειας.
  ipcMain.handle('get-app-product-name', () => {
    if (app.isPackaged) return path.basename(process.execPath, '.exe');
    try { return require('./package.json').build.productName; } catch (e) { return app.getName(); }
  });

  ipcMain.handle('get-version-history', () => {
    try {
      const content = fs.readFileSync(path.join(__dirname, 'VERSIONS.md'), 'utf-8');
      return { ok: true, content };
    } catch (e) {
      return { ok: false, error: e.message };
    }
  });

  ipcMain.handle('get-allowed-versions', async () => {
    const allowed = IS_MAIN_LINE ? await _fetchAllowedVersions() : await _fetchAllowedVersionsV2();
    return allowed || { versions: [], latestRecommendedVersion: null, safeDowngradeFloor: null, notice: null };
  });

  // Τρέχει τον ήδη κατεβασμένο installer (background download του
  // checkForUpdatesV2) — ο installer wizard παραμένει χειροκίνητος, μόνο η
  // λήψη του .exe έγινε αυτόματα πριν.
  ipcMain.handle('install-update-file', async (event, localPath) => {
    try {
      if (!localPath || !fs.existsSync(localPath)) {
        return { ok: false, error: 'Ο installer δεν βρέθηκε τοπικά.' };
      }
      const result = await shell.openPath(localPath); // κενό string = επιτυχία
      if (result) return { ok: false, error: result };
      return { ok: true };
    } catch (e) {
      return { ok: false, error: e.message };
    }
  });

  // Δημιουργεί GitHub issue (όχι αλλαγή αρχείου) — το token έχει δικαίωμα
  // ΜΟΝΟ "Issues: write" στο συγκεκριμένο repo. Ένας άνθρωπος βλέπει το
  // issue και αποφασίζει αν θα ενημερωθεί το allowed-versions.json — καμία
  // αυτόματη αλλαγή.
  ipcMain.handle('report-version-issue', async (event, lastGoodVersion, description) => {
    const token = _loadGithubToken();
    if (!token) return { ok: false, error: 'Η αναφορά δεν είναι διαθέσιμη σε αυτή την εγκατάσταση' };

    const currentVersion = app.getVersion();
    const hostname = os.hostname() || 'άγνωστο';
    const bodyText = [
      `**Τρέχουσα έκδοση (πιθανώς προβληματική):** v${currentVersion}`,
      `**Τελευταία έκδοση που δούλευε σωστά (κατά τον χρήστη):** v${lastGoodVersion}`,
      `**Μηχάνημα:** ${hostname}`,
      '',
      '**Περιγραφή προβλήματος:**',
      description || '(καμία περιγραφή)',
    ].join('\n');

    const payload = JSON.stringify({
      title: `[Αναφορά χρήστη] Πρόβλημα από v${currentVersion} — τελευταία σταθερή κατά τον χρήστη v${lastGoodVersion}`,
      body: bodyText,
    });

    try {
      const result = await new Promise((resolve, reject) => {
        const req = https.request({
          hostname: 'api.github.com',
          path: `/repos/${REPO}/issues`,
          method: 'POST',
          headers: {
            'Authorization': `Bearer ${token}`,
            'Accept': 'application/vnd.github+json',
            'Content-Type': 'application/json',
            'User-Agent': 'ExpVault-Updater',
          },
        }, (res) => {
          const chunks = [];
          res.on('data', (chunk) => chunks.push(chunk));
          res.on('end', () => resolve({ status: res.statusCode, data: Buffer.concat(chunks).toString('utf-8') }));
        });
        req.on('error', reject);
        req.write(payload);
        req.end();
      });
      if (result.status !== 201) {
        return { ok: false, error: `GitHub API σφάλμα ${result.status}` };
      }
      return { ok: true };
    } catch (e) {
      return { ok: false, error: e.message };
    }
  });
}

module.exports = { registerVersionIPC, checkVersionNotice, checkForUpdatesV2 };
