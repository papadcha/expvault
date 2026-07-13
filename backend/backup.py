import os, shutil, json, re, subprocess, sqlite3
from datetime import datetime
from pathlib import Path

import sys as _sys
_data_dir = os.environ.get(
    'EXPVAULT_DATA_DIR',
    str(Path(_sys.executable if getattr(_sys, 'frozen', False) else __file__).parent)
)
CONFIG_PATH = Path(_data_dir) / 'backup_config.json'
DB_PATH     = Path(_data_dir) / 'expvault.db'
TIMESTAMP_FMT = '%Y%m%d_%H%M%S'
PREFIX = 'expvault_backup_'
EXT    = '.db'

# Bundled rclone (βλ. EXPVAULT_RCLONE_PATH από main.js) — fallback στο
# rclone του system PATH αν δεν τρέχουμε packaged (ή σε Linux/Mac).
RCLONE_BIN = os.environ.get('EXPVAULT_RCLONE_PATH') or 'rclone'


def _load():
    if CONFIG_PATH.exists():
        with open(CONFIG_PATH, 'r', encoding='utf-8') as f:
            content = f.read().strip()
            if content:
                return json.loads(content)
    return {'paths': ['', ''], 'max_keep': 30, 'last_backup': '', 'last_status': ''}


def _save(cfg):
    with open(CONFIG_PATH, 'w', encoding='utf-8') as f:
        json.dump(cfg, f, ensure_ascii=False, indent=2)


def _is_rclone(path: str) -> bool:
    # rclone paths look like "remote:some/path" — must contain ':' but not start with '/'.
    # Windows local paths (C:\..., C:/...) also contain ':' μετά το drive letter — πρέπει
    # να αποκλειστούν πρώτα, αλλιώς κάθε τοπικό Windows path περνάει λανθασμένα από rclone.
    if re.match(r'^[A-Za-z]:[\\/]', path):
        return False
    return ':' in path and not path.startswith('/')


def get_config():
    return _load()


def save_config(paths: list, max_keep: int = 30):
    try:
        max_keep = int(max_keep)
    except (TypeError, ValueError):
        max_keep = 30
    max_keep = max(1, min(max_keep, 365))

    cfg = _load()
    cfg['paths']    = paths
    cfg['max_keep'] = max_keep
    _save(cfg)
    return cfg


def list_rclone_remotes() -> list:
    try:
        r = subprocess.run([RCLONE_BIN, 'listremotes'], capture_output=True, text=True, timeout=10)
        return [x.strip() for x in r.stdout.splitlines() if x.strip()]
    except Exception:
        return []


def list_remotes_detail() -> list:
    import configparser, sys
    candidates = [
        Path.home() / '.config' / 'rclone' / 'rclone.conf',
    ]
    if sys.platform == 'win32':
        appdata = os.environ.get('APPDATA', '')
        if appdata:
            candidates.insert(0, Path(appdata) / 'rclone' / 'rclone.conf')
    conf_path = next((p for p in candidates if p.exists()), None)
    if conf_path is None:
        return []
    cfg = configparser.ConfigParser()
    cfg.read(str(conf_path))
    result = []
    for name in cfg.sections():
        result.append({
            'name':     name,
            'remote':   name + ':',
            'type':     cfg[name].get('type', '?'),
            'provider': cfg[name].get('provider', ''),
        })
    return result


def delete_remote(name: str) -> dict:
    try:
        r = subprocess.run(
            [RCLONE_BIN, 'config', 'delete', name],
            capture_output=True, text=True, timeout=10
        )
        if r.returncode != 0:
            return {'ok': False, 'error': r.stderr.strip() or r.stdout.strip()}
        return {'ok': True}
    except Exception as e:
        return {'ok': False, 'error': str(e)}


# ── Local backup ──────────────────────────────────────────────────────────────

