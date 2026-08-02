# DONE — branch `v2`

Τεχνικό αρχείο ολοκληρωμένης δουλειάς σε αυτό το branch — κρατιέται για ιστορικό/αναφορά,
ίδιος σκοπός με το [`DONE.md`](DONE.md) του v1 αλλά ξεχωριστό γιατί τίποτα εδώ δεν έχει
κυκλοφορήσει ακόμα. Δείτε [`VERSIONS-v2.md`](VERSIONS-v2.md) για τη user-facing σύνοψη.

## Εισαγωγή παραστατικών από JSON/CSV/φάκελο/zip

Πλήρες εναλλακτικό στο PDF import: αντί για τοπικό OCR (αξιολογήθηκε και απορρίφθηκε — βλ.
παρακάτω), ο χειριστής ανεβάζει φωτογραφία παραστατικού σε ένα εξωτερικό vision LLM
(Claude/Gemini, δωρεάν web UI, χωρίς API key/κόστος) με ένα έτοιμο prompt, παίρνει πίσω
δομημένο JSON/CSV, και το εισάγει.

**Γιατί όχι τοπικό OCR (Tesseract):** σκέτη αναγνώριση χαρακτήρων χωρίς κατανόηση νοήματος —
χειρότερη ακρίβεια σε φωτογραφία χαρτιού (κλίση/φωτισμός) απ' ό,τι ένα vision LLM που ήδη
κάνει OCR+κατανόηση+δομημένη εξαγωγή μαζί. Θα χρειαζόταν επιπλέον bundling του Tesseract
binary + ελληνικά language data (μεγαλύτερος installer) και νέα regex/pattern-matching λογική
ειδικά για θορυβώδες OCR κείμενο — δουλειά για χειρότερο αποτέλεσμα.

