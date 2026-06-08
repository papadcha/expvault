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
                tipos TEXT NOT NULL CHECK(tipos IN ('ΕΙΣΑΓΩΓΗ','ΚΑΤΑΝΑΛΩΣΗ','ΕΠΙΣΤΡΟΦΗ','ΕΞΑΓΩΓΗ')),
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

            CREATE TABLE IF NOT EXISTS ypologismos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                parstatiko_agoras TEXT NOT NULL,
                imerominia_agoras TEXT NOT NULL,
                senario INTEGER NOT NULL CHECK(senario IN (1,2)),
                created_at TEXT DEFAULT (datetime('now'))
            );

            CREATE TABLE IF NOT EXISTS ypologismos_grammes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ypologismos_id INTEGER NOT NULL REFERENCES ypologismos(id) ON DELETE CASCADE,
                yliko_id INTEGER NOT NULL REFERENCES ylika(id),
                posotita_agoras REAL NOT NULL DEFAULT 0,
                posotita_katanalosis REAL NOT NULL DEFAULT 0,
                posotita_epistrofis REAL NOT NULL DEFAULT 0
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
        # Έλεγχος αν υπάρχει ήδη (case-insensitive)
        existing = conn.execute(
            "SELECT id FROM ylika WHERE UPPER(onoma)=UPPER(?) AND (diatomi_mm IS ? OR diatomi_mm=?)",
            (onoma.upper(), diatomi_mm, diatomi_mm)
        ).fetchone()
        if existing:
            return existing[0]  # Επιστρέφει υπάρχον id
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

def check_parstatiko_exists(arithmos_parstatikos):
    """Ελέγχει αν παραστατικό υπάρχει ήδη στη βάση."""
    if not arithmos_parstatikos:
        return []
    with get_db() as conn:
        rows = conn.execute('''
            SELECT k.imerominia, k.tipos, y.onoma as yliko_onoma, k.posotita, y.monada_metrisis
            FROM kiniseis k
            JOIN ylika y ON k.yliko_id = y.id
            WHERE k.arithmos_parstatikos = ?
            ORDER BY k.imerominia
        ''', (arithmos_parstatikos,)).fetchall()
        return [dict(r) for r in rows]

# ─── ΚΙΝΗΣΕΙΣ ────────────────────────────────────────────────────────────────

