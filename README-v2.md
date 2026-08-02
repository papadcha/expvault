# ExpVault — Πρόσθετα του branch `v2`

Αυτό το αρχείο περιγράφει **μόνο τις διαφορές** πάνω από τον κύριο [README.md](README.md)
στο branch `v2`. Δεν έχει κυκλοφορήσει ακόμα ως GitHub release — ενεργή ανάπτυξη.

Δομή: `main` = σταθερή γραμμή (auto-update, μόνο διορθώσεις λαθών/αναβαθμίσεις εξαρτήσεων).
`v2` = όλη η νέα ανάπτυξη, χωρίς δημοσίευση release μέχρι να ωριμάσει και να γίνει merge.

---

## Νέο: Εισαγωγή παραστατικών από JSON/CSV (φωτογραφία μέσω Claude/Gemini)

Εναλλακτικό στο PDF import, για παραστατικά που υπάρχουν μόνο σε χαρτί. Ο χειριστής ανεβάζει
φωτογραφία σε Claude ή Gemini (δωρεάν, χωρίς API key), παίρνει πίσω δομημένο JSON/CSV με
συγκεκριμένο σχήμα, και το εισάγει στο ExpVault — ίδιο preview/edit/submit flow με το PDF import.

Αναλυτικά: **[ΟΔΗΓΟΣ_ΧΡΗΣΗΣ-v2.md](ΟΔΗΓΟΣ_ΧΡΗΣΗΣ-v2.md)**.

### Νέα αρχεία / αρχιτεκτονική

| Αρχείο | Ρόλος |
|--------|-------|
| `backend/import_data.py` | Parsing JSON (ανεκτικό σε ```json fences, ISO ημερομηνίες, δεκαδικό κόμμα) και CSV (auto delimiter, ομαδοποίηση ανά παραστατικό) — φάκελος και .zip επίσης |
| `js/pdf-import.js` | Επεκτάθηκε: batch queue (`_loadImportResult`/`_showImportQueueItem`/`nextImportQueueItem`), fuzzy-match προειδοποίηση διπλότυπου υλικού (`_findCloseYlikoMatch`, Levenshtein), skip-and-next στο διπλοεγγραφή modal |

### Νέες bridge εντολές

- `parse_import_data` — δέχεται path σε αρχείο `.json`/`.csv`/`.zip` ή φάκελο, επιστρέφει
  `{items: [...], errors: [...]}` (πάντα λίστα, ακόμα κι όταν είναι ένα παραστατικό)

### Σχήμα JSON/CSV

Δείτε το πλήρες σχήμα (με το προαιρετικό πεδίο `agora_ref` για σωστό matching αγοράς/επιστροφής
σε batch import) στο [ΟΔΗΓΟΣ_ΧΡΗΣΗΣ-v2.md](ΟΔΗΓΟΣ_ΧΡΗΣΗΣ-v2.md#το-πλήρες-σχήμα-json).

---

## Fixes backported και στο main (v1.1.12)

Κατά την ανάπτυξη αυτού του feature εντοπίστηκε συστημικό bug σε 8 σημεία του
`backend/database.py`: αναζητήσεις/διαγραφές παραστατικού με exact-match χωρίς κανονικοποίηση
παύλας (`_clean_parst`), ενώ η αποθήκευση πάντα κανονικοποιεί. Αποτέλεσμα: αριθμός παραστατικού
με παύλα (π.χ. `ΔΙΧΝ-19586`) απέτυχε σιωπηλά να ταιριάξει με το ήδη αποθηκευμένο `ΔΙΧΝ 19586` —
σε έλεγχο διπλοεγγραφής, σύνδεση επιστροφής/αγοράς, και διαγραφή παραστατικού. Προϋπήρχε ήδη
στο v1.1.11, οπότε διορθώθηκε **και στα δύο branches** (v1.1.12 στο main, ίδιο fix εδώ).

---

## Αλλαγή: ενιαία παλέτα κατάστασης (presence / λήξη άδειας / downgrade)

Τα badges κατάστασης (ποιος άλλος είναι online, λήξη άδειας αγοράς, ασφαλές downgrade
έκδοσης) πέρασαν από gradient pills και πέντε ασύνδετες hex-παλέτες σε ένα ενιαίο, flat
outline+fill+font σύστημα — ίδια ακριβώς χρώματα με το αδερφό project lab-galatista.

### Νέα tokens (`css/app.css` `:root`)

| Token | Τιμή | Χρήση |
|---|---|---|
| `--status-ok` | `#16a34a` | ήσυχη κατάσταση (πράσινο) |
| `--status-ok-light` | `#22c55e` | version-history "ασφαλές downgrade" |
| `--status-warn-light` | `#f59e0b` | λήξη άδειας 31–90 ημέρες |
| `--status-warn` | `#d97706` | λήξη άδειας 16–30 ημέρες |
| `--status-danger-light` | `#ef4444` | λήξη άδειας 1–15 ημέρες / "urgent" |
| `--status-danger` | `#dc2626` | ήδη ληγμένη άδεια / "expired" / γνωστό πρόβλημα σχήματος |
| `--status-neutral` | `#94a3b8` | χωρίς καταχωρημένη ημ. λήξης |

Ξεχωριστά από τα `--success`/`--danger`, που παραμένουν αμετάβλητα (κουμπιά, στήλες +/- σε
πίνακες) — δεν είναι μέρος αυτού του status-signaling συστήματος.

### Νέα βαθμίδα: `expired`, ξεχωριστή από `urgent`

`.adeia-strip` (sidebar) και το `splash.html`'s `.tier-*` είχαν 5 βαθμίδες, με `urgent` να
καλύπτει ΚΑΙ "λήγει σε λίγες μέρες" ΚΑΙ "ήδη έληξε" με το ίδιο χρώμα. Έγιναν 6, split στο
`js/adeies.js` (`days_left < 0` → `adeia-strip-expired`) και στην tier-λογική του `splash.html`.

### Επηρεαζόμενα αρχεία

| Αρχείο | Αλλαγή |
|---|---|
| `css/app.css` | 7 νέα `--status-*` tokens· `.sidebar-presence-badge`/`.adeia-strip`/`#presence-section-box` gradient→flat· νέο tier `.adeia-strip-expired` |
| `js/adeies.js` | split `urgent`/`expired` στον υπολογισμό tier |
| `splash.html` | ίδιο split + flat `.tier-*` styling |
| `js/version-notice.js` | presence-list κάρτες (`ME_GREEN`/`OTHER_RED`), version-history list, πάνω banner "γνωστό πρόβλημα σχήματος" — Chakra UI/pastel hex → `--status-*`-ισοδύναμα |