**Backend** (`backend/import_data.py`, νέο αρχείο):
- `parse_json_multi(text)`: JSON object ή λίστα από objects. Ανεκτικό σε ` ```json ` markdown
  fences (τυπικό LLM output pattern) — strip πριν το `json.loads`.
- `parse_csv_multi(text)`: `csv.Sniffer` για auto-detect delimiter, ομαδοποίηση γραμμών ανά
  `(arithmos_parstatikou, tipos)` — όχι μόνο αριθμό (`__row_N__` fallback key αν λείπει ο
  αριθμός, ώστε κάθε τέτοια γραμμή να γίνεται δικό της "παραστατικό" αντί να συγχωνεύεται
  λάθος με το προηγούμενο). Αρχικά η ομαδοποίηση ήταν μόνο ανά αριθμό — αν δύο γραμμές
  μοιράζονταν τυχαία τον ίδιο αριθμό παραστατικού αλλά διαφορετικό `tipos` (π.χ. λάθος στο
  LLM output, ή ξαναχρησιμοποιημένος αριθμός εγγράφου), συγχωνεύονταν σιωπηλά και όλες οι
  γραμμές έπαιρναν τον τύπο της πρώτης — διορθώθηκε πριν προλάβει να εμφανιστεί σε πραγματική
  χρήση.
- `_norm_date`: δέχεται ISO (`YYYY-MM-DD`) εκτός από το κανονικό `DD/MM/YYYY` — τα LLMs
  μερικές φορές default σε ISO παρά τις οδηγίες στο prompt.
- `_norm_num`: δεκαδικό κόμμα ή τελεία, tolerant.
- `parse_folder`/`parse_zip`: μη-αναδρομικό για folder (μόνο top-level `.json`/`.csv`),
  οποιοδήποτε βάθος για zip (`zipfile.namelist()` filter). Per-file error isolation — ένα
  χαλασμένο αρχείο μέσα σε 10 δεν μπλοκάρει τα άλλα 9, συλλέγεται σε `errors[]`.
- Ενιαία απάντηση σχήματος `{items: [...], errors: [...]}` από τη νέα bridge εντολή
  `parse_import_data` — πάντα λίστα, ακόμα κι όταν είναι ένα αρχείο/ένα παραστατικό
  (απλοποιεί το frontend, δεν χρειάζεται δύο διαφορετικά response shapes).

**Frontend** (`js/pdf-import.js`):
- `_populatePdfForm(r)` έγινε κοινή συνάρτηση — καλείται είτε από `parsePdf()` (PDF) είτε από
  το batch queue (JSON/CSV), μηδενική διπλή λογική.
- Batch queue: `_loadImportResult` → `_showImportQueueItem(i)` δείχνει ένα στοιχείο τη φορά,
  `nextImportQueueItem()` προχωράει. Ο χειριστής κάνει submit ρητά για κάθε στοιχείο — καμία
  αυτόματη προώθηση μετά από submit, ώστε να μη διακόπτεται η ροή Βήμα-2 (ερώτηση
  αγοράς/επιστροφής) πριν προλάβει να απαντήσει.
- `window._pdfImportSource` ('pdf' ή 'data') καθορίζει το σωστό paratirishis label
  ("Εισαγωγή από PDF" vs "Εισαγωγή από JSON/CSV") — mislabeling bug που εντοπίστηκε και
  διορθώθηκε αμέσως μετά την πρώτη υλοποίηση.
- `_findCloseYlikoMatch`: Levenshtein distance, threshold `max(2, round(min(len)*0.25))` —
  προειδοποιεί για near-duplicate ονόματα υλικού (OCR/LLM typos, λατινικό/ελληνικό Χ) χωρίς
  να μπλοκάρει, με κουμπί instant-fix.

## Αξιόπιστο matching αγοράς/επιστροφής σε batch (`agora_ref`)

Το υπάρχον Βήμα-2 flow ("ποιο τιμολόγιο αγοράς αφορά η επιστροφή") default σε
`get_last_eisagogi_parstatiko()` — σωστό μόνο όταν εισάγεις ένα παραστατικό τη φορά. Σε batch
με πολλές αγορές πριν τις επιστροφές τους, θα πρότεινε πάντα την πιο πρόσφατη, όχι απαραίτητα
τη σωστή. Fix: προαιρετικό πεδίο `agora_ref` στο σχήμα JSON/CSV — αν παρόν,
`window._pdfSuggestedAgoraRef` (stashed στο `_populatePdfForm`) το προτιμά έναντι της
ευρετικής. Backward compatible: χωρίς το πεδίο, ίδια συμπεριφορά με πριν.

Επαληθεύτηκε live: submit PUR-1 → submit PUR-2 (decoy, ώστε "τελευταία αγορά" στη βάση να
γίνει σκόπιμα λάθος) → submit RET-1 με `agora_ref: PUR-1` → prefill = PUR-1 σωστά (όχι PUR-2).

## Bug class: κανονικοποίηση παύλας (`_clean_parst`)

Το `add_kinisi`/`update_kinisi` πάντα κανονικοποιούν το `arithmos_parstatikos` πριν την
αποθήκευση (`_clean_parst`: `"ΔΙΧΝ-19586"` → `"ΔΙΧΝ 19586"`). Βρέθηκε ότι **8 συναρτήσεις**
που κάνουν exact-match WHERE σε `arithmos_parstatikos`/`agora_ref` δεν έκαναν το ίδιο στο
input τους — προϋπήρχε ήδη στο v1.1.11, εντοπίστηκε ενώ δοκιμαζόταν το batch import εδώ.

Εντοπίστηκε σταδιακά, ένα-ένα, μέσω πραγματικού end-to-end testing (όχι μόνο code review) —
κάθε φορά που δοκιμάστηκε ένα σενάριο με παύλα στο αριθμό παραστατικού, βρέθηκε νέα
συνάρτηση με το ίδιο πρόβλημα:

1. `check_parstatiko_exists` — η προστασία από διπλοεγγραφή δεν ενεργοποιούνταν ποτέ.
2. `update_agora_ref` / `check_ekkremotita` — το "🔍 Έλεγχος" στο Βήμα-2 έδειχνε επιτυχία
   αλλά δεν συνέδεε τίποτα (0 rows matched, καμία ένδειξη σφάλματος).
3. `delete_kiniseis_by_parstatiko` / `delete_parstatiko_with_related` — το πιο σοβαρό: το
   "🗑 Διαγραφή Όλων" στο ίδιο το διπλοεγγραφή modal δεν έσβηνε τίποτα με παύλα, και μετά
   ξανακαταχωρούσε → επιδείνωνε τη διπλοεγγραφή αντί να τη διορθώσει.
4. `assign_epistrofi_parstatiko` — επιπλέον έγραφε **μη κανονικοποιημένη** τιμή στη βάση,
   ασυνεπές με το add_kinisi/update_kinisi.
5. `get_epistrofes_without_parstatiko`, `get_kiniseis_by_parstatiko_yliko` — ίδιο exact-match
   πρόβλημα σε αναζητήσεις.

**Backported στο main ως v1.1.12** — δεν ήταν κάτι που εισήγαγε το v2, οπότε ταιριάζει στην
πολιτική "v1 δέχεται μόνο διορθώσεις λαθών". Ίδιο fix commit περιεχόμενο και στα δύο branches.

**Μάθημα για μελλοντικό tooling:** αν προστεθεί ποτέ νέα συνάρτηση που κάνει WHERE σε
`arithmos_parstatikos`/`agora_ref`, πρέπει να καλεί `_clean_parst()` στο input της πρώτα —
δεν υπάρχει κεντρικό boundary layer που το κάνει αυτόματα (θα άξιζε σκέψη σε μελλοντικό
refactor, αλλά όχι τώρα — ρίσκο χωρίς άμεσο όφελος).

## Presence detection μέσω rclone (ποιος είναι online)

Κάθε εγκατάσταση γράφει periodic heartbeat στο ίδιο rclone remote που ήδη χρησιμοποιείται
για DB backup/sync (το slot "Cloud (rclone)" στη σελίδα Backup), ώστε άλλες εγκαταστάσεις να
βλέπουν ποιος χειριστής είναι online. Όλη η rclone/backup λογική ζει στο Python backend, οπότε
το presence detection ακολουθεί το ίδιο pattern με το `backend/backup.py`.

**Backend** (`backend/presence.py`, νέο αρχείο): `send_heartbeat()` γράφει
`{user, computer, last_seen}` (UTC ISO8601) σε `<remote>/presence/<computer>__<user>.json` —
όχι μόνο hostname, ώστε δύο μηχανήματα με ίδιο default hostname (π.χ. δύο καινούργια Windows
"DESKTOP-XXXXX") να μην αλληλοεπικαλύπτονται. `list_presence()` κάνει ένα `rclone copy
<remote>/presence <tmpdir>` (όχι `lsjson`+per-file `cat`) και διαβάζει όλα τα ληφθέντα JSON
τοπικά — ένα round-trip ανεξάρτητα από τον αριθμό εγκαταστάσεων. Ταυτότητα (`user`/`computer`)
από OS-level `USERNAME`/`USER`/`socket.gethostname()` — καμία νέα ρύθμιση identity, η
εφαρμογή δεν είχε ποτέ concept "τρέχων χρήστης".

**Bridge/main.js**: νέες εντολές `send_heartbeat`/`list_presence`. Η `send_heartbeat` καλείται
μόνο από το main process (`main.js`'s `callPython`, το πρώτο `setInterval` σε αυτό το
codebase — 90 δευτερόλεπτα, μέσα στο εύρος 1-2 λεπτών του spec), όχι από το renderer, οπότε
δεν μπαίνει στο `ALLOWED_PYTHON_COMMANDS`· η `list_presence` μπαίνει, γιατί τη χρειάζεται το
UI. Χρειάστηκε `clearInterval` στο `window-all-closed` ώστε το heartbeat να μην τρέξει μετά
το κλείσιμο του bridge stdin.

**UI** (`js/backup.js`, σελίδα Backup): νέο panel "Συνδεδεμένοι χρήστες" κάτω από τα "Remotes
rclone" — πράσινο "● online" αν `last_seen` < 2 λεπτά, αλλιώς "τελευταία σύνδεση: πριν Χ" με
νέο τοπικό relative-time helper (`_relativeTimeGr`, δεν υπήρχε παρόμοιο πουθενά στο repo).

## Sidebar/titlebar redesign — presence status button στην κορυφή

Το presence detection παραπάνω ήταν αρχικά ορατό μόνο στον αναλυτικό πίνακα της σελίδας
Backup — τετράδα commits (`3b733ff`, `f962abc`, `2239382`, `cbb1158`) το ανέβασε σε ένα
compact status button στην κορυφή του sidebar, ορατό από παντού:

- **`.sidebar-logo`** (`index.html`): το app icon (`assets/icon.png`) έγινε το ίδιο ο τίτλος —
  αφαιρέθηκε το ξεχωριστό κείμενο τίτλου (πλέον περιττό, το icon ήδη κουβαλάει το wordmark
  "ExpVault"), clickable button που πλοηγεί στο Dashboard. Από κάτω: `#sidebar-version`
  (κεντραρισμένο, 26px title ↔ 26px icon box baseline-aligned — 4 rounds tuning μέχρι να
  χωράει τίτλος+έκδοση σε μία γραμμή με 23px περιθώριο). Ίδιο branding refresh στο custom
  titlebar (`#titlebar-drag`): έφυγε το παλιό 💣 emoji + ελληνικό όνομα, μπήκε το πραγματικό
  icon + "ExpVault" + έκδοση.
