import { escapeHtml } from './utils.js';

// Parser για VERSIONS.md — αναμένει επικεφαλίδες μορφής "vX.Y.Z — ημ/νία  [ΤΑΓ]"
// ακολουθούμενες από γραμμή παύλων, ίδιο format σε κάθε release.
export function parseVersionsMd(text) {
  const lines = text.split('\n');
  const entries = [];
  let current = null;
  const headerRe = /^v(\d+\.\d+\.\d+)\s+—\s+(\S+)(?:\s+\[(.+?)\])?\s*$/;
  for (let i = 0; i < lines.length; i++) {
    const line = lines[i];
    const m = line.match(headerRe);
    if (m && /^-{5,}/.test(lines[i + 1] || '')) {
      if (current) entries.push(current);
      current = { version: m[1], date: m[2], tag: m[3] || null, body: [] };
      i++;
      continue;
    }
    if (current && line.trim()) current.body.push(line.trim());
  }
  if (current) entries.push(current);
  return entries;
}

export async function showVersionHistory() {
  const modal = document.getElementById('version-history-modal');
  const body  = document.getElementById('version-history-body');
  body.innerHTML = '<p style="color:var(--muted);">Φόρτωση…</p>';
  modal.classList.add('open');

  const [historyResult, allowed, currentVersion] = await Promise.all([
    window.api.getVersionHistory(),
    window.api.getAllowedVersions(),
    window.api.getAppVersion(),
  ]);

  if (!historyResult?.ok) {
    body.innerHTML = '<p style="color:var(--muted);">Δεν ήταν δυνατή η φόρτωση του ιστορικού εκδόσεων.</p>';
    return;
  }

  const entries    = parseVersionsMd(historyResult.content);
  const allowedMap = new Map((allowed?.versions || []).map(v => [v.version, v]));

  const noticeHtml = allowed?.notice
    ? `<div style="background:#fde8e8;border:1px solid #f5b7b1;color:#7b1c1c;
         border-radius:6px;padding:10px 14px;margin-bottom:12px;font-size:13px;">
         ⚠️ ${escapeHtml(allowed.notice)}</div>`
    : '';

  const entriesHtml = entries.map(e => {
    const safe      = allowedMap.get(e.version);
    const isCurrent = e.version === currentVersion;
    const color = safe ? '#68d391' : '#fc8181';
    const bg    = safe ? '#c6f6d520' : '#fed7d720';
    const action = safe
      ? `<button class="btn btn-outline btn-sm" onclick="window.api.openExternal('${escapeHtml(safe.downloadUrl)}')">⬇ Λήψη</button>`
      : `<span style="color:var(--muted);font-size:11px;">δεν συνιστάται downgrade</span>`;
    return `
      <div style="border-left:3px solid ${color};background:${bg};border-radius:6px;
           padding:8px 10px;margin-bottom:6px;">
        <div style="display:flex;justify-content:space-between;align-items:center;gap:8px;flex-wrap:wrap;">
          <div>
            <strong>v${escapeHtml(e.version)}</strong>
            <span style="color:var(--muted);font-size:12px;">— ${escapeHtml(e.date)}</span>
            ${isCurrent ? `<span style="color:var(--accent);font-size:11px;margin-left:6px;">τρέχουσα</span>` : ''}
          </div>
          ${action}
        </div>
        <div style="font-size:12px;color:var(--muted);margin-top:4px;white-space:pre-wrap;">${escapeHtml(e.body.join('\n'))}</div>
      </div>`;
  }).join('');

  const reportOptions = (allowed?.versions || []).map(v =>
    `<option value="${escapeHtml(v.version)}">v${escapeHtml(v.version)}</option>`
  ).join('');

  body.innerHTML = `
    ${noticeHtml}
    <div style="display:grid;grid-template-columns:1.3fr 1fr;gap:20px;">
      <div style="max-height:50vh;overflow-y:auto;">${entriesHtml}</div>
      <div style="border-left:1px solid var(--border);padding-left:16px;">
        <div style="font-weight:600;font-size:13px;margin-bottom:6px;">🐞 Αναφορά Προβλήματος</div>
        <p style="font-size:11px;color:var(--muted);margin-bottom:8px;">
          Πράσινο = ασφαλές downgrade (με κουμπί λήψης). Κόκκινο = δεν συνιστάται
          επιστροφή τόσο παλιά. Αν εντοπίσατε από ποια έκδοση ξεκίνησε ένα
          πρόβλημα, αναφέρετέ το εδώ.
        </p>
        <label style="font-size:11px;">Τελευταία έκδοση που δούλευε σωστά</label>
        <select id="report-last-good-version" style="width:100%;margin-bottom:8px;">${reportOptions}</select>
        <label style="font-size:11px;">Περιγραφή προβλήματος</label>
        <textarea id="report-issue-description" rows="4" style="width:100%;margin-bottom:8px;"
                  placeholder="Τι παρατηρήσατε; Πότε συμβαίνει;"></textarea>
        <button class="btn btn-outline btn-sm" id="report-issue-btn"
                onclick="submitVersionIssueReport()">Αποστολή Αναφοράς</button>
      </div>
    </div>
  `;
}