def _dest_name(ts: str, reason: str = None) -> str:
    """Ονομασία αρχείου backup — προαιρετικό reason suffix (π.χ. 'annual',
    'adeia1', 'adeia2') ώστε να ξεχωρίζει στη λίστα backups το γιατί τρέχει
    κάθε backup (manual/auto-on-close δεν έχουν reason, ίδιο format με πριν)."""
    return f'{PREFIX}{ts}_{reason}{EXT}' if reason else f'{PREFIX}{ts}{EXT}'


def _do_local_backup(folder: str, max_keep: int, reason: str = None) -> dict:
    p = Path(folder)
    try:
        p.mkdir(parents=True, exist_ok=True)
    except Exception as e:
        return {'ok': False, 'error': str(e), 'folder': folder}

    ts   = datetime.now().strftime(TIMESTAMP_FMT)
    dest = p / _dest_name(ts, reason)
    try:
        shutil.copy2(DB_PATH, dest)
    except Exception as e:
        return {'ok': False, 'error': str(e), 'folder': folder}

    backups = sorted(p.glob(f'{PREFIX}*{EXT}'))
    for old in backups[:-max_keep]:
        try:
            old.unlink()
        except Exception:
            pass

    return {'ok': True, 'path': str(dest), 'folder': folder}


def _list_local_backups(folder: str) -> list:
    p = Path(folder)
    if not p.exists():
        return []
    result = []
    for f in sorted(p.glob(f'{PREFIX}*{EXT}'), reverse=True):
        m = re.search(r'(\d{8}_\d{6})', f.name)
        if m:
            ts = datetime.strptime(m.group(1), TIMESTAMP_FMT)
            result.append({
                'name':    f.name,
                'path':    str(f),
                'ts':      ts.strftime('%d/%m/%Y %H:%M:%S'),
                'size_kb': round(f.stat().st_size / 1024, 1),
            })
    return result


# ── rclone backup ─────────────────────────────────────────────────────────────

def _do_rclone_backup(remote: str, max_keep: int, reason: str = None) -> dict:
    ts   = datetime.now().strftime(TIMESTAMP_FMT)
    dest = f"{remote.rstrip('/')}/{_dest_name(ts, reason)}"
    try:
        r = subprocess.run(
            [RCLONE_BIN, 'copyto', str(DB_PATH), dest],
            capture_output=True, text=True, timeout=120
        )
        if r.returncode != 0:
            return {'ok': False, 'error': r.stderr.strip() or r.stdout.strip(), 'folder': remote}
    except subprocess.TimeoutExpired:
        return {'ok': False, 'error': 'Timeout (120s)', 'folder': remote}
    except FileNotFoundError:
        return {'ok': False, 'error': 'rclone δεν βρέθηκε στο σύστημα', 'folder': remote}
    except Exception as e:
        return {'ok': False, 'error': str(e), 'folder': remote}

    # Prune oldest beyond max_keep
    try:
        ls = subprocess.run(
            [RCLONE_BIN, 'lsjson', remote, '--include', f'{PREFIX}*{EXT}'],
            capture_output=True, text=True, timeout=60
        )
        if ls.returncode == 0:
            files = sorted(json.loads(ls.stdout or '[]'), key=lambda x: x['Name'])
            for old in files[:-max_keep]:
                subprocess.run(
                    [RCLONE_BIN, 'deletefile', f"{remote.rstrip('/')}/{old['Name']}"],
                    capture_output=True, timeout=30
                )
    except Exception:
        pass

    return {'ok': True, 'path': dest, 'folder': remote}


def _list_rclone_backups(remote: str) -> list:
    try:
        r = subprocess.run(
            [RCLONE_BIN, 'lsjson', remote, '--include', f'{PREFIX}*{EXT}'],
            capture_output=True, text=True, timeout=60
        )
        if r.returncode != 0:
            return []
        files = sorted(json.loads(r.stdout or '[]'), key=lambda x: x['Name'], reverse=True)
        result = []
        for f in files:
            m = re.search(r'(\d{8}_\d{6})', f['Name'])
            if m:
                ts = datetime.strptime(m.group(1), TIMESTAMP_FMT)
                result.append({
                    'name':    f['Name'],
                    'path':    f"{remote.rstrip('/')}/{f['Name']}",
                    'ts':      ts.strftime('%d/%m/%Y %H:%M:%S'),
                    'size_kb': round(f.get('Size', 0) / 1024, 1),
                })
        return result
    except Exception:
        return []


