import re
import sqlite3
from contextlib import contextmanager
from datetime import datetime

def _clean_parst(s):
    """Κανονικοποίηση αρ. παραστατικού: αφαίρεση παύλας, π.χ. 'ΔΙΧΝ-19586' → 'ΔΙΧΝ 19586'."""
    if not s:
        return s
    return re.sub(r'\s*[-–]\s*', ' ', s).strip()

NOMIKES_KATIGORIES = [
    'Πυρίτιδα & Δυναμιτίδα', 'ANFO', 'Slurries', 'Γαλακτώματα',
    'Ζελατοδυναμίτιδα', 'Καψύλλια κοινά', 'Καψύλλια NONEL', 'Καψύλλια ηλεκτρικά',
    'Θρυαλλίδα κοινή', 'Θρυαλλίδα ακαριαία', 'Λοιπά εκρηκτικά',
]

MONADES_NOMIKON_KATIGORION = {
    'Πυρίτιδα & Δυναμιτίδα': 'kg',
    'ANFO':                   'kg',
    'Slurries':               'kg',
    'Γαλακτώματα':           'kg',
    'Ζελατοδυναμίτιδα':       'kg',
    'Καψύλλια κοινά':        'τεμ',
    'Καψύλλια NONEL':        'τεμ',
    'Καψύλλια ηλεκτρικά':    'τεμ',
    'Θρυαλλίδα κοινή':       'm',
    'Θρυαλλίδα ακαριαία':    'm',
    'Λοιπά εκρηκτικά':        'kg',
}

