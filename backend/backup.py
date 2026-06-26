import os, shutil, json, re, subprocess
from datetime import datetime
from pathlib import Path

CONFIG_PATH = Path(__file__).parent / 'backup_config.json'
DB_PATH     = Path(__file__).parent / 'expvault.db'
TIMESTAMP_FMT = '%Y%m%d_%H%M%S'
PREFIX = 'expvault_backup_'
EXT    = '.db'


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
    # rclone paths look like "remote:some/path" — must contain ':' but not start with '/'
    return ':' in path and not path.startswith('/')


def get_config():
    return _load()


def save_config(paths: list, max_keep: int = 30):
    cfg = _load()
    cfg['paths']    = paths
    cfg['max_keep'] = max_keep
    _save(cfg)
    return cfg


def list_rclone_remotes() -> list:
    try:
        r = subprocess.run(['rclone', 'listremotes'], capture_output=True, text=True, timeout=10)
        return [x.strip() for x in r.stdout.splitlines() if x.strip()]
    except Exception:
        return []


# ── Local backup ──────────────────────────────────────────────────────────────

def _do_local_backup(folder: str, max_keep: int) -> dict:
    p = Path(folder)
    try:
        p.mkdir(parents=True, exist_ok=True)
    except Exception as e:
        return {'ok': False, 'error': str(e), 'folder': folder}

    ts   = datetime.now().strftime(TIMESTAMP_FMT)
    dest = p / f'{PREFIX}{ts}{EXT}'
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

def _do_rclone_backup(remote: str, max_keep: int) -> dict:
    ts   = datetime.now().strftime(TIMESTAMP_FMT)
    dest = f"{remote.rstrip('/')}/{PREFIX}{ts}{EXT}"
    try:
        r = subprocess.run(
            ['rclone', 'copyto', str(DB_PATH), dest],
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
            ['rclone', 'lsjson', remote, '--include', f'{PREFIX}*{EXT}'],
            capture_output=True, text=True, timeout=60
        )
        if ls.returncode == 0:
            files = sorted(json.loads(ls.stdout or '[]'), key=lambda x: x['Name'])
            for old in files[:-max_keep]:
                subprocess.run(
                    ['rclone', 'deletefile', f"{remote.rstrip('/')}/{old['Name']}"],
                    capture_output=True, timeout=30
                )
    except Exception:
        pass

    return {'ok': True, 'path': dest, 'folder': remote}


def _list_rclone_backups(remote: str) -> list:
    try:
        r = subprocess.run(
            ['rclone', 'lsjson', remote, '--include', f'{PREFIX}*{EXT}'],
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

def do_backup(folder: str, max_keep: int = 30) -> dict:
    if _is_rclone(folder):
        return _do_rclone_backup(folder, max_keep)
    return _do_local_backup(folder, max_keep)


def list_backups(folder: str) -> list:
    if _is_rclone(folder):
        return _list_rclone_backups(folder)
    return _list_local_backups(folder)


def run_all_backups() -> dict:
    cfg      = _load()
    paths    = [p for p in cfg.get('paths', []) if p]
    max_keep = cfg.get('max_keep', 30)

    if not paths:
        return {'ok': False, 'error': 'Δεν έχουν οριστεί φάκελοι backup', 'results': []}

    results = []
    any_ok  = False
    for p in paths:
        r = do_backup(p, max_keep)
        results.append(r)
        if r['ok']:
            any_ok = True

    ts = datetime.now().strftime('%d/%m/%Y %H:%M:%S')
    cfg['last_backup'] = ts
    cfg['last_status'] = 'ok' if any_ok else 'error'
    _save(cfg)

    return {'ok': any_ok, 'results': results, 'last_backup': ts}
