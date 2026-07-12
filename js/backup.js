import { escapeHtml, py, showConfirm } from './utils.js';

// ── BACKUP ───────────────────────────────────────────────────────────────────
export async function loadBackupPage() {
  try {
    const [cfg, remotes] = await Promise.all([
      py('get_backup_config'),
      py('list_rclone_remotes').catch(() => []),
    ]);
    const paths = cfg.paths ?? ['', ''];
    document.getElementById('bk-path0').value = paths[0] ?? '';
    document.getElementById('bk-path1').value = paths[1] ?? '';
    document.getElementById('bk-maxkeep').value = cfg.max_keep ?? 30;

    // Show available rclone remotes as clickable chips
    const remotesEl = document.getElementById('bk-remotes');
    if (remotes.length > 0) {
      remotesEl.innerHTML = remotes.map(r =>
        `<button onclick="bkSetRemote(this)" data-remote="${escapeHtml(r)}"
          style="padding:3px 10px;background:var(--card);border:1px solid rgba(255,255,255,0.15);border-radius:4px;color:var(--navy2);font-size:12px;cursor:pointer;">${escapeHtml(r)}</button>`
      ).join('');
    }

    const lastEl = document.getElementById('bk-last');
    if (cfg.last_backup) {
      const ok = cfg.last_status !== 'error';
      lastEl.style.display = 'block';
      lastEl.innerHTML = (ok ? '✅' : '⚠️') + ` Τελευταίο backup: <strong>${escapeHtml(cfg.last_backup)}</strong>`;
      lastEl.style.color = ok ? 'var(--text)' : '#e57373';
    } else {
      lastEl.style.display = 'none';
    }

    const listsEl = document.getElementById('bk-lists');
    listsEl.innerHTML = '';
    for (let i = 0; i < 2; i++) {
      const p = paths[i];
      if (!p) continue;
      const label = i === 0 ? 'Τοπικός Φάκελος' : 'Cloud (rclone)';
      let rows = '';
      try {
        const backups = await py('list_backups', { folder: p });
        if (backups.length === 0) {
          rows = `<tr><td colspan="4" style="padding:10px;color:var(--muted);text-align:center;">Δεν υπάρχουν αντίγραφα ακόμα</td></tr>`;
        } else {
          rows = backups.slice(0, 10).map(b =>
            `<tr>
              <td style="padding:6px 10px;">${escapeHtml(b.ts)}</td>
              <td style="padding:6px 10px;font-family:monospace;font-size:12px;color:var(--muted);">${escapeHtml(b.name)}</td>
              <td style="padding:6px 10px;text-align:right;color:var(--muted);">${b.size_kb} KB</td>
              <td style="padding:6px 10px;text-align:center;">
                <button onclick="bkRestore(this.dataset.path)" data-path="${escapeHtml(b.path)}"
                  style="padding:3px 10px;background:rgba(229,115,115,0.15);border:1px solid rgba(229,115,115,0.4);border-radius:4px;color:#e57373;font-size:11px;cursor:pointer;">
                  Επαναφορά
                </button>
              </td>
            </tr>`
          ).join('');
        }
      } catch {
        rows = `<tr><td colspan="3" style="padding:10px;color:#e57373;">Σφάλμα ανάγνωσης φακέλου</td></tr>`;
      }
      listsEl.innerHTML += `
        <div style="margin-bottom:20px;">
          <div style="font-size:12px;font-weight:600;color:var(--muted);text-transform:uppercase;letter-spacing:0.5px;margin-bottom:8px;">${label} — ${escapeHtml(p)}</div>
          <table style="width:100%;border-collapse:collapse;background:var(--card);border-radius:8px;overflow:hidden;font-size:13px;">
            <thead><tr style="background:rgba(0,0,0,0.2);">
              <th style="padding:8px 10px;text-align:left;font-weight:600;color:var(--navy2);">Ημερομηνία</th>
              <th style="padding:8px 10px;text-align:left;font-weight:600;color:var(--navy2);">Αρχείο</th>
              <th style="padding:8px 10px;text-align:right;font-weight:600;color:var(--navy2);">Μέγεθος</th>
              <th style="padding:8px 10px;text-align:center;font-weight:600;color:var(--navy2);width:100px;"></th>
            </tr></thead>
            <tbody>${rows}</tbody>
          </table>
        </div>`;
    }
  } catch (e) {
    console.error('loadBackupPage:', e);
  }
  bkRefreshRemotes();
}

