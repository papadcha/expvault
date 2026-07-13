# TODO

Ιδέες για μελλοντική υλοποίηση — ελεγμένες ως προς εφικτότητα πάνω στην τρέχουσα αρχιτεκτονική. Όσα σημειώνονται **ΈΓΙΝΕ** έχουν υλοποιηθεί.

## 1. Alert χαμηλού υπολοίπου άδειας — **ΈΓΙΝΕ**

Όταν το υπόλοιπο μιας άδειας (ανά νομική κατηγορία) πέσει κάτω από **3× τον μέσο όρο των αγορών** της, εμφάνιση toast στον χρήστη.

**Trigger points (και τα δύο επαληθεύτηκαν στην πραγματική εφαρμογή):**
- Κατά την καταχώρηση κίνησης: `backend/bridge.py`'s `add_kinisi` handler επιστρέφει side-channel `adeia_alerts` όταν η καταχώρηση αγγίζει άδεια κάτω από το κατώφλι· το `js/utils.js`'s `py()` το διαβάζει αυτόματα και δείχνει toast — δουλεύει από όλα τα σημεία που καλούν `add_kinisi` (kiniseis.js, pdf-import.js, ypologismos.js) χωρίς να χρειαστεί αλλαγή σε καθένα ξεχωριστά.
- Στην εκκίνηση της εφαρμογής: `checkAdeiaThresholdsOnStartup()` (`js/utils.js`) καλείται από το INIT section του `index.html`, αμέσως μετά το `loadDashboard()` (renderer-side, όχι μέσω main.js/`ready-to-show` όπως το `checkVersionNotice` — απλούστερο, μιας κι έτσι κι αλλιώς περνάει από το python bridge μέσω `py()`).

**Υλοποίηση:**
- `backend/database.py`'s `get_adeia_low_balance_alerts(adeia_id=None, threshold_multiplier=3.0)`: συνδυάζει το υπόλοιπο (ίδια λογική με `get_adeia_katigoria_remaining`) με νέο query μέσου όρου ΕΙΣΑΓΩΓΗ ανά (`adeia_id`, `nomiki_katigoria`). Κατηγορίες χωρίς ιστορικό αγορών αγνοούνται (όχι false positives σε νέες άδειες).
- Νέα bridge command `check_adeia_thresholds` (χωρίς adeia_id — όλες οι άδειες, για το startup check).
- Toast μέσω του υπάρχοντος `window._showToast`.

## 2. Backup ανά άδεια (event-driven, όχι ημερολογιακό) + ετήσιο backup — **ΈΓΙΝΕ**

**Δύο backups ανά άδεια**, με trigger από **query πάνω στις κινήσεις της άδειας** (όχι από `imerominia_lixis`):
- **Backup #1** (σιωπηλά): όταν το υπόλοιπο άδειας πέσει κάτω από 3× μέσο όρο αγορών (ίδιο κατώφλι με το alert της §1).
- **Backup #2** (με toast ειδοποίησης): όταν το υπόλοιπο πέσει κάτω από 1× μέσο όρο αγορών.
- Μοιράζεται τη λογική υπολογισμού remaining/average με το feature #1 (`get_adeia_low_balance_alerts`, ίδιο query, διαφορετικό `threshold_multiplier`).

**Ετήσιο backup**: ημερολογιακό — τρέχει αν πέρασαν ≥365 μέρες από το `last_annual_backup` (ή ποτέ δεν έτρεξε), ελέγχεται στην εκκίνηση.

**Και τα δύο τρέχουν σιωπηλά αν δεν υπάρχουν configured backup paths** (`run_all_backups()` επιστρέφει `ok:false` χωρίς crash, το marker δεν "καταναλώνεται" — ξαναδοκιμάζει σε κάθε επόμενη εκκίνηση μέχρι να μπουν paths).

**Υλοποίηση:**
- `backend/backup.py`: `check_annual_backup()`, `check_adeia_backups(alerts_level1, alerts_level2)`. Νέα πεδία στο `backup_config.json`: `last_annual_backup` (ημερομηνία), `adeia_backup_state` (`{"<adeia_id>:<nomiki_katigoria>": {backup1_done, backup2_done}}`).
- Νέα bridge command `check_startup_backups` (`backend/bridge.py`) — συνδυάζει `check_annual_backup()` με `check_adeia_backups()` πάνω σε `database.get_adeia_low_balance_alerts()` με δύο thresholds (3.0 και 1.0).
- `js/utils.js`'s `checkAdeiaBackupsOnStartup()`, καλείται από το `index.html` INIT section· toast μόνο για τα backup#2 (`notify`).
- **Reset markers** (απάντηση στο ανοιχτό ερώτημα): **δεν** βασίζεται σε equality της εγκεκριμένης ποσότητας (δοκιμάστηκε πρώτα, βρέθηκε bug — δες παρακάτω) αλλά σε **recovery**: μόλις μια (adeia_id, nomiki_katigoria) βγει από το level1 (υπόλοιπο ξαναανέβει πάνω από 3× μέσο όρο, είτε από ΕΠΙΣΤΡΟΦΗ είτε από αύξηση έγκρισης), ο marker διαγράφεται αυτόματα από το `adeia_backup_state` — αν ξαναμπεί αργότερα σε alert για οποιονδήποτε λόγο, ξανατρέχει κανονικά. Αυτοθεραπεύεται επίσης όταν διαγράφεται μια άδεια (ο stale marker της απλά δεν εμφανίζεται πια στα current alerts, καθαρίζεται στο επόμενο check).
- **Πολλαπλές νομικές κατηγορίες ανά άδεια** (απάντηση στο άλλο ανοιχτό ερώτημα): κάθε (adeia_id, nomiki_katigoria) παρακολουθείται ανεξάρτητα· επειδή το backup είναι πάντα ολόκληρη η βάση (ένα SQLite αρχείο, όχι per-κατηγορία), αρκεί ΜΙΑ κατηγορία να περάσει το κατώφλι για να τρέξει backup — αυτό υλοποιεί φυσικά το "το χειρότερο αποφασίζει".