export async function submitVersionIssueReport() {
  const lastGood = document.getElementById('report-last-good-version')?.value;
  const desc     = document.getElementById('report-issue-description')?.value?.trim();
  if (!lastGood) { window._showToast('⚠️ Επιλέξτε έκδοση', 'warn'); return; }
  if (!desc)     { window._showToast('⚠️ Περιγράψτε το πρόβλημα', 'warn'); return; }

  const btn = document.getElementById('report-issue-btn');
  if (btn) btn.disabled = true;
  try {
    const result = await window.api.reportVersionIssue(lastGood, desc);
    if (result?.ok) {
      window._showToast('✅ Η αναφορά στάλθηκε', 'success');
      document.getElementById('version-history-modal').classList.remove('open');
    } else {
      window._showToast('⚠️ Σφάλμα αναφοράς: ' + (result?.error || ''), 'error');
    }
  } finally {
    if (btn) btn.disabled = false;
  }
}

// Banner "νέα έκδοση διαθέσιμη" / "γνωστό πρόβλημα σε αυτή την έκδοση,
// προτείνεται προσωρινό downgrade" — από version-check.js, ξεχωριστό κανάλι
// (version-notice) από το update-status του electron-updater.
export function showVersionNotice(info) {
  const banner = document.getElementById('version-notice-banner');
  const msg    = document.getElementById('version-notice-msg');
  const btn    = document.getElementById('version-notice-btn');
  const isRollback = info.kind === 'rollback';

  msg.textContent = isRollback
    ? `Η έκδοσή σας (v${info.current}) έχει γνωστό πρόβλημα. Προτείνεται προσωρινή επιστροφή σε v${info.latest}${info.notes ? ' — ' + info.notes : ''}`
    : `Νέα έκδοση διαθέσιμη: v${info.latest} (τρέχουσα: v${info.current})`;
  btn.textContent = isRollback ? `Λήψη v${info.latest}` : 'Λήψη';
  btn.onclick = () => window.api.openExternal(info.url);
  banner.style.display = 'flex';
}
if (window.api?.onVersionNotice) {
  window.api.onVersionNotice(showVersionNotice);
}

// ── ΙΣΤΟΡΙΚΟ ΕΚΔΟΣΕΩΝ / SAFE DOWNGRADE FLOOR ─────────────────────────────────
// Ξεχωριστό, παράλληλο μηχανισμό από το AUTO-UPDATE (electron-updater) — αυτό
// καλύπτει "ποια έκδοση έχει γνωστό πρόβλημα / μέχρι πού μπορείς να κάνεις
// ασφαλές downgrade", κάτι που το electron-updater δεν ξέρει.
if (window.api?.getAppVersion) {
  window.api.getAppVersion().then(ver => {
    const el = document.getElementById('sidebar-version');
    if (el && ver) {
      el.textContent = 'ExpVault v' + ver;
      el.title = 'Δες τι άλλαξε';
      el.onclick = showVersionHistory;
    }
  });
}
