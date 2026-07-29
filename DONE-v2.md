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