export async function bkPickDir(idx) {
  if (!window.api?.openDir) return alert('Απαιτείται η εφαρμογή desktop.');
  const dir = await window.api.openDir();
  if (dir) document.getElementById(`bk-path${idx}`).value = dir;
}

export function bkSetRemote(btn) {
  const remote = btn.dataset.remote;
  const input = document.getElementById('bk-path1');
  // If already starts with this remote, don't overwrite existing subfolder
  if (!input.value.startsWith(remote)) {
    input.value = remote;
    input.focus();
    input.setSelectionRange(input.value.length, input.value.length);
  }
}

export async function bkRefreshRemotes() {
  const el = document.getElementById('bk-remotes-table');
  if (!el) return;
  try {
    const remotes = await py('list_remotes_detail');

    // Also refresh the chips in the cloud field
    const chipsEl = document.getElementById('bk-remotes');
    if (chipsEl) {
      chipsEl.innerHTML = remotes.map(r =>
        `<button onclick="bkSetRemote(this)" data-remote="${escapeHtml(r.remote)}"
          style="padding:3px 10px;background:var(--card);border:1px solid rgba(255,255,255,0.15);border-radius:4px;color:var(--navy2);font-size:12px;cursor:pointer;">${escapeHtml(r.remote)}</button>`
      ).join('');
    }

    if (remotes.length === 0) {
      el.innerHTML = `<div style="padding:16px;color:var(--muted);text-align:center;">Δεν υπάρχουν remotes — πατήστε «Νέο Remote».</div>`;
      return;
    }
    const typeLabels = {
      mega: 'Mega', drive: 'Google Drive', dropbox: 'Dropbox',
      onedrive: 'OneDrive', s3: 'Amazon S3', b2: 'Backblaze B2',
      sftp: 'SFTP', ftp: 'FTP', webdav: 'WebDAV',
    };
    const providerLabels = {
      Mega: 'Mega', Wasabi: 'Wasabi', Minio: 'MinIO',
      Cloudflare: 'Cloudflare R2', DigitalOcean: 'DigitalOcean Spaces',
      Backblaze: 'Backblaze B2', Alibaba: 'Alibaba OSS',
    };
    const getLabel = r => (r.provider && providerLabels[r.provider]) || typeLabels[r.type] || r.type;
    el.innerHTML = `
      <table style="width:100%;border-collapse:collapse;">
        <thead><tr style="background:rgba(0,0,0,0.2);">
          <th style="padding:8px 12px;text-align:left;font-size:12px;font-weight:600;color:var(--navy2);">Όνομα</th>
          <th style="padding:8px 12px;text-align:left;font-size:12px;font-weight:600;color:var(--navy2);">Πάροχος</th>
          <th style="padding:8px 12px;text-align:right;font-size:12px;font-weight:600;color:var(--navy2);"></th>
        </tr></thead>
        <tbody>${remotes.map(r => `
          <tr style="border-top:1px solid rgba(255,255,255,0.05);">
            <td style="padding:8px 12px;font-family:monospace;font-size:13px;">${escapeHtml(r.remote)}</td>
            <td style="padding:8px 12px;color:var(--muted);font-size:12px;">${escapeHtml(getLabel(r))}</td>
            <td style="padding:8px 12px;text-align:right;">
              <button onclick="bkDeleteRemote(${escapeHtml(JSON.stringify(r.name))})"
                style="padding:3px 10px;background:none;border:1px solid rgba(229,115,115,0.4);border-radius:4px;color:#e57373;font-size:11px;cursor:pointer;">Διαγραφή</button>
            </td>
          </tr>`).join('')}
        </tbody>
      </table>`;
  } catch(e) {
    el.innerHTML = `<div style="padding:16px;color:#e57373;">Σφάλμα: ${escapeHtml(e.message)}</div>`;
  }
}