def classify_nomiki_katigoria(onoma):
    """Νόμιμη κατηγορία εκρηκτικού βάσει περιγραφής (βλ. κατηγοριες_εκρηκτικων.txt).
    ΗΛΕΚΤΡ ελέγχεται πρώτο γιατί 'ΗΛΕΚΤΡΙΚΟΙ ΠΥΡΟΚΡΟΤΗΤΕΣ' περιέχει και ΠΥΡΟΚΡ."""
    if not onoma:
        return None
    o = onoma.upper()
    if 'ΣΑΚΟΥΛ' in o or 'ΠΕΝΣ' in o or 'CRIMPER' in o:
        return None
    if 'SLURR' in o:
        return 'Slurries'
    if 'EM-EX' in o or 'EMEX' in o or 'ΓΑΛΑΚΤΩΜ' in o:
        return 'Γαλακτώματα'
    if 'POLADYN' in o or 'ΖΕΛΑΤ' in o:
        return 'Ζελατοδυναμίτιδα'
    if 'AN-FO' in o or 'ANFO' in o or 'ΠΕΤΡΑΜΜΩΝ' in o:
        return 'ANFO'
    if 'ΠΥΡΙΤ' in o or 'ΔΥΝΑΜΙΤ' in o:
        return 'Πυρίτιδα & Δυναμιτίδα'
    if 'ΗΛΕΚΤΡ' in o:
        return 'Καψύλλια ηλεκτρικά'
    if 'NONEL' in o:
        return 'Καψύλλια NONEL'
    if 'ΚΟΙΝΟΙ' in o or 'ΠΥΡΟΚΡ' in o:
        return 'Καψύλλια κοινά'
    if 'ΑΚΑΡ' in o:
        return 'Θρυαλλίδα ακαριαία'
    if 'ΒΡΑΔΥΚ' in o:
        return 'Θρυαλλίδα κοινή'
    return 'Λοιπά εκρηκτικά'

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
        # Pre-flight migration: adeia_ylika παλιό σχήμα (yliko_id) → διαγράφεται και
        # ξαναδημιουργείται παρακάτω με nomiki_katigoria. Πρέπει να τρέξει πριν το CREATE TABLE.
        # Οι παλιές εγκεκριμένες ποσότητες σώζονται πρώτα (αθροιστικά ανά νόμιμη κατηγορία,
        # μέσω classify_nomiki_katigoria στο όνομα του υλικού) και ξαναγράφονται μετά το
        # CREATE TABLE παρακάτω — αλλιώς χάνονται οριστικά σε κάθε upgrade/restore παλιάς βάσης.
        migrated_adeia_ylika = []
        try:
            cols = [r[1] for r in conn.execute("PRAGMA table_info(adeia_ylika)").fetchall()]
            if cols and 'yliko_id' in cols:
                old_rows = conn.execute("""
                    SELECT ay.adeia_id, y.onoma, ay.egekrimeni_posotita
                    FROM adeia_ylika ay JOIN ylika y ON ay.yliko_id = y.id
                """).fetchall()
                aggregated = {}
                for adeia_id, onoma, posotita in old_rows:
                    key = (adeia_id, classify_nomiki_katigoria(onoma))
                    aggregated[key] = aggregated.get(key, 0.0) + posotita
                migrated_adeia_ylika = [(adeia_id, kat, posot) for (adeia_id, kat), posot in aggregated.items()]
                conn.execute("DROP TABLE adeia_ylika")
        except Exception:
            pass

        # Βασικό σχήμα (πλήρες, με όλες τις στήλες που έχουν προστεθεί μέχρι σήμερα).
        # Πρέπει να τρέξει ΠΡΙΝ τα υπόλοιπα migrations, ώστε PRAGMA table_info να βρίσκει πάντα
        # τους πίνακες σε νέες εγκαταστάσεις (αλλιώς τα ALTER TABLE παρακάτω αποτυγχάνουν σιωπηλά).
        conn.executescript('''
            CREATE TABLE IF NOT EXISTS ylika (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                onoma TEXT NOT NULL,
                diatomi_mm INTEGER,
                monada_metrisis TEXT NOT NULL,
                paratirishis TEXT,
                kategoria TEXT,
                export_group TEXT,
                nomiki_katigoria TEXT,
                UNIQUE(onoma, diatomi_mm)
            );

            CREATE TABLE IF NOT EXISTS promitheftes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                onoma TEXT NOT NULL UNIQUE,
                syntomografia TEXT
            );

            CREATE TABLE IF NOT EXISTS adeies (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                arithmos_adeias TEXT NOT NULL UNIQUE,
                perigrafi TEXT,
                syntomografia_ekdousas TEXT,
                imerominia_ekdosis TEXT,
                imerominia_lixis TEXT
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
                created_at TEXT DEFAULT (datetime('now')),
                agora_ref TEXT
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

            CREATE TABLE IF NOT EXISTS adeia_ylika (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                adeia_id INTEGER NOT NULL REFERENCES adeies(id) ON DELETE CASCADE,
                nomiki_katigoria TEXT NOT NULL,
                egekrimeni_posotita REAL NOT NULL,
                UNIQUE(adeia_id, nomiki_katigoria)
            );

            INSERT OR IGNORE INTO auxon_counter(id, next_val) VALUES (1, 1);
        ''')

        if migrated_adeia_ylika:
            conn.executemany(
                "INSERT INTO adeia_ylika (adeia_id, nomiki_katigoria, egekrimeni_posotita) VALUES (?, ?, ?)",
                migrated_adeia_ylika
            )

        # ── Migrations για παλιότερες εγκαταστάσεις (πίνακες προϋπάρχουν χωρίς κάποια στήλη) ──

        # Migration: agora_ref για επιστροφές
        try:
            cols = [r[1] for r in conn.execute("PRAGMA table_info(kiniseis)").fetchall()]
            if cols and 'agora_ref' not in cols:
                conn.execute("ALTER TABLE kiniseis ADD COLUMN agora_ref TEXT")
                # Auto-migration: κάθε ΕΠΙΣΤΡΟΦΗ → αμέσως προηγούμενη αγορά με κοινά υλικά
                epistrofes = conn.execute(
                    "SELECT id, arithmos_parstatikos, auxon_arithmos, yliko_id FROM kiniseis WHERE tipos='ΕΠΙΣΤΡΟΦΗ' ORDER BY auxon_arithmos"
                ).fetchall()
                for epi in epistrofes:
                    agora = conn.execute(
                        """SELECT arithmos_parstatikos FROM kiniseis
                           WHERE tipos='ΕΙΣΑΓΩΓΗ' AND yliko_id=? AND auxon_arithmos<?
                           ORDER BY auxon_arithmos DESC LIMIT 1""",
                        (epi[3], epi[2])
                    ).fetchone()
                    if agora:
                        conn.execute("UPDATE kiniseis SET agora_ref=? WHERE id=?", (agora[0], epi[0]))
        except Exception:
            pass
        # Migration: agora_ref για καταναλώσεις (χωρίς παραστατικό)
        try:
            katanalosis = conn.execute(
                "SELECT id, yliko_id, auxon_arithmos FROM kiniseis WHERE tipos='ΚΑΤΑΝΑΛΩΣΗ' AND (agora_ref IS NULL OR agora_ref='') ORDER BY auxon_arithmos"
            ).fetchall()
            for kat in katanalosis:
                agora = conn.execute(
                    """SELECT arithmos_parstatikos FROM kiniseis
                       WHERE tipos='ΕΙΣΑΓΩΓΗ' AND yliko_id=? AND auxon_arithmos<?
                         AND arithmos_parstatikos IS NOT NULL AND arithmos_parstatikos!=''
                       ORDER BY auxon_arithmos DESC LIMIT 1""",
                    (kat[1], kat[2])
                ).fetchone()
                if agora:
                    conn.execute("UPDATE kiniseis SET agora_ref=? WHERE id=?", (agora[0], kat[0]))
        except Exception:
            pass
        # Migration: kategoria στα ylika
        try:
            cols = [r[1] for r in conn.execute("PRAGMA table_info(ylika)").fetchall()]
            if cols and 'kategoria' not in cols:
                conn.execute("ALTER TABLE ylika ADD COLUMN kategoria TEXT")
        except Exception:
            pass
        # Migration: export_group στα ylika
        try:
            cols = [r[1] for r in conn.execute("PRAGMA table_info(ylika)").fetchall()]
            if cols and 'export_group' not in cols:
                conn.execute("ALTER TABLE ylika ADD COLUMN export_group TEXT")
                # Αυτόματη συμπλήρωση από kategoria + όνομα
                conn.execute("""UPDATE ylika SET export_group=CASE
                    WHEN kategoria='SNAPLINE' THEN 'NONEL SNAPLINE'
                    WHEN kategoria='LP'       THEN 'NONEL LP'
                    WHEN kategoria='UNIDET'   THEN 'NONEL UNIDET'
                    WHEN onoma LIKE '%POLADYN%'        THEN 'POLADYN'
                    WHEN onoma LIKE '%ΘΡΥΑΛΛΙΔΑ%'     THEN 'ΘΡΥΑΛΛΙΔΑ'
                    WHEN onoma LIKE '%ΠΥΡΟΚΡΟΤΗΤΕΣ%'  THEN 'ΠΥΡΟΚΡΟΤΗΤΕΣ'
                    ELSE NULL END""")
        except Exception:
            pass
        # Migration: nomiki_katigoria στα ylika (νόμιμη κατηγορία για Δελτίο Δραστηριότητας)
        try:
            cols = [r[1] for r in conn.execute("PRAGMA table_info(ylika)").fetchall()]
            if cols and 'nomiki_katigoria' not in cols:
                conn.execute("ALTER TABLE ylika ADD COLUMN nomiki_katigoria TEXT")
                for r in conn.execute("SELECT id, onoma FROM ylika").fetchall():
                    conn.execute("UPDATE ylika SET nomiki_katigoria=? WHERE id=?",
                                 (classify_nomiki_katigoria(r[1]), r[0]))
        except Exception:
            pass
        # Migration: διαχωρισμός καψυλλίων + μετονομασία Ζελατινοδυναμιτίδα → Ζελατοδυναμίτιδα
        try:
            for r in conn.execute(
                """SELECT id, onoma FROM ylika WHERE nomiki_katigoria IN
                   ('Καψύλια κοινά + NONEL', 'Ζελατινοδυναμιτίδα')"""
            ).fetchall():
                conn.execute("UPDATE ylika SET nomiki_katigoria=? WHERE id=?",
                             (classify_nomiki_katigoria(r[1]), r[0]))
        except Exception:
            pass
        # Migration: syntomografia στους promitheftes
        try:
            cols = [r[1] for r in conn.execute("PRAGMA table_info(promitheftes)").fetchall()]
            if cols and 'syntomografia' not in cols:
                conn.execute("ALTER TABLE promitheftes ADD COLUMN syntomografia TEXT")
        except Exception:
            pass
        # Migration: εκδούσα αρχή + ημερομηνίες άδειας
        try:
            cols = [r[1] for r in conn.execute("PRAGMA table_info(adeies)").fetchall()]
            if cols and 'syntomografia_ekdousas' not in cols:
                conn.execute("ALTER TABLE adeies ADD COLUMN syntomografia_ekdousas TEXT")
            if cols and 'imerominia_ekdosis' not in cols:
                conn.execute("ALTER TABLE adeies ADD COLUMN imerominia_ekdosis TEXT")
            if cols and 'imerominia_lixis' not in cols:
                conn.execute("ALTER TABLE adeies ADD COLUMN imerominia_lixis TEXT")
        except Exception:
            pass

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

