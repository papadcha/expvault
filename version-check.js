// version-check.js — ΜΟΝΑΔΙΚΟΣ update-check μηχανισμός της εφαρμογής.
//
// Μέχρι την v1.1.12 υπήρχε ΚΑΙ ένα δεύτερο, ανεξάρτητο μηχανισμό εδώ
// (electron-updater/setupAutoUpdater() στο main.js) — silent auto-download +
// auto-install βασισμένο σε "ό,τι λέει το GitHub Releases API *latest* σε αυτό
// το repo", χωρίς καμία γνώση για known-bad releases. Αφαιρέθηκε εντελώς από
// την v1.2.0: ήταν ο μόνος τρόπος να εγγυηθούμε ότι κανένα μελλοντικό release
// διαφορετικής γραμμής προϊόντος (π.χ. ExpVault+/v2, βλ. branch `v2`) δεν
// μπορεί ποτέ να αυτο-εγκατασταθεί πάνω σε ήδη εγκατεστημένα v1.x — μια φορά
// που κάθε install ανέβει σε v1.2.0+ (μέσω του ΙΔΙΟΥ παλιού electron-updater,
// μία τελευταία φορά, αφού ήδη έτρεχε), αυτό το ρίσκο εξαφανίζεται μόνιμα.
//
// Τι κάνει τώρα: διαβάζει allowed-versions.json από το branch main, συγκρίνει
// semantic version, δείχνει banner "νέα έκδοση"/"γνωστό πρόβλημα, πρότεινε
// rollback" στο renderer, κατεβάζει τον installer στο background χωρίς καμία
// ενέργεια χρήστη — αλλά το ΤΡΕΞΙΜΟ του installer παραμένει πάντα χειροκίνητο
// κλικ, ποτέ silent auto-install. Ίδιο proven-in-production μοτίβο με το
// lab-galatista's modules/update-check.js (εκεί ESM/net.request· εδώ
// CommonJS/https+net — ίδια συμπεριφορά, βλ. DONE.md).
//
// ΠΡΟΣΟΧΗ λειτουργικός κανόνας: αν οριστεί notice/χαμηλώσει το
// latestRecommendedVersion επειδή ένα release αποδείχτηκε προβληματικό,
// πρέπει ΕΠΙΣΗΣ να γίνει unpublish/draft το ίδιο το GitHub release —
// αλλιώς όποιος δεν έχει ανοίξει ακόμα την εφαρμογή για να δει το notice
// μπορεί να το κατεβάσει απευθείας από το GitHub Releases σελίδα.
const https = require('https');
const fs = require('fs');
const os = require('os');
const path = require('path');
const { app, ipcMain, shell, net } = require('electron');

const REPO = 'papadcha/expvault';
const UPDATES_DIR = path.join(app.getPath('userData'), 'updates');

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
    console.log('[Update] Αποτυχία background λήψης installer:', e.message);
    try { fs.rmSync(destPath, { force: true }); } catch (e2) {}
    return null;
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

  ipcMain.handle('get-version-history', () => {
    try {
      const content = fs.readFileSync(path.join(__dirname, 'VERSIONS.md'), 'utf-8');
      return { ok: true, content };
    } catch (e) {
      return { ok: false, error: e.message };
    }
  });

  ipcMain.handle('get-allowed-versions', async () => {
    const allowed = await _fetchAllowedVersions();
    return allowed || { versions: [], latestRecommendedVersion: null, safeDowngradeFloor: null, notice: null };
  });

  // Τρέχει τον ήδη κατεβασμένο installer (background download του
  // checkVersionNotice) — ο installer wizard παραμένει χειροκίνητος, μόνο η
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

module.exports = { registerVersionIPC, checkVersionNotice };
