# ExpVault — Βιβλίο Εκρηκτικών Υλών

Εφαρμογή διαχείρισης βιβλίου αγοράς και κατανάλωσης εκρηκτικών υλών λατομείου. Παράγει νόμιμη εκτύπωση 2 σελίδων (αγορές/επιστροφές + καταναλώσεις) και υποστηρίζει αυτόματη εισαγωγή από PDF τιμολόγια Προμηθευτή/EpsilonNet.

---

## Αρχιτεκτονική

```
Electron (UI)  ←→  Python IPC Bridge (stdin/stdout JSON)  ←→  SQLite
```

| Αρχείο | Ρόλος |
|--------|-------|
| `main.js` | Electron main process, spawns bridge.py |
| `preload.js` | Exposes `window.api` στο renderer |
| `index.html` | SPA frontend (root του project) |
| `backend/bridge.py` | Python IPC handler |
| `backend/database.py` | SQLite operations |
| `backend/exports.py` | PDF/Excel export |
| `backend/pdf_parser.py` | EpsilonNet PDF parser |
| `backend/expvault.db` | Βάση δεδομένων |

---

## Προαπαιτούμενα

### Linux (Arch/Ubuntu/Debian)

```bash
# Node.js & Electron
sudo pacman -S nodejs npm           # Arch
sudo apt install nodejs npm         # Ubuntu/Debian
npm install -g electron

# Python
sudo pacman -S python python-pip    # Arch
sudo apt install python3 python3-pip  # Ubuntu/Debian

# Python βιβλιοθήκες
pip install pypdf reportlab openpyxl --break-system-packages

# Fonts (για PDF export)
sudo pacman -S ttf-liberation       # Arch
sudo apt install fonts-liberation   # Ubuntu/Debian
# Προαιρετικά: ttf-jetbrains-mono, ttc-iosevka
```

### Windows

```powershell
# Node.js: κατέβασε από https://nodejs.org
npm install -g electron

# Python: κατέβασε από https://python.org
pip install pypdf reportlab openpyxl

# Fonts: εγκατάσταση Liberation Fonts από https://github.com/liberationfonts/liberation-fonts
```

### macOS

```bash
# Homebrew (αν δεν υπάρχει): https://brew.sh
brew install node python

# Electron
npm install -g electron

# Python βιβλιοθήκες
pip3 install pypdf reportlab openpyxl

# Fonts
brew install --cask font-liberation
# Προαιρετικά: brew install --cask font-jetbrains-mono
```

---

## Εγκατάσταση & Εκκίνηση

```bash
git clone <repo-url>
cd expvault
npm install
electron .
```

---

## Βάση Δεδομένων

| Πίνακας | Περιγραφή |
|---------|-----------|
| `ylika` | Είδη εκρηκτικών υλών |
| `promitheftes` | Προμηθευτές |
| `adeies` | Άδειες + εκδούσα αρχή |
| `kiniseis` | Κινήσεις βιβλίου |
| `auxon_counter` | Αυξών αριθμός κινήσεων |
| `ypologismos` | Προσωρινοί υπολογισμοί επιστροφής/κατανάλωσης |
| `ypologismos_grammes` | Γραμμές υπολογισμού ανά υλικό |

### Τύποι κινήσεων (`kiniseis.tipos`)

| Τύπος | Περιγραφή |
|-------|-----------|
| `ΕΙΣΑΓΩΓΗ` | Αγορά από Προμηθευτή (αυτόματα ή χειροκίνητα) |
| `ΚΑΤΑΝΑΛΩΣΗ` | Κατανάλωση (χειροκίνητη από χειριστή) |
| `ΕΠΙΣΤΡΟΦΗ` | Επιστροφή (ΔΑ Επιχείρησης ή πιστωτικό Προμηθευτή) |

---

## Ροή Εργασίας

### Σενάριο 1: Αγορά + Κατανάλωση → Επιστροφή

1. Εισαγωγή PDF τιμολογίου αγοράς → `ΕΙΣΑΓΩΓΗ`
2. Χειροκίνητη καταχώρηση κατανάλωσης → `ΚΑΤΑΝΑΛΩΣΗ`
3. **Υπολογιστής**: Επιστροφή = Αγορά − Κατανάλωση → παράγει PDF για έκδοση ΔΑ
4. Εισαγωγή PDF πιστωτικού/ΔΑ επιστροφής → `ΕΠΙΣΤΡΟΦΗ`

### Σενάριο 2: Αγορά + Επιστροφή → Κατανάλωση

1. Εισαγωγή PDF τιμολογίου αγοράς → `ΕΙΣΑΓΩΓΗ`
2. Εισαγωγή PDF πιστωτικού επιστροφής → `ΕΠΙΣΤΡΟΦΗ`
3. **Υπολογιστής**: Κατανάλωση = Αγορά − Επιστροφή (αυτόματος υπολογισμός)

---

## Οδηγός Χρήσης

> Αναλυτικός οδηγός: **[ΟΔΗΓΟΣ_ΧΡΗΣΗΣ.md](ΟΔΗΓΟΣ_ΧΡΗΣΗΣ.md)**

### Σύντομη επισκόπηση λειτουργιών