def add_yliko(onoma, diatomi_mm, monada, paratirishis, export_group=None, export_subgroup=None, nomiki_katigoria=None):
    with get_db() as conn:
        existing = conn.execute(
            "SELECT id FROM ylika WHERE UPPER(onoma)=UPPER(?) AND (diatomi_mm IS ? OR diatomi_mm=?)",
            (onoma.upper(), diatomi_mm, diatomi_mm)
        ).fetchone()
        if existing:
            return existing[0]
        nomiki_katigoria = nomiki_katigoria or classify_nomiki_katigoria(onoma)
        conn.execute(
            "INSERT INTO ylika(onoma,diatomi_mm,monada_metrisis,paratirishis,export_group,nomiki_katigoria) VALUES(?,?,?,?,?,?)",
            (onoma.upper(), diatomi_mm or None, monada, paratirishis or None, export_group, nomiki_katigoria))

def update_yliko(id, onoma, diatomi_mm, monada, paratirishis, export_group=None, export_subgroup=None, nomiki_katigoria=None):
    with get_db() as conn:
        nomiki_katigoria = nomiki_katigoria or classify_nomiki_katigoria(onoma)
        conn.execute(
            "UPDATE ylika SET onoma=?,diatomi_mm=?,monada_metrisis=?,paratirishis=?,export_group=?,nomiki_katigoria=? WHERE id=?",
            (onoma.upper(), diatomi_mm or None, monada, paratirishis or None, export_group, nomiki_katigoria, id))

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