Επαληθεύτηκε με Python integration test (idempotency, backup#1 vs backup#2, reset μετά από renewal, annual boundary στις 365 μέρες) και με το `run-expvault` driver πάνω στην πραγματική dev εφαρμογή (πραγματικό state transition σε πραγματικά configured backup paths, self-healing state μετά τη διαγραφή δοκιμαστικής άδειας).

**Γνωστό pre-existing θέμα που εντοπίστηκε παρεμπιπτόντως (εκτός scope, δεν διορθώθηκε):** `backup.py`'s `_is_rclone(path)` κάνει `':' in path` — κάθε Windows local path (`C:\...`) περιέχει `:` και άρα ταξινομείται λανθασμένα ως rclone remote. Φαίνεται να "δουλεύει" τυχαία επειδή το rclone μπορεί να διευθυνσιοδοτήσει και τοπικά paths, αλλά περνάει από subprocess αντί για απλό `shutil.copy2`. Αν θες, μπαίνει σαν ξεχωριστό todo item.

## 3. Ευρήματα από static review (επιβεβαιωμένα — ολοκληρωμένα)

Πρόταση εξωτερικού review (ChatGPT), ελεγμένη πάνω στο πραγματικό repo — μόνο τα επιβεβαιωμένα σημεία.

- ~~**Destructive migration στο `adeia_ylika`** (`backend/database.py:80-87`)~~ — **ΈΓΙΝΕ.** Οι παλιές εγκεκριμένες ποσότητες σώζονται πριν το `DROP TABLE` (αθροιστικά ανά νόμιμη κατηγορία μέσω `classify_nomiki_katigoria`) και ξαναγράφονται μετά το `CREATE TABLE`. Επαληθεύτηκε με test script.
- ~~**`restore_backup` χωρίς προστασία** (`backend/backup.py:219-242`)~~ — **ΈΓΙΝΕ.** Προστέθηκε `PRAGMA integrity_check` στο πηγαίο αρχείο πριν το restore, αυτόματο `expvault_prerestore_<ts>.db` snapshot της τρέχουσας βάσης, και atomic αντικατάσταση (`os.replace`). Επαληθεύτηκε με test script (άκυρο αρχείο απορρίπτεται χωρίς να πειράξει την ενεργή βάση).
- ~~**`requirements.txt` λείπει**~~ — **ΈΓΙΝΕ.** Προστέθηκε `requirements.txt` με pinned εκδόσεις (τις ήδη εγκατεστημένες: pyinstaller 6.21.0, reportlab 5.0.0, openpyxl 3.1.5, python-docx 1.2.0), `build.ps1` και `CLAUDE.md` ενημερώθηκαν να το χρησιμοποιούν. Το `package-lock.json` υπήρχε ήδη (αυτό το κομμάτι του review ήταν λάθος).
- ~~**`max_keep` του backup χωρίς validation** (`backend/backup.py:44-49`)~~ — **ΈΓΙΝΕ.** Το `save_config()` τώρα κάνει clamp σε ακέραιο 1–365, με fallback σε 30 για μη έγκυρες τιμές.

## 4. Ευρήματα από static review (μικρής προτεραιότητας / defense-in-depth, για αργότερα)

Δεν είναι ενεργά exploitable με τον τρόπο που περιγράφτηκαν, αλλά αξίζει σκλήρυνση/εκσυγχρονισμός όταν βρεθεί χρόνος:

- **Εύθραυστο pattern `onclick='fn(${escapeHtml(JSON.stringify(obj))})'`**: εμφανίζεται σε 8 αρχεία (`kiniseis.js`, `adeies.js`, `promitheftes.js`, `ylika.js`, `backup.js`, `pdf-import.js`, `templates.js`). Επαληθεύτηκε ότι ο συνδυασμός `JSON.stringify` + `escapeHtml` είναι σήμερα ασφαλής (το πρώτο χειρίζεται το escaping μέσα στο JS string, το δεύτερο το HTML attribute boundary), αλλά είναι εύθραυστο — μια μελλοντική απλοποίηση του `escapeHtml` θα το έσπαγε αθόρυβα. Αντικατάσταση με `addEventListener` + `data-*` attributes θα το έκανε πιο ανθεκτικό δομικά.
- **`window.api.call(cmd, payload)` περνάει οποιοδήποτε `cmd` string ατόφιο** (`preload.js:4` → `main.js:139` → `backend/bridge.py`): το bridge έχει ήδη fixed allowlist ~58 hardcoded commands (όχι πραγματικό αυθαίρετο RPC), αλλά αρκετά από αυτά είναι destructive (`delete_*`, `restore_backup` με ελεύθερο path, `delete_remote`) και προσβάσιμα χωρίς επιπλέον έλεγχο. Αξίζει σκλήρυνση ως defense-in-depth — ειδικά επειδή το `pdf_parser.py` επεξεργάζεται εξωτερικά PDF τιμολόγια προμηθευτή, ένα πιο ρεαλιστικό μελλοντικό attack surface από χειρόγραφα πεδία σημειώσεων.
