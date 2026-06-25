import os, shutil, json, re
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
            return json.load(f)
    return {'paths': ['', ''], 'max_keep': 30, 'last_backup': '', 'last_status': ''}


def _save(cfg):
    with open(CONFIG_PATH, 'w', encoding='utf-8') as f:
        json.dump(cfg, f, ensure_ascii=False, indent=2)


def get_config():
    return _load()


def save_config(paths: list, max_keep: int = 30):
    cfg = _load()
    cfg['paths']    = paths
    cfg['max_keep'] = max_keep
    _save(cfg)
    return cfg


def do_backup(folder: str, max_keep: int = 30) -> dict:
    folder = Path(folder)
    try:
        folder.mkdir(parents=True, exist_ok=True)
    except Exception as e:
        return {'ok': False, 'error': str(e), 'folder': str(folder)}

    ts   = datetime.now().strftime(TIMESTAMP_FMT)
    dest = folder / f'{PREFIX}{ts}{EXT}'
    try:
        shutil.copy2(DB_PATH, dest)
    except Exception as e:
        return {'ok': False, 'error': str(e), 'folder': str(folder)}

    # Prune oldest beyond max_keep
    backups = sorted(folder.glob(f'{PREFIX}*{EXT}'))
    for old in backups[:-max_keep]:
        try:
            old.unlink()
        except Exception:
            pass

    return {'ok': True, 'path': str(dest), 'folder': str(folder)}


def list_backups(folder: str) -> list:
    folder = Path(folder)
    if not folder.exists():
        return []
    result = []
    for f in sorted(folder.glob(f'{PREFIX}*{EXT}'), reverse=True):
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