def add_promitheftis(onoma, syntomografia=None):
    with get_db() as conn:
        conn.execute("INSERT INTO promitheftes(onoma, syntomografia) VALUES(?,?)", (onoma, syntomografia))

def update_promitheftis(id, onoma, syntomografia=None):
    with get_db() as conn:
        conn.execute("UPDATE promitheftes SET onoma=?, syntomografia=? WHERE id=?", (onoma, syntomografia, id))

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

def add_adeia(arithmos, perigrafi, syntomografia_ekdousas=None, imerominia_ekdosis=None, imerominia_lixis=None):
    with get_db() as conn:
        cur = conn.execute(
            "INSERT INTO adeies(arithmos_adeias,perigrafi,syntomografia_ekdousas,imerominia_ekdosis,imerominia_lixis) VALUES(?,?,?,?,?)",
            (arithmos, perigrafi or None, syntomografia_ekdousas, imerominia_ekdosis or None, imerominia_lixis or None)
        )
        return cur.lastrowid

def update_adeia(id, arithmos, perigrafi, syntomografia_ekdousas=None, imerominia_ekdosis=None, imerominia_lixis=None):
    with get_db() as conn:
        conn.execute(
            "UPDATE adeies SET arithmos_adeias=?,perigrafi=?,syntomografia_ekdousas=?,imerominia_ekdosis=?,imerominia_lixis=? WHERE id=?",
            (arithmos, perigrafi or None, syntomografia_ekdousas, imerominia_ekdosis or None, imerominia_lixis or None, id)
        )

def get_adeia_ylika(adeia_id):
    """Εγκεκριμένες ποσότητες ανά νόμιμη κατηγορία για μία άδεια, με χρησιμοποιημένη & υπόλοιπο.
    Χρησιμοποιημένη = ΕΙΣΑΓΩΓΗ − ΕΠΙΣΤΡΟΦΗ αθροιστικά για όλα τα υλικά της κατηγορίας."""
    with get_db() as conn:
        rows = conn.execute("""
            SELECT ay.id, ay.adeia_id, ay.nomiki_katigoria, ay.egekrimeni_posotita,
                   COALESCE(ks.xrisimopoiimeni, 0.0) as xrisimopoiimeni
            FROM adeia_ylika ay
            LEFT JOIN (
                SELECT k.adeia_id, y.nomiki_katigoria,
                       SUM(CASE WHEN k.tipos='ΕΙΣΑΓΩΓΗ' THEN k.posotita
                                WHEN k.tipos='ΕΠΙΣΤΡΟΦΗ' THEN -k.posotita
                                ELSE 0 END) as xrisimopoiimeni
                FROM kiniseis k
                JOIN ylika y ON k.yliko_id = y.id
                WHERE k.tipos IN ('ΕΙΣΑΓΩΓΗ','ΕΠΙΣΤΡΟΦΗ')
                GROUP BY k.adeia_id, y.nomiki_katigoria
            ) ks ON ks.adeia_id = ay.adeia_id AND ks.nomiki_katigoria = ay.nomiki_katigoria
            WHERE ay.adeia_id = ?
            ORDER BY ay.nomiki_katigoria
        """, (adeia_id,)).fetchall()
        result = []
        for r in rows:
            d = dict(r)
            d['monada_metrisis'] = MONADES_NOMIKON_KATIGORION.get(d['nomiki_katigoria'], '')
            result.append(d)
        return result