export async function bkOpenRcloneTerminal() {
  if (!window.api?.openRcloneTerminal) return alert('Απαιτείται η εφαρμογή desktop.');
  const r = await window.api.openRcloneTerminal();
  if (!r.ok) alert('⚠️ ' + r.error);
}

export async function bkDeleteRemote(name) {
  showConfirm(`Διαγραφή remote "${name}";`, async () => {
    try {
      const r = await py('delete_remote', { name });
      if (!r.ok) { alert('Σφάλμα: ' + r.error); return; }
      bkRefreshRemotes();
    } catch(e) {
      alert('Σφάλμα: ' + e.message);
    }
  });
}

export async function bkSave() {
  const paths = [
    document.getElementById('bk-path0').value.trim(),
    document.getElementById('bk-path1').value.trim(),
  ];
  const maxKeep = parseInt(document.getElementById('bk-maxkeep').value) || 30;
  try {
    await py('save_backup_config', { paths, max_keep: maxKeep });
    alert('Οι ρυθμίσεις αποθηκεύτηκαν.');
    loadBackupPage();
  } catch (e) {
    alert('Σφάλμα: ' + e.message);
  }
}

export async function bkNow() {
  const btn = document.querySelector('#page-backup button[onclick="bkNow()"]');
  if (btn) { btn.disabled = true; btn.textContent = '⏳ Γίνεται backup...'; }
  try {
    const r = await py('run_backup');
    if (r.ok) {
      alert('Backup ολοκληρώθηκε επιτυχώς.');
    } else {
      const errs = (r.results || []).filter(x => !x.ok).map(x => x.error).join('\n');
      alert('Σφάλμα backup:\n' + (errs || r.error || 'Άγνωστο σφάλμα'));
    }
    loadBackupPage();
  } catch (e) {
    alert('Σφάλμα: ' + e.message);
  } finally {
    if (btn) { btn.disabled = false; btn.textContent = '▶ Backup Τώρα'; }
  }
}

export async function bkRestore(path) {
  showConfirm(
    `Επαναφορά από αντίγραφο;\n\n${path}\n\nΤα τρέχοντα δεδομένα θα αντικατασταθούν. Η εφαρμογή θα επανεκκινηθεί.`,
    async () => {
      try {
        const r = await py('restore_backup', { path });
        if (r.ok) {
          alert('✅ Επαναφορά ολοκληρώθηκε — επανεκκίνηση εφαρμογής...');
          setTimeout(() => window.location.reload(), 1500);
        } else {
          alert('⚠️ Σφάλμα επαναφοράς:\n' + (r.error || 'Άγνωστο σφάλμα'));
        }
      } catch (e) {
        alert('⚠️ Σφάλμα: ' + e.message);
      }
    }
  );
}

// Overlay κατά το κλείσιμο (αν backup τρέχει)
if (window.api?.onBackupProgress) {
  const bar = document.getElementById('bk-progress');
  const icon = document.getElementById('bk-progress-icon');
  const msg  = document.getElementById('bk-progress-msg');
  window.api.onBackupProgress(status => {
    if (status === 'start') {
      bar.style.display = 'flex';
      icon.textContent = '💾';
      msg.textContent = 'Γίνεται backup... παρακαλώ περιμένετε.';
    } else if (status === 'done') {
      icon.textContent = '✅';
      msg.textContent = 'Backup ολοκληρώθηκε.';
    } else if (status === 'error') {
      icon.textContent = '⚠️';
      msg.textContent = 'Το backup απέτυχε — κλείσιμο εφαρμογής.';
    }
  });
}