# ── Public API ────────────────────────────────────────────────────────────────

def do_backup(folder: str, max_keep: int = 30, reason: str = None) -> dict:
    if _is_rclone(folder):
        return _do_rclone_backup(folder, max_keep, reason)
    return _do_local_backup(folder, max_keep, reason)


def list_backups(folder: str) -> list:
    if _is_rclone(folder):
        return _list_rclone_backups(folder)
    return _list_local_backups(folder)


def _known_backup_paths() -> set:
    """Τα backup paths που η ίδια η εφαρμογή βλέπει μέσα στα configured backup
    paths — defense-in-depth ώστε το restore_backup να μην δέχεται αυθαίρετο
    path (π.χ. αν κάποιος καταφέρει να καλέσει απευθείας το IPC με δικό του
    payload), μόνο ό,τι η ίδια η εφαρμογή ήδη έδειξε ως δικό της backup."""
    cfg = _load()
    known = set()
    for folder in [p for p in cfg.get('paths', []) if p]:
        for b in list_backups(folder):
            known.add(b['path'])
    return known


def _validate_sqlite_file(path: str) -> tuple:
    """PRAGMA integrity_check πάνω στο υποψήφιο αρχείο πριν εφαρμοστεί ως restore."""
    try:
        conn = sqlite3.connect(f'file:{path}?mode=ro', uri=True)
        try:
            row = conn.execute('PRAGMA integrity_check').fetchone()
            if not row or row[0] != 'ok':
                return False, 'Το αρχείο απέτυχε στον έλεγχο ακεραιότητας SQLite (integrity_check)'
            return True, ''
        finally:
            conn.close()
    except sqlite3.Error as e:
        return False, f'Μη έγκυρο αρχείο βάσης SQLite: {e}'


def restore_backup(path: str) -> dict:
    if path not in _known_backup_paths():
        return {'ok': False, 'error': 'Μη αναγνωρισμένο backup path — επιτρέπεται restore μόνο από τα configured backup paths.'}

    import tempfile
    tmp_path = None
    try:
        if _is_rclone(path):
            with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as tmp:
                tmp_path = tmp.name
            r = subprocess.run(
                [RCLONE_BIN, 'copyto', path, tmp_path],
                capture_output=True, text=True, timeout=120
            )
            if r.returncode != 0:
                return {'ok': False, 'error': r.stderr.strip() or r.stdout.strip()}
            source_path = tmp_path
        else:
            source_path = path

        valid, err = _validate_sqlite_file(source_path)
        if not valid:
            return {'ok': False, 'error': err}

        # Auto-snapshot της τρέχουσας βάσης πριν το restore, δίχτυ ασφαλείας
        # αν το restore αποδειχτεί λάθος επιλογή αρχείου.
        if DB_PATH.exists():
            ts = datetime.now().strftime(TIMESTAMP_FMT)
            shutil.copy2(DB_PATH, DB_PATH.parent / f'expvault_prerestore_{ts}{EXT}')

        # Atomic αντικατάσταση: γράφε σε temp δίπλα στο DB_PATH, μετά os.replace().
        tmp_dest = DB_PATH.parent / f'.{DB_PATH.name}.tmp_restore'
        shutil.copy2(source_path, tmp_dest)
        os.replace(tmp_dest, DB_PATH)

        return {'ok': True}
    except Exception as e:
        return {'ok': False, 'error': str(e)}
    finally:
        if tmp_path:
            try:
                os.unlink(tmp_path)
            except Exception:
                pass