def get_adeia_katigoria_remaining(adeia_id, nomiki_katigoria):
    """Υπόλοιπο εγκεκριμένης ποσότητας για συγκεκριμένη άδεια + κατηγορία."""
    with get_db() as conn:
        row = conn.execute("""
            SELECT ay.egekrimeni_posotita,
                   COALESCE(ks.xrisimopoiimeni, 0.0) as xrisimopoiimeni
            FROM adeia_ylika ay
            LEFT JOIN (
                SELECT k.adeia_id, y.nomiki_katigoria,
                       SUM(CASE WHEN k.tipos='ΕΙΣΑΓΩΓΗ' THEN k.posotita
                                WHEN k.tipos='ΕΠΙΣΤΡΟΦΗ' THEN -k.posotita
                                ELSE 0 END) as xrisimopoiimeni
                FROM kiniseis k
                JOIN ylika y ON k.yliko_id = y.id
                WHERE k.tipos IN ('ΕΙΣΑΓΩΓΗ','ΕΠΙΣΤΡΟΦΗ')
                GROUP BY k.adeia_id, y.nomiki_katigoria
            ) ks ON ks.adeia_id = ay.adeia_id AND ks.nomiki_katigoria = ay.nomiki_katigoria
            WHERE ay.adeia_id = ? AND ay.nomiki_katigoria = ?
        """, (adeia_id, nomiki_katigoria)).fetchone()
        if not row:
            return None
        r = dict(row)
        r['nomiki_katigoria'] = nomiki_katigoria
        r['monada_metrisis']  = MONADES_NOMIKON_KATIGORION.get(nomiki_katigoria, '')
        r['ypoloipo'] = r['egekrimeni_posotita'] - r['xrisimopoiimeni']
        return r

def get_adeia_low_balance_alerts(adeia_id=None, threshold_multiplier=3.0):
    """Άδειες/κατηγορίες με υπόλοιπο κάτω από threshold_multiplier × τον μέσο όρο
    ποσότητας ανά αγορά (ΕΙΣΑΓΩΓΗ) της κατηγορίας. Κατηγορίες χωρίς ιστορικό
    αγορών αγνοούνται (δεν υπάρχει μέσος όρος για να κριθεί κατώφλι).
    Με adeia_id περιορίζεται σε μία άδεια (χρήση: αμέσως μετά από νέα καταχώρηση)."""
    with get_db() as conn:
        rows = conn.execute("""
            SELECT ay.adeia_id, a.arithmos_adeias, ay.nomiki_katigoria, ay.egekrimeni_posotita,
                   COALESCE(used.xrisimopoiimeni, 0.0) AS xrisimopoiimeni,
                   avg_purch.meso_oro AS meso_oro_agoras
            FROM adeia_ylika ay
            JOIN adeies a ON a.id = ay.adeia_id
            LEFT JOIN (
                SELECT k.adeia_id, y.nomiki_katigoria,
                       SUM(CASE WHEN k.tipos='ΕΙΣΑΓΩΓΗ' THEN k.posotita
                                WHEN k.tipos='ΕΠΙΣΤΡΟΦΗ' THEN -k.posotita
                                ELSE 0 END) as xrisimopoiimeni
                FROM kiniseis k JOIN ylika y ON k.yliko_id = y.id
                WHERE k.tipos IN ('ΕΙΣΑΓΩΓΗ','ΕΠΙΣΤΡΟΦΗ')
                GROUP BY k.adeia_id, y.nomiki_katigoria
            ) used ON used.adeia_id = ay.adeia_id AND used.nomiki_katigoria = ay.nomiki_katigoria
            LEFT JOIN (
                SELECT k.adeia_id, y.nomiki_katigoria, AVG(k.posotita) as meso_oro
                FROM kiniseis k JOIN ylika y ON k.yliko_id = y.id
                WHERE k.tipos='ΕΙΣΑΓΩΓΗ'
                GROUP BY k.adeia_id, y.nomiki_katigoria
            ) avg_purch ON avg_purch.adeia_id = ay.adeia_id AND avg_purch.nomiki_katigoria = ay.nomiki_katigoria
            WHERE (:adeia_id IS NULL OR ay.adeia_id = :adeia_id)
        """, {'adeia_id': adeia_id}).fetchall()

        alerts = []
        for row in rows:
            d = dict(row)
            if not d['meso_oro_agoras']:
                continue
            ypoloipo = d['egekrimeni_posotita'] - d['xrisimopoiimeni']
            if ypoloipo < threshold_multiplier * d['meso_oro_agoras']:
                alerts.append({
                    'adeia_id': d['adeia_id'],
                    'arithmos_adeias': d['arithmos_adeias'],
                    'nomiki_katigoria': d['nomiki_katigoria'],
                    'ypoloipo': round(ypoloipo, 3),
                    'meso_oro_agoras': round(d['meso_oro_agoras'], 3),
                    'monada_metrisis': MONADES_NOMIKON_KATIGORION.get(d['nomiki_katigoria'], ''),
                })
        return alerts