def get_kiniseis(yliko_id=None, apo=None, eos=None, tipos=None):
    sql = '''
        SELECT k.*, y.onoma as yliko_onoma, y.diatomi_mm, y.monada_metrisis,
               p.onoma as promitheftis_onoma, a.arithmos_adeias, a.perigrafi as ekdousa_archi
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

def get_last_eisagogi_parstatiko():
    """Επιστρέφει το τελευταίο παραστατικό ΕΙΣΑΓΩΓΗΣ."""
    with get_db() as conn:
        row = conn.execute(
            "SELECT arithmos_parstatikos, imerominia FROM kiniseis WHERE tipos='ΕΙΣΑΓΩΓΗ' AND arithmos_parstatikos IS NOT NULL ORDER BY auxon_arithmos DESC LIMIT 1"
        ).fetchone()
        return dict(row) if row else {}

def batch_update_parstatiko(old_parst, new_parst=None, new_date=None):
    """Μαζική ενημέρωση παραστατικού/ημερομηνίας σε όλες τις κινήσεις."""
    with get_db() as conn:
        if new_parst and new_date:
            conn.execute(
                "UPDATE kiniseis SET arithmos_parstatikos=?, imerominia=? WHERE arithmos_parstatikos=?",
                (new_parst, new_date, old_parst)
            )
        elif new_parst:
            conn.execute(
                "UPDATE kiniseis SET arithmos_parstatikos=? WHERE arithmos_parstatikos=?",
                (new_parst, old_parst)
            )
        elif new_date:
            conn.execute(
                "UPDATE kiniseis SET imerominia=? WHERE arithmos_parstatikos=?",
                (new_date, old_parst)
            )
        return conn.execute(
            "SELECT changes()"
        ).fetchone()[0]

# ─── ΥΠΟΛΟΙΠΑ ────────────────────────────────────────────────────────────────

def get_apothemates():
    with get_db() as conn:
        rows = conn.execute('''
            SELECT y.id, y.onoma, y.diatomi_mm, y.monada_metrisis,
                IFNULL(SUM(CASE WHEN k.tipos='ΕΙΣΑΓΩΓΗ' THEN k.posotita ELSE 0 END),0) as synolo_eisagogon,
                IFNULL(SUM(CASE WHEN k.tipos='ΚΑΤΑΝΑΛΩΣΗ' OR (k.tipos='ΕΞΑΓΩΓΗ' AND (k.arithmos_parstatikos IS NULL OR k.arithmos_parstatikos='')) THEN k.posotita ELSE 0 END),0) as katanalosi_xeirokiniti,
                IFNULL(SUM(CASE WHEN k.tipos='ΕΠΙΣΤΡΟΦΗ' OR (k.tipos='ΕΞΑΓΩΓΗ' AND k.arithmos_parstatikos IS NOT NULL AND k.arithmos_parstatikos!='') THEN k.posotita ELSE 0 END),0) as epistrofi_xeirokiniti
            FROM ylika y
            INNER JOIN kiniseis k ON y.id = k.yliko_id
            GROUP BY y.id
            HAVING synolo_eisagogon > 0
            ORDER BY y.onoma
        ''').fetchall()

        result = []
        for r in rows:
            d = dict(r)
            agores   = d['synolo_eisagogon']
            kat_xeir = d['katanalosi_xeirokiniti']
            epi_xeir = d['epistrofi_xeirokiniti']

            if kat_xeir > 0 and epi_xeir == 0:
                # Σενάριο 2: έχει κατανάλωση → υπολόγισε επιστροφή
                d['synolo_katanalosis'] = kat_xeir
                d['synolo_epistrofon']  = max(0.0, agores - kat_xeir)
            else:
                # Σενάριο 1: έχει επιστροφή (ή τίποτα) → υπολόγισε κατανάλωση
                d['synolo_epistrofon']  = epi_xeir
                d['synolo_katanalosis'] = max(0.0, agores - epi_xeir)

            d['ypoloipo'] = round(agores - d['synolo_katanalosis'] - d['synolo_epistrofon'], 6)
            result.append(d)
        return result

# ─── ΕΛΕΓΧΟΣ ΕΚΚΡΕΜΟΤΗΤΑΣ ────────────────────────────────────────────────────

def check_ekkremotita(yliko_id=None, imerominia=None, parstatiko=None):
    """
    Ελέγχει αν μετά από μια καταχώρηση υπάρχει εκκρεμότητα (λείπει η 3η κίνηση).
    Επιστρέφει dict με:
      - ekkremotita: bool
      - tipo: 'ΚΑΤΑΝΑΛΩΣΗ' ή 'ΕΠΙΣΤΡΟΦΗ' (τι λείπει)
      - yliko_id, yliko_onoma, monada
      - posotita: η υπολογισμένη ποσότητα που λείπει
      - imerominia, parstatiko: στοιχεία σχετικής αγοράς
    """
    with get_db() as conn:
        # Πάρε όλες τις κινήσεις του υλικού για αυτή την ημερομηνία
        sql = '''
            SELECT k.tipos, k.posotita, k.arithmos_parstatikos,
                   k.imerominia, k.yliko_id, y.onoma, y.monada_metrisis
            FROM kiniseis k
            JOIN ylika y ON k.yliko_id = y.id
            WHERE 1=1
        '''
        params = []
        if yliko_id:
            sql += ' AND k.yliko_id=?'; params.append(yliko_id)
        if imerominia:
            sql += ' AND k.imerominia=?'; params.append(imerominia)
        if parstatiko:
            # Φίλτρο: υλικά που ανήκουν στο συγκεκριμένο παραστατικό αγοράς
            sql += ' AND k.yliko_id IN (SELECT yliko_id FROM kiniseis WHERE arithmos_parstatikos=? AND tipos='ΕΙΣΑΓΩΓΗ')'
            params.append(parstatiko)

        rows = conn.execute(sql, params).fetchall()
        if not rows:
            return {'ekkremotita': False}

        # Ομαδοποίηση ανά υλικό
        by_yliko = {}
        for r in rows:
            yid = r['yliko_id']
            if yid not in by_yliko:
                by_yliko[yid] = {
                    'yliko_id': yid,
                    'yliko_onoma': r['onoma'],
                    'monada': r['monada_metrisis'],
                    'imerominia': r['imerominia'],
                    'agores': 0, 'katanalosis': 0, 'epistrofes': 0
                }
            t = r['tipos']
            if t == 'ΕΙΣΑΓΩΓΗ':
                by_yliko[yid]['agores'] += r['posotita']
            elif t == 'ΚΑΤΑΝΑΛΩΣΗ':
                by_yliko[yid]['katanalosis'] += r['posotita']
            elif t == 'ΕΠΙΣΤΡΟΦΗ' or (t == 'ΕΞΑΓΩΓΗ' and r['arithmos_parstatikos']):
                by_yliko[yid]['epistrofes'] += r['posotita']

        # Έλεγχος για κάθε υλικό
        ekkremotes = []
        for yid, d in by_yliko.items():
            agores = d['agores']
            kat    = d['katanalosis']
            epi    = d['epistrofes']

            if agores == 0:
                continue

            if kat == 0 and epi == 0:
                # Δεν έχει ούτε κατανάλωση ούτε επιστροφή — εκκρεμεί και τα δύο
                ekkremotes.append({**d, 'tipo': 'ΚΑΤΑΝΑΛΩΣΗ',
                                   'posotita': agores, 'ekkremotita': True})
            elif kat > 0 and epi == 0:
                # Σενάριο 2: λείπει επιστροφή
                ep_ypol = round(agores - kat, 6)
                if ep_ypol > 0:
                    ekkremotes.append({**d, 'tipo': 'ΕΠΙΣΤΡΟΦΗ',
                                       'posotita': ep_ypol, 'ekkremotita': True})
            elif epi > 0 and kat == 0:
                # Σενάριο 1: λείπει κατανάλωση
                kat_ypol = round(agores - epi, 6)
                if kat_ypol > 0:
                    ekkremotes.append({**d, 'tipo': 'ΚΑΤΑΝΑΛΩΣΗ',
                                       'posotita': kat_ypol, 'ekkremotita': True})

        if not ekkremotes:
            return {'ekkremotita': False}

        return {'ekkremotita': True, 'ekkremes': ekkremotes}

def delete_kiniseis_by_parstatiko(arithmos_parstatikos):
    """Διαγράφει όλες τις κινήσεις με συγκεκριμένο παραστατικό."""
    with get_db() as conn:
        conn.execute(
            "DELETE FROM kiniseis WHERE arithmos_parstatikos=?",
            (arithmos_parstatikos,)
        )

# ─── ΥΠΟΛΟΓΙΣΜΟΣ ─────────────────────────────────────────────────────────────

def save_ypologismos(parstatiko_agoras, imerominia_agoras, senario, grammes):
    """
    Αποθηκεύει υπολογισμό. Διαγράφει τυχόν παλιό για το ίδιο παραστατικό.
    grammes: list of {yliko_id, posotita_agoras, posotita_katanalosis, posotita_epistrofis}
    """
    with get_db() as conn:
        conn.execute("DELETE FROM ypologismos WHERE parstatiko_agoras=?", (parstatiko_agoras,))
        conn.execute(
            "INSERT INTO ypologismos(parstatiko_agoras, imerominia_agoras, senario) VALUES(?,?,?)",
            (parstatiko_agoras, imerominia_agoras, senario)
        )
        yid = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
        for g in grammes:
            conn.execute(
                "INSERT INTO ypologismos_grammes(ypologismos_id,yliko_id,posotita_agoras,posotita_katanalosis,posotita_epistrofis) VALUES(?,?,?,?,?)",
                (yid, g['yliko_id'], g['posotita_agoras'], g['posotita_katanalosis'], g['posotita_epistrofis'])
            )
        return yid

def get_ypologismos(parstatiko_agoras):
    """Επιστρέφει τον υπολογισμό για ένα παραστατικό."""
    with get_db() as conn:
        yp = conn.execute(
            "SELECT * FROM ypologismos WHERE parstatiko_agoras=?", (parstatiko_agoras,)
        ).fetchone()
        if not yp:
            return None
        grammes = conn.execute('''
            SELECT g.*, y.onoma as yliko_onoma, y.monada_metrisis
            FROM ypologismos_grammes g
            JOIN ylika y ON g.yliko_id = y.id
            WHERE g.ypologismos_id=?
        ''', (yp['id'],)).fetchall()
        return {**dict(yp), 'grammes': [dict(g) for g in grammes]}

def delete_ypologismos(parstatiko_agoras):
    with get_db() as conn:
        conn.execute("DELETE FROM ypologismos WHERE parstatiko_agoras=?", (parstatiko_agoras,))

def compare_ypologismos_with_vivlio(parstatiko_agoras):
    """
    Συγκρίνει τον υπολογισμό με τα δεδομένα του βιβλίου.
    Επιστρέφει {ok: bool, differences: list}
    """
    yp = get_ypologismos(parstatiko_agoras)
    if not yp:
        return {'ok': False, 'error': 'Δεν βρέθηκε υπολογισμός'}

    with get_db() as conn:
        # Πάρε κινήσεις από το βιβλίο για το ίδιο παραστατικό αγοράς
        kiniseis = conn.execute('''
            SELECT k.tipos, k.posotita, k.yliko_id, y.onoma, y.monada_metrisis
            FROM kiniseis k
            JOIN ylika y ON k.yliko_id = y.id
            WHERE k.arithmos_parstatikos=? OR k.yliko_id IN (
                SELECT yliko_id FROM ypologismos_grammes WHERE ypologismos_id=?
            )
        ''', (parstatiko_agoras, yp['id'])).fetchall()

        # Ομαδοποίηση ανά υλικό
        vivlio = {}
        for k in kiniseis:
            yid = k['yliko_id']
            if yid not in vivlio:
                vivlio[yid] = {'onoma': k['onoma'], 'monada': k['monada_metrisis'],
                               'agores': 0, 'katanalosis': 0, 'epistrofes': 0}
            if k['tipos'] == 'ΕΙΣΑΓΩΓΗ':
                vivlio[yid]['agores'] += k['posotita']
            elif k['tipos'] == 'ΚΑΤΑΝΑΛΩΣΗ':
                vivlio[yid]['katanalosis'] += k['posotita']
            elif k['tipos'] in ('ΕΠΙΣΤΡΟΦΗ', 'ΕΞΑΓΩΓΗ'):
                vivlio[yid]['epistrofes'] += k['posotita']

        differences = []
        for g in yp['grammes']:
            yid = g['yliko_id']
            v = vivlio.get(yid, {})
            kat_vivlio = v.get('katanalosis', 0) or (v.get('agores', 0) - v.get('epistrofes', 0))
            kat_yp = g['posotita_katanalosis']

            if abs(kat_vivlio - kat_yp) > 0.001:
                differences.append({
                    'yliko_onoma': g['yliko_onoma'],
                    'monada': g['monada_metrisis'],
                    'katanalosi_ypologistis': kat_yp,
                    'katanalosi_vivliou': kat_vivlio,
                    'diafora': round(kat_yp - kat_vivlio, 3)
                })

        return {'ok': len(differences) == 0, 'differences': differences}