- **`#sidebar-presence`**: νέο πράσινο/κόκκινο status button ακριβώς κάτω από την έκδοση —
  πράσινο όταν δεν υπάρχει άλλος συνδεδεμένος χρήστης, κόκκινο όταν υπάρχει. Click πλοηγεί
  στη σελίδα Backup (τον αναλυτικό πίνακα). Νέα bridge εντολή `whoami` (`backend/presence.py`)
  ώστε το renderer να αγνοεί το δικό του heartbeat κατά τον υπολογισμό "υπάρχει *άλλος*
  online" — ίδιο "εξαίρεσε τον εαυτό σου" pattern με το identity-based φιλτράρισμα.
- Το εικονίδιο του presence button ξεκίνησε emoji, έγινε inline SVG (`cbb1158`) — το emoji
  είχε διαφορετικά vertical ink metrics ανάμεσα στο automated screenshot tool και το
  πραγματικό desktop, δημιουργώντας misalignment ορατό μόνο στην πραγματική εφαρμογή. Το SVG
  αποφεύγει ολόκληρη αυτή την κλάση bug.

## Presence badge + Ιστορικό Εκδόσεων redesign

Δεύτερο redesign πάνω στο presence button παραπάνω (2026-08-02): το version badge και το
presence status button ενώθηκαν σε ένα, και η λίστα συνδεδεμένων χρηστών μετακόμισε από τη
σελίδα Backup στο modal Ιστορικού Εκδόσεων:

