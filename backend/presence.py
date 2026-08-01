"""
presence.py — heartbeat-based presence detection over the same rclone remote
used for DB backup/sync (backend/backup.py).

Each install periodically writes its own <computer>__<user>.json under
<remote>/presence/; list_presence() merges every install's file into one list
for the renderer to render as an online/offline table.
"""
import os
import json
import re
import socket
import subprocess
import tempfile
from datetime import datetime, timezone
from pathlib import Path

import backup  # RCLONE_BIN, get_config(), _is_rclone()

RCLONE_BIN = backup.RCLONE_BIN
PRESENCE_SUBDIR = 'presence'


def _sanitize(name: str) -> str:
    return re.sub(r'[^A-Za-z0-9_-]', '_', name or '') or 'machine'


def _identity() -> dict:
    user = os.environ.get('USERNAME') or os.environ.get('USER') or 'άγνωστος'
    computer = socket.gethostname() or 'machine'
    return {'user': user, 'computer': computer}


def whoami() -> dict:
    """Δημόσιο wrapper της _identity() για το bridge — ώστε ο renderer να μπορεί
    να εξαιρέσει το δικό του heartbeat όταν υπολογίζει αν υπάρχει *άλλος*
    συνδεδεμένος χρήστης."""
    return _identity()


def _remote_dir():
    cfg = backup.get_config()
    paths = cfg.get('paths') or ['', '']
    remote = paths[1] if len(paths) > 1 else ''
    if not remote or not backup._is_rclone(remote):
        return None
    return f"{remote.rstrip('/')}/{PRESENCE_SUBDIR}"


def send_heartbeat() -> dict:
    remote_dir = _remote_dir()
    if remote_dir is None:
        return {'ok': True, 'skipped': True, 'reason': 'no_remote_configured'}

    ident = _identity()
    payload = {
        'user': ident['user'],
        'computer': ident['computer'],
        'last_seen': datetime.now(timezone.utc).isoformat(timespec='seconds'),
    }
    dest = f"{remote_dir}/{_sanitize(ident['computer'])}__{_sanitize(ident['user'])}.json"

    tmp_path = None
    try:
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False,
                                          encoding='utf-8') as tmp:
            json.dump(payload, tmp, ensure_ascii=False)
            tmp_path = tmp.name

        r = subprocess.run(
            [RCLONE_BIN, 'copyto', tmp_path, dest],
            capture_output=True, text=True, timeout=30
        )
        if r.returncode != 0:
            return {'ok': False, 'error': r.stderr.strip() or r.stdout.strip(), 'folder': remote_dir}
    except subprocess.TimeoutExpired:
        return {'ok': False, 'error': 'Timeout (30s)', 'folder': remote_dir}
    except FileNotFoundError:
        return {'ok': False, 'error': 'rclone δεν βρέθηκε στο σύστημα', 'folder': remote_dir}
    except Exception as e:
        return {'ok': False, 'error': str(e), 'folder': remote_dir}
    finally:
        if tmp_path:
            try:
                os.unlink(tmp_path)
            except Exception:
                pass

    return {'ok': True, 'path': dest}


def list_presence() -> list:
    remote_dir = _remote_dir()
    if remote_dir is None:
        return []

    with tempfile.TemporaryDirectory() as tmp_dir:
        try:
            r = subprocess.run(
                [RCLONE_BIN, 'copy', remote_dir, tmp_dir, '--include', '*.json'],
                capture_output=True, text=True, timeout=60
            )
        except Exception:
            return []
        if r.returncode != 0:
            # π.χ. ο φάκελος presence/ δεν υπάρχει ακόμα — καμία εγκατάσταση δεν
            # έχει στείλει heartbeat ποτέ — άδεια λίστα, όχι σφάλμα
            return []

        result = []
        for f in Path(tmp_dir).glob('*.json'):
            try:
                with open(f, 'r', encoding='utf-8') as fh:
                    data = json.load(fh)
                if data.get('user') and data.get('last_seen'):
                    result.append({
                        'user': data.get('user', ''),
                        'computer': data.get('computer', ''),
                        'last_seen': data.get('last_seen', ''),
                    })
            except Exception:
                continue  # αγνόησε κατεστραμμένο/μερικώς-γραμμένο αρχείο
        return result