def set_adeia_katigoria(adeia_id, nomiki_katigoria, egekrimeni_posotita):
    with get_db() as conn:
        conn.execute("""
            INSERT INTO adeia_ylika(adeia_id, nomiki_katigoria, egekrimeni_posotita)
            VALUES(?,?,?)
            ON CONFLICT(adeia_id, nomiki_katigoria) DO UPDATE SET egekrimeni_posotita=excluded.egekrimeni_posotita
        """, (adeia_id, nomiki_katigoria, egekrimeni_posotita))

def delete_adeia_yliko(id):
    with get_db() as conn:
        conn.execute("DELETE FROM adeia_ylika WHERE id=?", (id,))

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
        SELECT k.*, y.onoma as yliko_onoma, y.diatomi_mm, y.monada_metrisis, y.export_group, y.nomiki_katigoria,
               p.onoma as promitheftis_onoma, p.syntomografia as promitheftis_syntomografia, a.arithmos_adeias, a.perigrafi as ekdousa_archi, a.syntomografia_ekdousas
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
               adeia_id, promitheftis_id, paratirishis, ypografi, agora_ref=None):
    arithmos_parstatikos = _clean_parst(arithmos_parstatikos)
    agora_ref = _clean_parst(agora_ref)
    # Δεν επιτρέπεται αποθήκευση αυτόματα υπολογισμένων καταναλώσεων
    if tipos == 'ΚΑΤΑΝΑΛΩΣΗ' and paratirishis == 'Αυτόματος υπολογισμός':
        raise ValueError("Απαγορεύεται η αποθήκευση αυτόματου υπολογισμού ως ΚΑΤΑΝΑΛΩΣΗ")
    auxon = next_auxon()
    with get_db() as conn:
        # Auto-link κατανάλωσης στην τελευταία αγορά του ίδιου υλικού
        if tipos == 'ΚΑΤΑΝΑΛΩΣΗ' and not agora_ref:
            last = conn.execute(
                """SELECT arithmos_parstatikos FROM kiniseis
                   WHERE tipos='ΕΙΣΑΓΩΓΗ' AND yliko_id=?
                     AND arithmos_parstatikos IS NOT NULL AND arithmos_parstatikos!=''
                   ORDER BY auxon_arithmos DESC LIMIT 1""",
                (yliko_id,)
            ).fetchone()
            if last:
                agora_ref = last[0]
        conn.execute('''
            INSERT INTO kiniseis(auxon_arithmos,imerominia,tipos,yliko_id,posotita,
                arithmos_parstatikos,adeia_id,promitheftis_id,paratirishis,ypografi,agora_ref)
            VALUES(?,?,?,?,?,?,?,?,?,?,?)
        ''', (auxon, imerominia, tipos, yliko_id, posotita,
              arithmos_parstatikos or None, adeia_id or None,
              promitheftis_id or None, paratirishis or None, ypografi or None, agora_ref or None))

def update_kinisi(id, imerominia, tipos, yliko_id, posotita, arithmos_parstatikos,
                  adeia_id, promitheftis_id, paratirishis, ypografi, agora_ref=None):
    arithmos_parstatikos = _clean_parst(arithmos_parstatikos)
    agora_ref = _clean_parst(agora_ref)
    with get_db() as conn:
        conn.execute('''
            UPDATE kiniseis SET imerominia=?,tipos=?,yliko_id=?,posotita=?,
                arithmos_parstatikos=?,adeia_id=?,promitheftis_id=?,paratirishis=?,ypografi=?,agora_ref=?
            WHERE id=?
        ''', (imerominia, tipos, yliko_id, posotita, arithmos_parstatikos or None,
              adeia_id or None, promitheftis_id or None,
              paratirishis or None, ypografi or None, agora_ref or None, id))

def update_agora_ref(arithmos_parstatikos, agora_ref):
    with get_db() as conn:
        conn.execute(
            "UPDATE kiniseis SET agora_ref=? WHERE arithmos_parstatikos=? AND tipos='ΕΠΙΣΤΡΟΦΗ'",
            (agora_ref or None, arithmos_parstatikos)
        )

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