- **Sidebar badge**: το `#sidebar-version` και το `#sidebar-presence` ενώθηκαν σε ΕΝΑ
  `#sidebar-presence-badge` (πράσινο/κόκκινο ίδιο gradient με πριν) — η ξεχωριστή SVG
  εικόνα presence αφαιρέθηκε, το πράσινο/κόκκινο χρώμα του ίδιου του κουτιού αρκεί ως status.
  Click ανοίγει πλέον το modal Ιστορικού Εκδόσεων (`showVersionHistory()`) αντί να πλοηγεί
  στη σελίδα Backup — η σελίδα Backup δεν έχει πια δικό της presence panel.
- **Λίστα συνδεδεμένων χρηστών**: μετακόμισε από πίνακα στη σελίδα Backup
  (`bkRefreshPresence`/`#bk-presence-list`, αφαιρέθηκαν) σε δυναμικές ισομεγέθεις κάρτες
  (`#presence-list`) μέσα στο modal Ιστορικού Εκδόσεων — μόνο online χρήστες, όχι πίνακας με
  offline ιστορικό. Το δικό μας entry συνθέτεται client-side αν το πραγματικό heartbeat δεν
  έχει προλάβει να συγχρονιστεί, ΑΚΟΜΑ ΚΑΙ αν υπάρχει ένα stale (παλιό, >2 λεπτά) entry με το
  ίδιο user/computer στη λίστα — βρέθηκε live στο dev testing (stale heartbeat file από
  προηγούμενο test session) ότι το αρχικό `alreadyListed` check δεν ξεχώριζε αυτή την
  περίπτωση (οποιοδήποτε entry με το ίδιο identity μετρούσε ως "already listed" ανεξαρτήτως
  φρεσκάδας) — διορθώθηκε ώστε `alreadyListed` να απαιτεί επίσης online. Χρώματα reused από
  το `:root` του app: `--accent` (#e8a020, δική μας κάρτα όταν υπάρχει άλλος online),
  `--success` (#1a7a4a, δική μας κάρτα όταν είμαστε μόνοι), `--danger` (#c0392b, κάρτες
  άλλων online).
- **Bonus fix, ίδιο commit**: το `VERSIONS.md` είναι χειροκίνητα word-wrapped σαν αρχείο
  κειμένου, και το παλιό `parseVersionsMd`/`white-space:pre-wrap` έκανε τις περιγραφές να
  "κόβονται" στη μέση ανεξάρτητα από το πλάτος του modal. `parseVersionsMd`
  (`js/version-notice.js`) ενώνει πλέον συνεχόμενες γραμμές σε ένα bullet μέχρι την επόμενη
  γραμμή που ξεκινά με λέξη-κλειδί + άνω-κάτω τελεία ("Νέο:", "Fix:", "Αλλαγή:", "Docs:", …).
- **Sidebar font sizes**: follow-up στο ίδιο redesign — το `.nav-item`/`.nav-icon`,
  `.sidebar-version-top` και `.adeia-strip` μεγάλωσαν (13px→15px/16px, 15px→17px) ώστε όλο το
  sidebar να διαβάζεται σε συνεπές, μεγαλύτερο μέγεθος αντί το badge να ξεχωρίζει μόνο του.

**Αρχεία:** `index.html`, `css/app.css`, `js/backup.js` (αφαιρέθηκε το presence-panel του),
`js/version-notice.js` (νέο presence badge/list logic + parser fix).

## Ενιαία παλέτα κατάστασης, ευθυγραμμισμένη με το lab-galatista

Οπτικός έλεγχος (2026-08-02) ανάμεσα στο ExpVault και το αδερφό project lab-galatista έδειξε
ότι, ενώ το χρωματικό νόημα ταυτίζεται (πράσινο=ήσυχο, κόκκινο=προσοχή, θερμότερο χρώμα όσο
πιο κοντά στη λήξη/στο πρόβλημα), η υλοποίηση όχι: το presence badge/λωρίδα άδειας του
sidebar ήταν gradient pills με raw Tailwind hex, ενώ το version-history list και το πάνω
banner "γνωστό πρόβλημα σχήματος" κουβαλούσαν ο καθένας τη δική του ασύνδετη παλέτα (Chakra
UI green.300/red.300 στο ένα, ξεχωριστό pastel red στο άλλο) — τουλάχιστον πέντε ασύνδετες
οικογένειες κόκκινου και τρεις πράσινου μέσα στο ίδιο codebase. Το lab-galatista αντίθετα
περνάει σχεδόν κάθε τέτοιο badge από τα δικά του `--ok`/`--warn`/`--fail` tokens.

Απόφαση: υιοθέτηση των ίδιων ακριβών χρωμάτων (και του flat outline/fill/font ύφους αντί για
gradient) με το lab-galatista, σε 7 νέα `--status-*` tokens στο `:root` του `css/app.css`
(`--status-ok #16a34a`, `--status-ok-light #22c55e`, `--status-warn-light #f59e0b`,
`--status-warn #d97706`, `--status-danger-light #ef4444`, `--status-danger #dc2626`,
`--status-neutral #94a3b8`) — ξεχωριστά από τα υπάρχοντα `--success`/`--danger`, που
παραμένουν αμετάβλητα γιατί χρησιμοποιούνται ευρέως αλλού (κουμπιά, στήλες +/- σε πίνακες) και
δεν είναι μέρος αυτού του status-signaling συστήματος:

- **`.sidebar-presence-badge`**: gradient pill → flat κουτί (`--status-ok`/`--status-danger-light`
  fill+border+font, ίδιο pattern με το lab-galatista `.presence-badge`).
- **`.adeia-strip`** (sidebar) **και `splash.html`'s `.tier-*`** (ίδιοι ακριβώς 5 gradients
  πριν, ίδια ακριβώς 6 flat κουτιά τώρα): προστέθηκε 6η βαθμίδα `expired`/`tier-expired`,
  ξεχωριστή από `urgent` — πριν το `days_left <= 15` κάλυπτε ΚΑΙ "λήγει σε λίγες μέρες" ΚΑΙ
  "ήδη έληξε" με το ίδιο κόκκινο, το lab-galatista ήδη τα ξεχωρίζει σε δύο εντάσεις. Split στο
  `js/adeies.js` (`days_left < 0` → `adeia-strip-expired`) και στο `splash.html`'s inline
  tier-λογική.
