import sqlite3
from contextlib import contextmanager
from datetime import datetime

DB_NAME = 'expvault.db'

@contextmanager
def get_db():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()

def init_db():
    with get_db() as conn:
        conn.executescript('''
            CREATE TABLE IF NOT EXISTS ylika (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                onoma TEXT NOT NULL,
                diatomi_mm INTEGER,
                monada_metrisis TEXT NOT NULL,
                paratirishis TEXT,
                UNIQUE(onoma, diatomi_mm)
            );

            CREATE TABLE IF NOT EXISTS promitheftes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                onoma TEXT NOT NULL UNIQUE
            );

            CREATE TABLE IF NOT EXISTS adeies (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                arithmos_adeias TEXT NOT NULL UNIQUE,
                perigrafi TEXT
            );

            CREATE TABLE IF NOT EXISTS kiniseis (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                auxon_arithmos INTEGER NOT NULL,
                imerominia TEXT NOT NULL,
                tipos TEXT NOT NULL CHECK(tipos IN ('ΕΙΣΑΓΩΓΗ','ΕΞΑΓΩΓΗ')),
                yliko_id INTEGER NOT NULL REFERENCES ylika(id),
                posotita REAL NOT NULL CHECK(posotita > 0),
                arithmos_parstatikos TEXT,
                adeia_id INTEGER REFERENCES adeies(id),
                promitheftis_id INTEGER REFERENCES promitheftes(id),
                paratirishis TEXT,
                ypografi TEXT,
                created_at TEXT DEFAULT (datetime('now'))
            );

            CREATE TABLE IF NOT EXISTS auxon_counter (
                id INTEGER PRIMARY KEY CHECK(id=1),
                next_val INTEGER NOT NULL DEFAULT 1
            );

            INSERT OR IGNORE INTO auxon_counter(id, next_val) VALUES (1, 1);
        ''')

def next_auxon():
    with get_db() as conn:
        row = conn.execute("SELECT next_val FROM auxon_counter WHERE id=1").fetchone()
        val = row[0]
        conn.execute("UPDATE auxon_counter SET next_val=? WHERE id=1", (val+1,))
        return val

# ─── ΥΛΙΚΑ ───────────────────────────────────────────────────────────────────

def get_all_ylika():
    with get_db() as conn:
        return [dict(r) for r in conn.execute(
            "SELECT * FROM ylika ORDER BY onoma").fetchall()]

def add_yliko(onoma, diatomi_mm, monada, paratirishis):
    with get_db() as conn:
        conn.execute(
            "INSERT INTO ylika(onoma,diatomi_mm,monada_metrisis,paratirishis) VALUES(?,?,?,?)",
            (onoma.upper(), diatomi_mm or None, monada, paratirishis or None))

def update_yliko(id, onoma, diatomi_mm, monada, paratirishis):
    with get_db() as conn:
        conn.execute(
            "UPDATE ylika SET onoma=?,diatomi_mm=?,monada_metrisis=?,paratirishis=? WHERE id=?",
            (onoma.upper(), diatomi_mm or None, monada, paratirishis or None, id))

def delete_yliko(id):
    with get_db() as conn:
        c1 = conn.execute("SELECT COUNT(*) FROM kiniseis WHERE yliko_id=?", (id,)).fetchone()[0]
        if c1 > 0:
            raise ValueError("Το υλικό χρησιμοποιείται σε κινήσεις και δεν μπορεί να διαγραφεί.")
        conn.execute("DELETE FROM ylika WHERE id=?", (id,))

# ─── ΠΡΟΜΗΘΕΥΤΕΣ ─────────────────────────────────────────────────────────────

def get_all_promitheftes():
    with get_db() as conn:
        return [dict(r) for r in conn.execute("SELECT * FROM promitheftes ORDER BY onoma").fetchall()]

def add_promitheftis(onoma):
    with get_db() as conn:
        conn.execute("INSERT INTO promitheftes(onoma) VALUES(?)", (onoma,))

def update_promitheftis(id, onoma):
    with get_db() as conn:
        conn.execute("UPDATE promitheftes SET onoma=? WHERE id=?", (onoma, id))

def delete_promitheftis(id):
    with get_db() as conn:
        c = conn.execute("SELECT COUNT(*) FROM kiniseis WHERE promitheftis_id=?", (id,)).fetchone()[0]
        if c > 0:
            raise ValueError("Ο προμηθευτής έχει συνδεδεμένες κινήσεις.")
        conn.execute("DELETE FROM promitheftes WHERE id=?", (id,))

# ─── ΑΔΕΙΕΣ ──────────────────────────────────────────────────────────────────

def get_all_adeies():
    with get_db() as conn:
        return [dict(r) for r in conn.execute("SELECT * FROM adeies ORDER BY arithmos_adeias").fetchall()]