def batch_update_parstatiko(old_parst, new_parst=None, new_date=None,
                            new_adeia_id=None, new_promitheftis_id=None, new_agora_ref=None):
    """Μαζική ενημέρωση παραστατικού σε όλες τις κινήσεις."""
    new_parst = _clean_parst(new_parst) if new_parst else new_parst
    sets, vals = [], []
    if new_parst:
        sets.append('arithmos_parstatikos=?'); vals.append(new_parst)
    if new_date:
        sets.append('imerominia=?'); vals.append(new_date)
    if new_adeia_id is not None:
        sets.append('adeia_id=?'); vals.append(new_adeia_id if new_adeia_id != '' else None)
    if new_promitheftis_id is not None:
        sets.append('promitheftis_id=?'); vals.append(new_promitheftis_id if new_promitheftis_id != '' else None)
    if not sets:
        return 0
    vals.append(old_parst)
    with get_db() as conn:
        conn.execute(f"UPDATE kiniseis SET {', '.join(sets)} WHERE arithmos_parstatikos=?", vals)
        n = conn.execute("SELECT changes()").fetchone()[0]
        # Ενημέρωση agora_ref σε επιστροφές εντός του ίδιου παραστατικού
        if new_agora_ref is not None:
            target = new_parst or old_parst
            conn.execute(
                "UPDATE kiniseis SET agora_ref=? WHERE arithmos_parstatikos=? AND tipos='ΕΠΙΣΤΡΟΦΗ'",
                (new_agora_ref or None, target)
            )
        # Αν αλλάζει το όνομα αγοράς, ενημέρωσε και agora_ref linked επιστροφών
        if new_parst and new_parst != old_parst:
            conn.execute(
                "UPDATE kiniseis SET agora_ref=? WHERE agora_ref=? AND tipos='ΕΠΙΣΤΡΟΦΗ'",
                (new_parst, old_parst)
            )
        return n

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
        if imerominia and not parstatiko:
            # Όταν υπάρχει parstatiko, αγνοούμε imerominia — οι επιστροφές
            # μπορεί να είναι σε διαφορετική ημερομηνία και βρίσκονται μέσω agora_ref
            sql += ' AND k.imerominia=?'; params.append(imerominia)
        if parstatiko:
            # Φίλτρο με agora_ref — συνδέει ΕΠΙΣΤΡΟΦΕΣ με την αγορά τους
            sql += """ AND (
                (k.tipos='ΕΙΣΑΓΩΓΗ' AND k.arithmos_parstatikos=?) OR
                (k.tipos='ΚΑΤΑΝΑΛΩΣΗ' AND k.arithmos_parstatikos=?) OR
                (k.tipos='ΕΠΙΣΤΡΟΦΗ' AND k.agora_ref=?)
            )"""
            params.extend([parstatiko, parstatiko, parstatiko])

        rows = conn.execute(sql, params).fetchall()
        if not rows:
            return {'ekkremotita': False}

        # Ομαδοποίηση ανά υλικό
        by_yliko = {}
        for r in rows:
            yid = r['yliko_id']
            t = r['tipos']
            rp = r['arithmos_parstatikos']

            if yid not in by_yliko:
                by_yliko[yid] = {
                    'yliko_id': yid,
                    'yliko_onoma': r['onoma'],
                    'monada': r['monada_metrisis'],
                    'imerominia': '',
                    'agores': 0, 'katanalosis': 0, 'epistrofes': 0
                }
            if t == 'ΕΙΣΑΓΩΓΗ':
                by_yliko[yid]['agores'] += r['posotita']
                if not by_yliko[yid]['imerominia']:
                    by_yliko[yid]['imerominia'] = r['imerominia']
            elif t == 'ΚΑΤΑΝΑΛΩΣΗ':
                by_yliko[yid]['katanalosis'] += r['posotita']
            elif t in ('ΕΠΙΣΤΡΟΦΗ', 'ΕΞΑΓΩΓΗ'):
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

def get_agores_with_pending_epistrofes():
    """Επιστρέφει αγορές που έχουν τουλάχιστον μία επιστροφή χωρίς παραστατικό (εκκρεμής)."""
    with get_db() as conn:
        rows = conn.execute('''
            SELECT k.arithmos_parstatikos, MIN(k.imerominia) as imerominia
            FROM kiniseis k
            WHERE k.tipos = 'ΕΙΣΑΓΩΓΗ'
              AND k.arithmos_parstatikos IS NOT NULL AND k.arithmos_parstatikos != ''
              AND EXISTS (
                SELECT 1 FROM kiniseis e
                WHERE e.tipos = 'ΕΠΙΣΤΡΟΦΗ'
                  AND e.agora_ref = k.arithmos_parstatikos
                  AND (e.arithmos_parstatikos IS NULL OR e.arithmos_parstatikos = '')
              )
            GROUP BY k.arithmos_parstatikos
            ORDER BY k.arithmos_parstatikos
        ''').fetchall()
        return [dict(r) for r in rows]