- **`#presence-section-box`** (modal Ιστορικού Εκδόσεων): έμεινε flat κουτί όπως πριν, απλά η
  ένταση του πράσινου/κόκκινου άλλαξε να ταιριάζει με το lab-galatista.
- **Κάρτες online χρηστών** (`ME_GREEN`/`OTHER_RED` στο `js/version-notice.js`): αντικαθιστά
  τα `--success`/`--danger` (#1a7a4a/#c0392b) που περιγράφονται στην προηγούμενη ενότητα με τα
  lab-galatista ισοδύναμα (#16a34a/#dc2626). Το `ME_ORANGE` παραμένει το δικό μας `--accent`
  (#e8a020, αμετάβλητο) — το lab-galatista δανείζεται εκεί το πορτοκαλί του δικού του
  λογότυπου, όχι κάποιο κοινό token, οπότε δεν έχει νόημα να το αντιγράψουμε.
- **Ιστορικό Εκδόσεων list + πάνω banner** (`js/version-notice.js`): Chakra UI hex
  (`#68d391`/`#fc8181`) και pastel red banner (`#fde8e8`/`#f5b7b1`/`#7b1c1c`) αντικαταστάθηκαν
  με τα ίδια `--status-*`-ισοδύναμα hex.

Επαληθεύτηκε οπτικά με το `run-expvault` skill (dev mode) και ένα προσωρινό playwright script
για το splash window (δεν επιλέγεται από το skill's `launch`, βλ. σχόλιο στο `driver.mjs`) —
δοκιμάστηκαν και οι 6 βαθμίδες αλλάζοντας προσωρινά το `imerominia_lixis` μιας άδειας στη dev
βάση, με επαναφορά σε `NULL` στο τέλος.

**Αρχεία:** `css/app.css` (νέα tokens + 3 components), `js/adeies.js` (split expired tier),
`splash.html` (ίδιο split + flat tiers), `js/version-notice.js` (presence cards, version list,
schema banner).

## Dual-install: ExpVault+ (v2) εγκαθίσταται παράλληλα με το ExpVault (main)

Στόχος: να μπορεί ο χειριστής να δοκιμάσει τη δουλειά του `v2` σε πραγματικό μηχάνημα χωρίς να
πειράξει την υπάρχουσα, "εν χρήσει" εγκατάσταση/βάση — ίδιο μοτίβο με το dual-install setup του
lab-galatista (`daigma-lims` δίπλα στο `lab-galatista`, βλ. εκείνου το
`Odigies-Dipli-Egkatastasi-v1-v2.md`, εκτός repo).

**Ξεχωριστή ταυτότητα, μόνο στο `v2`** (`package.json`): `name: "expvaultplus"`,
`appId: "gr.latomeio.expvaultplus"`, `productName: "ExpVault+"`, `version: "2.0.0"` — αυτό
αυτόματα μετακινεί το data folder σε `%APPDATA%\expvaultplus\` (το Electron το παίρνει από το
`name`) και δίνει ξεχωριστή καταχώρηση Προγράμματα/Εγκατάσταση αντί να πατήσει πάνω στο
`gr.latomeio.expvault` του κανονικού ExpVault. Το `main` δεν αλλάζει καθόλου.

**Titlebar/sidebar δείχνουν "ExpVault+" δυναμικά**, όχι hardcoded string — νέο
`get-app-product-name` IPC (`version-check.js`) + `js/version-notice.js` γεμίζει
`#titlebar-app-name`/tooltip του sidebar logo. Δύο αποτυχημένες προσπάθειες πριν τη σωστή
λύση, και οι δύο επιβεβαιωμένες **live σε packaged build**, όχι θεωρητικά:
1. `require('./package.json').build.productName` — δουλεύει σε dev, σκάει σε packaged
   (`TypeError: undefined.productName`): το electron-builder αφαιρεί εντελώς το `"build"` key
   από το package.json μέσα στο `app.asar` (μόνο name/version/description/author/license/
   main/dependencies/allowScripts επιζούν).
2. `app.getName()` — επιστρέφει το `"name"` field (`"expvaultplus"`), ΟΧΙ το `productName`,
   και στα ΔΥΟ mode.
3. Τελική λύση: `app.isPackaged ? path.basename(process.execPath, '.exe') : package.json's
   build.productName` — σε packaged build το ίδιο το exe είναι ονομασμένο "ExpVault+.exe" από
   το electron-builder, άρα το `process.execPath` είναι το μοναδικό αξιόπιστο σημείο αλήθειας.

**Δημόσιο GitHub release**: πρώτα αφαιρέθηκε το `electron-updater` από το `main` (v1.2.0, βλ.
DONE.md/VERSIONS.md — το `electron-updater` δεν έχει καμία γνώση appId, θα μπορούσε να
αυτο-εγκαταστήσει ένα ExpVault+ release πάνω σε πραγματικά v1.x installs), ώστε να γίνει
ασφαλές να δημοσιευτεί το ExpVault+. Το tag είναι σκόπιμα `expvaultplus-v2.0.0` (ΟΧΙ
`v2.0.0`) — το CLAUDE.md λέει ρητά ότι το `v2` δεν παίρνει tag στο `vX.Y.Z` namespace μέχρι να
γίνει το πραγματικό main merge, και ένα "v2.0.0" θα έδειχνε σαν επόμενη επίσημη έκδοση στη
δημόσια σελίδα Releases. Marked pre-release επίσης, ώστε το "Latest" badge του repo να δείχνει
πάντα στο πραγματικό ExpVault.

**Αρχεία:** `package.json`, `main.js` (IS_MAIN_LINE guard), `version-check.js`
(`get-app-product-name`, `checkForUpdatesV2`, `allowed-versions-v2.json` fetch από branch `v2`),
`preload.js`, `index.html`/`js/version-notice.js` (dynamic titlebar), νέο
`allowed-versions-v2.json`.
