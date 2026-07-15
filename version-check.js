// version-check.js — έλεγχος allowed-versions.json manifest από GitHub raw,
// σύγκριση semantic version, "νέα έκδοση"/"γνωστό πρόβλημα, πρότεινε rollback"
// notice στο renderer, και η ροή αναφοράς προβλήματος έκδοσης
// (report-version-issue) που δημιουργεί GitHub issue μέσω fine-grained PAT.
//
// Ξεχωριστό, παράλληλο μηχανισμό από το setupAutoUpdater()/checkForUpdatesManually()
// του main.js (electron-updater / GitHub releases API) — αυτό εδώ καλύπτει κάτι
// που το electron-updater δεν ξέρει: "αυτή η έκδοση έχει γνωστό πρόβλημα, μέχρι
// ποια μπορείς να κάνεις ασφαλές downgrade".
//
// ΠΡΟΣΟΧΗ λειτουργικός κανόνας: αν ποτέ οριστεί notice/χαμηλώσει το
// latestRecommendedVersion επειδή ένα release αποδείχτηκε προβληματικό, αυτό
// ΜΟΝΟ ΤΟΥ δεν εμποδίζει το electron-updater να συνεχίσει να κατεβάζει/εγκαθιστά
// αυτόματα το ίδιο (χαλασμένο) GitHub release σε όσους δεν έχουν ενημερωθεί ακόμα.
// Πρέπει ΕΠΙΣΗΣ να γίνει unpublish ή να σημειωθεί ως draft/prerelease το ίδιο
// το GitHub release — η αλλαγή του allowed-versions.json από μόνη της δεν αρκεί.
const https = require('https');
const fs = require('fs');
const os = require('os');
const path = require('path');
const { app, ipcMain } = require('electron');

const REPO = 'papadcha/expvault';

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