def assign_epistrofi_parstatiko(agora_ref, new_parstatiko, new_date=None):
    """Αναθέτει παραστατικό+ημερομηνία σε επιστροφές linked με αγορά που δεν έχουν ακόμα παραστατικό."""
    with get_db() as conn:
        if new_date:
            conn.execute(
                """UPDATE kiniseis SET arithmos_parstatikos=?, imerominia=?
                   WHERE tipos='ΕΠΙΣΤΡΟΦΗ' AND agora_ref=?
                     AND (arithmos_parstatikos IS NULL OR arithmos_parstatikos='')""",
                (new_parstatiko, new_date, agora_ref)
            )
        else:
            conn.execute(
                """UPDATE kiniseis SET arithmos_parstatikos=?
                   WHERE tipos='ΕΠΙΣΤΡΟΦΗ' AND agora_ref=?
                     AND (arithmos_parstatikos IS NULL OR arithmos_parstatikos='')""",
                (new_parstatiko, agora_ref)
            )
        return conn.execute("SELECT changes()").fetchone()[0]

def get_epistrofes_without_parstatiko(agora_ref):
    """Επιστρέφει επιστροφές χωρίς παραστατικό για συγκεκριμένη αγορά."""
    with get_db() as conn:
        rows = conn.execute('''
            SELECT k.id, k.auxon_arithmos, k.imerominia, k.posotita,
                   y.onoma as yliko_onoma, y.diatomi_mm, y.monada_metrisis
            FROM kiniseis k JOIN ylika y ON k.yliko_id = y.id
            WHERE k.tipos='ΕΠΙΣΤΡΟΦΗ' AND k.agora_ref=?
              AND (k.arithmos_parstatikos IS NULL OR k.arithmos_parstatikos='')
            ORDER BY k.auxon_arithmos
        ''', (agora_ref,)).fetchall()
        return [dict(r) for r in rows]

def get_kiniseis_by_parstatiko_yliko(arithmos_parstatikos, yliko_id):
    """Επιστρέφει τις κινήσεις ενός υλικού που ανήκουν σε ένα παραστατικό (αγορά + κατανάλωση + επιστροφή)."""
    with get_db() as conn:
        rows = conn.execute('''
            SELECT k.*, y.onoma as yliko_onoma, y.diatomi_mm, y.monada_metrisis,
                   p.onoma as promitheftis_onoma, a.arithmos_adeias
            FROM kiniseis k
            JOIN ylika y ON k.yliko_id = y.id
            LEFT JOIN promitheftes p ON k.promitheftis_id = p.id
            LEFT JOIN adeies a ON k.adeia_id = a.id
            WHERE k.yliko_id = ?
              AND (k.arithmos_parstatikos = ? OR k.agora_ref = ?)
            ORDER BY
              CASE k.tipos WHEN 'ΕΙΣΑΓΩΓΗ' THEN 1 WHEN 'ΚΑΤΑΝΑΛΩΣΗ' THEN 2 WHEN 'ΕΠΙΣΤΡΟΦΗ' THEN 3 ELSE 4 END,
              k.auxon_arithmos
        ''', (yliko_id, arithmos_parstatikos, arithmos_parstatikos)).fetchall()
        return [dict(r) for r in rows]

def delete_kiniseis_by_parstatiko(arithmos_parstatikos):
    """Διαγράφει όλες τις κινήσεις με συγκεκριμένο παραστατικό."""
    with get_db() as conn:
        conn.execute(
            "DELETE FROM kiniseis WHERE arithmos_parstatikos=?",
            (arithmos_parstatikos,)
        )

def delete_parstatiko_with_related(arithmos_parstatikos, include_agora_ref=True):
    """Διαγράφει παραστατικό + επιστροφές συνδεδεμένες μέσω agora_ref."""
    with get_db() as conn:
        conn.execute("DELETE FROM kiniseis WHERE arithmos_parstatikos=?", (arithmos_parstatikos,))
        if include_agora_ref:
            conn.execute("DELETE FROM kiniseis WHERE agora_ref=?", (arithmos_parstatikos,))

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