def add_adeia(arithmos, perigrafi):
    with get_db() as conn:
        conn.execute("INSERT INTO adeies(arithmos_adeias,perigrafi) VALUES(?,?)", (arithmos, perigrafi or None))

def update_adeia(id, arithmos, perigrafi):
    with get_db() as conn:
        conn.execute("UPDATE adeies SET arithmos_adeias=?,perigrafi=? WHERE id=?", (arithmos, perigrafi or None, id))

def delete_adeia(id):
    with get_db() as conn:
        c = conn.execute("SELECT COUNT(*) FROM kiniseis WHERE adeia_id=?", (id,)).fetchone()[0]
        if c > 0:
            raise ValueError("Η άδεια χρησιμοποιείται σε κινήσεις.")
        conn.execute("DELETE FROM adeies WHERE id=?", (id,))

# ─── ΚΙΝΗΣΕΙΣ ────────────────────────────────────────────────────────────────

def get_kiniseis(yliko_id=None, apo=None, eos=None, tipos=None):
    sql = '''
        SELECT k.*, y.onoma as yliko_onoma, y.diatomi_mm, y.monada_metrisis,
               p.onoma as promitheftis_onoma, a.arithmos_adeias
        FROM kiniseis k
        JOIN ylika y ON k.yliko_id = y.id
        LEFT JOIN promitheftes p ON k.promitheftis_id = p.id
        LEFT JOIN adeies a ON k.adeia_id = a.id
        WHERE 1=1
    '''
    params = []
    if yliko_id:
        sql += " AND k.yliko_id=?"; params.append(yliko_id)
    if apo:
        sql += " AND k.imerominia>=?"; params.append(apo)
    if eos:
        sql += " AND k.imerominia<=?"; params.append(eos)
    if tipos:
        sql += " AND k.tipos=?"; params.append(tipos)
    sql += " ORDER BY k.auxon_arithmos ASC"
    with get_db() as conn:
        return [dict(r) for r in conn.execute(sql, params).fetchall()]

def add_kinisi(imerominia, tipos, yliko_id, posotita, arithmos_parstatikos,
               adeia_id, promitheftis_id, paratirishis, ypografi):
    auxon = next_auxon()
    with get_db() as conn:
        conn.execute('''
            INSERT INTO kiniseis(auxon_arithmos,imerominia,tipos,yliko_id,posotita,
                arithmos_parstatikos,adeia_id,promitheftis_id,paratirishis,ypografi)
            VALUES(?,?,?,?,?,?,?,?,?,?)
        ''', (auxon, imerominia, tipos, yliko_id, posotita,
              arithmos_parstatikos or None, adeia_id or None,
              promitheftis_id or None, paratirishis or None, ypografi or None))

def update_kinisi(id, imerominia, tipos, yliko_id, posotita, arithmos_parstatikos,
                  adeia_id, promitheftis_id, paratirishis, ypografi):
    with get_db() as conn:
        conn.execute('''
            UPDATE kiniseis SET imerominia=?,tipos=?,yliko_id=?,posotita=?,
                arithmos_parstatikos=?,adeia_id=?,promitheftis_id=?,paratirishis=?,ypografi=?
            WHERE id=?
        ''', (imerominia, tipos, yliko_id, posotita, arithmos_parstatikos or None,
              adeia_id or None, promitheftis_id or None,
              paratirishis or None, ypografi or None, id))

def delete_kinisi(id):
    with get_db() as conn:
        conn.execute("DELETE FROM kiniseis WHERE id=?", (id,))

# ─── ΥΠΟΛΟΙΠΑ ────────────────────────────────────────────────────────────────

def get_apothemates():
    with get_db() as conn:
        rows = conn.execute('''
            SELECT y.id, y.onoma, y.diatomi_mm, y.monada_metrisis,
                IFNULL(SUM(CASE WHEN k.tipos='ΕΙΣΑΓΩΓΗ' THEN k.posotita ELSE 0 END),0) as synolo_eisagogon,
                IFNULL(SUM(CASE WHEN k.tipos='ΕΞΑΓΩΓΗ'  THEN k.posotita ELSE 0 END),0) as synolo_exagogon,
                IFNULL(SUM(CASE WHEN k.tipos='ΕΙΣΑΓΩΓΗ' THEN k.posotita ELSE 0 END),0) -
                IFNULL(SUM(CASE WHEN k.tipos='ΕΞΑΓΩΓΗ'  THEN k.posotita ELSE 0 END),0) as ypoloipo
            FROM ylika y
            LEFT JOIN kiniseis k ON y.id = k.yliko_id
            GROUP BY y.id ORDER BY y.onoma
        ''').fetchall()
        return [dict(r) for r in rows]