| Σελίδα | Λειτουργία |
|--------|-----------|
| **Παράμετροι** | Ορισμός ειδών εκρηκτικών, προμηθευτών, αδειών (υποχρεωτικό πριν οποιαδήποτε κίνηση) |
| **Εισαγωγή PDF** | Αυτόματη ανάλυση τιμολογίων EpsilonNet/NITROCHEM → καταχώρηση ΕΙΣΑΓΩΓΗ/ΕΠΙΣΤΡΟΦΗ |
| **Βιβλίο Κινήσεων** | Χειροκίνητη καταχώρηση/επεξεργασία/διαγραφή κάθε κίνησης |
| **Υπολογισμός** | Σενάριο 1: Αγορά−Κατανάλωση=Επιστροφή · Σενάριο 2: Αγορά−Επιστροφή=Κατανάλωση + εκτύπωση Δελτίου |
| **Παραστατικά** | Ανάθεση αρ. παραστατικού σε εκκρεμείς επιστροφές, μετονομασία, διαγραφή (με cascade) |
| **Εκτύπωση / Εξαγωγή** | Βιβλίο Κινήσεων (PDF/Excel/Word) · Κατάσταση Αγορών (Excel) · Δελτίο Δραστηριότητας (Excel/PDF) |
| **Πρότυπα PDF** | Εκπαίδευση αναγνωρίσεων για νέους προμηθευτές μέσω επιλογής τιμών στο raw text |
| **Πίνακας Ελέγχου** | Έλεγχος ισορροπίας (Αγορές = Καταναλώσεις + Επιστροφές), τελευταίες κινήσεις |
| **Αποθέματα** | Τρέχον απόθεμα ανά υλικό |

### Τυπική ημερήσια ροή

```
Λήψη τιμολογίου PDF
  └→ Εισαγωγή PDF → έλεγχος → Καταχώρηση Όλων
        └→ (αργότερα) Υπολογιστής → Δελτίο PDF → Εξαγωγή/Υποβολή
```

---

## PDF Parser (EpsilonNet)

**Αναγνωρίζει αυτόματα:**
- Ημερομηνία, αριθμό παραστατικού
- Αριθμό άδειας (πριν από `Δ.Α. ...`)
- Εκδούσα αρχή (`ΔΙΕΥΘΥΝΣΗ ΑΣΦΑΛΕΙΑΣ` κ.ά.)
- Προμηθευτή (Προμηθευτής για αγορές, Επιχείρηση για επιστροφές)
- Τύπο εγγράφου: `Τιμολόγιο Πώλησης` → `ΕΙΣΑΓΩΓΗ`, `Πιστωτικό Τιμολόγιο` → `ΕΠΙΣΤΡΟΦΗ`
- Υλικά με ποσότητα και μονάδα

**Μορφή γραμμής EpsilonNet:**
```
ΤΙΜΗ ΑΞΙΑ ΚΩΔΙΚΟΣ ΠΕΡΙΓΡΑΦΗ ΜΜ ΠΟΣΟΤΗΤΑ 0,00
π.χ.: 1,30 2.600,00 40000000 ΠΕΤΡΑΜΜΩΝΙΤΗΣ (AN-FO) Κιλ 2.000,000 0,00
```

---

## PDF Export (Βιβλίο)

Εξάγει **2 σελίδες landscape A4** με επιλογή font:

**Σελίδα 1 — Αγορές/Επιστροφές:**
`Α/Α | Αρ.Άδ./Εκδ.Αρχή | [υλικά] | Ημερ.Αγ./Αρ.Δελτ. | Στοιχεία Προμηθευτή`

**Σελίδα 2 — Καταναλώσεις:**
`Ημερ.Εισαγ.Αποθ. | Ημερ.Κατανάλ. | [υλικά] | Παρατηρήσεις`

- Δυναμικές στήλες ανά υλικό
- Επιστροφές με κόκκινο text
- Αυτόματος υπολογισμός κατανάλωσης (Αγορά − Επιστροφή)
- Επιλογή font: Iosevka / JetBrains Mono / Liberation Mono
- Apple-like palette: #CDD5DB τίτλος, #E4E9ED headers, #F4F6F8 zebra

---

## Εκκρεμή (TODO)

- [ ] Καλύτερο UX στα "Είδη Εκρηκτικών"
- [ ] Εξαγωγή σε .docx
- [ ] Banner εκκρεμότητας + καταχώρηση από Υπολογισμό στο Βιβλίο
- [ ] Parser δελτίου επιστροφής Επιχείρησης
- [ ] Διαφοροποίηση ΔΑ Επιχείρησης από προμηθευτή αγοράς
- [ ] Αποθήκευση προτίμησης font

---

## Χρήσιμες Εντολές

```bash
# Καθαρισμός Electron cache
rm -rf ~/.config/expvault

# Migration βάσης (νέοι τύποι kiniseis)
cd backend && python3 -c "
import sqlite3
conn = sqlite3.connect('expvault.db')
conn.executescript('''
  PRAGMA foreign_keys=OFF;
  CREATE TABLE kiniseis_new (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    auxon_arithmos INTEGER NOT NULL,
    imerominia TEXT NOT NULL,
    tipos TEXT NOT NULL CHECK(tipos IN (\"ΕΙΣΑΓΩΓΗ\",\"ΚΑΤΑΝΑΛΩΣΗ\",\"ΕΠΙΣΤΡΟΦΗ\",\"ΕΞΑΓΩΓΗ\")),
    yliko_id INTEGER NOT NULL REFERENCES ylika(id),
    posotita REAL NOT NULL CHECK(posotita > 0),
    arithmos_parstatikos TEXT,
    adeia_id INTEGER REFERENCES adeies(id),
    promitheftis_id INTEGER REFERENCES promitheftes(id),
    paratirishis TEXT,
    ypografi TEXT,
    created_at TEXT DEFAULT (datetime(\"now\"))
  );
  INSERT INTO kiniseis_new SELECT * FROM kiniseis;
  DROP TABLE kiniseis;
  ALTER TABLE kiniseis_new RENAME TO kiniseis;
  PRAGMA foreign_keys=ON;
''')
conn.commit()
conn.close()
"

# Deploy (αντιγράφει από ~/Downloads και κάνει git push)
./deploy.sh "Περιγραφή αλλαγής"
```