def run_all_backups(reason: str = None) -> dict:
    cfg      = _load()
    paths    = [p for p in cfg.get('paths', []) if p]
    max_keep = cfg.get('max_keep', 30)

    if not paths:
        return {'ok': False, 'error': 'Δεν έχουν οριστεί φάκελοι backup', 'results': []}

    results = []
    any_ok  = False
    for p in paths:
        r = do_backup(p, max_keep, reason)
        results.append(r)
        if r['ok']:
            any_ok = True

    ts = datetime.now().strftime('%d/%m/%Y %H:%M:%S')
    cfg['last_backup'] = ts
    cfg['last_status'] = 'ok' if any_ok else 'error'
    _save(cfg)

    return {'ok': any_ok, 'results': results, 'last_backup': ts}


# ── Startup-triggered backups: ετήσιο (ημερολογιακό) + ανά άδεια (event-driven) ──

def check_annual_backup() -> dict:
    """Τρέχει backup αν πέρασε >=365 μέρες από το τελευταίο ετήσιο (ή ποτέ δεν έτρεξε).
    Ελέγχεται στην εκκίνηση της εφαρμογής — δεν υπάρχει scheduler/cron, οπότε αν η
    εφαρμογή μείνει κλειστή πάνω από ένα χρόνο το backup απλώς καθυστερεί μέχρι το
    επόμενο άνοιγμα."""
    cfg  = _load()
    last = cfg.get('last_annual_backup', '')
    if last:
        try:
            if (datetime.now() - datetime.strptime(last, '%Y-%m-%d')).days < 365:
                return {'ran': False}
        except ValueError:
            pass  # άκυρη/παλιά τιμή -> τρέχει σαν να μην είχε ξανατρέξει

    result = run_all_backups(reason='annual')
    if not result['ok']:
        return {'ran': False, 'error': result.get('error')}

    cfg = _load()
    cfg['last_annual_backup'] = datetime.now().strftime('%Y-%m-%d')
    _save(cfg)
    return {'ran': True, 'result': result}


def check_adeia_backups(alerts_level1: list, alerts_level2: list) -> dict:
    """alerts_level1/alerts_level2: αποτέλεσμα του database.get_adeia_low_balance_alerts()
    με threshold_multiplier=3.0 και =1.0 αντίστοιχα. Backup #1 (χωρίς toast) όταν μπει
    στο level1, backup #2 (με toast — επιστρέφεται στο 'notify') όταν μπει στο level2.

    Μία φορά ανά (adeia_id, nomiki_katigoria) όσο παραμένει σε alert: μόλις το υπόλοιπο
    ξαναανέβει πάνω από level1 (3x μέσο όρο) — είτε από νέα ΕΠΙΣΤΡΟΦΗ είτε από αύξηση
    εγκεκριμένης ποσότητας — ο marker καθαρίζεται μόνος του, οπότε αν ξαναμπεί αργότερα
    σε alert (νέες αγορές, ή μείωση της έγκρισης) ξανατρέχει κανονικά."""
    cfg   = _load()
    state = dict(cfg.get('adeia_backup_state', {}))

    current = {f"{a['adeia_id']}:{a['nomiki_katigoria']}": a for a in alerts_level1}
    level2_keys = {f"{a['adeia_id']}:{a['nomiki_katigoria']}" for a in alerts_level2}

    notify = []
    changed = False

    for key in list(state.keys()):
        if key not in current:
            del state[key]
            changed = True

    for key, a in current.items():
        entry = state.get(key, {'backup1_done': False, 'backup2_done': False})
        is_level2 = key in level2_keys
        needs_run = (is_level2 and not entry.get('backup2_done')) or \
                    (not is_level2 and not entry.get('backup1_done'))

        if needs_run:
            result = run_all_backups(reason='adeia2' if is_level2 else 'adeia1')
            if result['ok']:
                entry['backup1_done'] = True
                if is_level2:
                    entry['backup2_done'] = True
                    notify.append(a)
            changed = True

        state[key] = entry

    if changed:
        cfg = _load()
        cfg['adeia_backup_state'] = state
        _save(cfg)

    return {'notify': notify}
