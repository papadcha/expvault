# DONE

Αρχειοθέτηση ολοκληρωμένων items που προέκυψαν από το `TODO.md` — κρατιέται για ιστορικό/αναφορά, όχι για ενεργή δουλειά.

## Alert χαμηλού υπολοίπου άδειας

Όταν το υπόλοιπο μιας άδειας (ανά νομική κατηγορία) πέσει κάτω από **3× τον μέσο όρο των αγορών** της, εμφάνιση toast στον χρήστη.

**Trigger points (και τα δύο επαληθεύτηκαν στην πραγματική εφαρμογή):**
- Κατά την καταχώρηση κίνησης: `backend/bridge.py`'s `add_kinisi` handler επιστρέφει side-channel `adeia_alerts` όταν η καταχώρηση αγγίζει άδεια κάτω από το κατώφλι· το `js/utils.js`'s `py()` το διαβάζει αυτόματα και δείχνει toast — δουλεύει από όλα τα σημεία που καλούν `add_kinisi` (kiniseis.js, pdf-import.js, ypologismos.js) χωρίς να χρειαστεί αλλαγή σε καθένα ξεχωριστά.
- Στην εκκίνηση της εφαρμογής: `checkAdeiaThresholdsOnStartup()` (`js/utils.js`) καλείται από το INIT section του `index.html`, αμέσως μετά το `loadDashboard()` (renderer-side, όχι μέσω main.js/`ready-to-show` όπως το `checkVersionNotice` — απλούστερο, μιας κι έτσι κι αλλιώς περνάει από το python bridge μέσω `py()`).

**Υλοποίηση:**
- `backend/database.py`'s `get_adeia_low_balance_alerts(adeia_id=None, threshold_multiplier=3.0)`: συνδυάζει το υπόλοιπο (ίδια λογική με `get_adeia_katigoria_remaining`) με νέο query μέσου όρου ΕΙΣΑΓΩΓΗ ανά (`adeia_id`, `nomiki_katigoria`). Κατηγορίες χωρίς ιστορικό αγορών αγνοούνται (όχι false positives σε νέες άδειες).
- Νέα bridge command `check_adeia_thresholds` (χωρίς adeia_id — όλες οι άδειες, για το startup check).
- Toast μέσω του υπάρχοντος `window._showToast`.

## Backup ανά άδεια (event-driven, όχι ημερολογιακό) + ετήσιο backup

**Δύο backups ανά άδεια**, με trigger από **query πάνω στις κινήσεις της άδειας** (όχι από `imerominia_lixis`):
- **Backup #1** (σιωπηλά): όταν το υπόλοιπο άδειας πέσει κάτω από 3× μέσο όρο αγορών (ίδιο κατώφλι με το alert).
- **Backup #2** (με toast ειδοποίησης): όταν το υπόλοιπο πέσει κάτω από 1× μέσο όρο αγορών.
- Μοιράζεται τη λογική υπολογισμού remaining/average με το alert χαμηλού υπολοίπου (`get_adeia_low_balance_alerts`, ίδιο query, διαφορετικό `threshold_multiplier`).

**Ετήσιο backup**: ημερολογιακό — τρέχει αν πέρασαν ≥365 μέρες από το `last_annual_backup` (ή ποτέ δεν έτρεξε), ελέγχεται στην εκκίνηση.

**Και τα δύο τρέχουν σιωπηλά αν δεν υπάρχουν configured backup paths** (`run_all_backups()` επιστρέφει `ok:false` χωρίς crash, το marker δεν "καταναλώνεται" — ξαναδοκιμάζει σε κάθε επόμενη εκκίνηση μέχρι να μπουν paths).

**Υλοποίηση:**
- `backend/backup.py`: `check_annual_backup()`, `check_adeia_backups(alerts_level1, alerts_level2)`. Νέα πεδία στο `backup_config.json`: `last_annual_backup` (ημερομηνία), `adeia_backup_state` (`{"<adeia_id>:<nomiki_katigoria>": {backup1_done, backup2_done}}`).
- Νέα bridge command `check_startup_backups` (`backend/bridge.py`) — συνδυάζει `check_annual_backup()` με `check_adeia_backups()` πάνω σε `database.get_adeia_low_balance_alerts()` με δύο thresholds (3.0 και 1.0).
- `js/utils.js`'s `checkAdeiaBackupsOnStartup()`, καλείται από το `index.html` INIT section· toast μόνο για τα backup#2 (`notify`).
- **Reset markers**: **δεν** βασίζεται σε equality της εγκεκριμένης ποσότητας (δοκιμάστηκε πρώτα, βρέθηκε bug) αλλά σε **recovery**: μόλις μια (adeia_id, nomiki_katigoria) βγει από το level1 (υπόλοιπο ξαναανέβει πάνω από 3× μέσο όρο, είτε από ΕΠΙΣΤΡΟΦΗ είτε από αύξηση έγκρισης), ο marker διαγράφεται αυτόματα από το `adeia_backup_state` — αν ξαναμπεί αργότερα σε alert για οποιονδήποτε λόγο, ξανατρέχει κανονικά. Αυτοθεραπεύεται επίσης όταν διαγράφεται μια άδεια.
- **Πολλαπλές νομικές κατηγορίες ανά άδεια**: κάθε (adeia_id, nomiki_katigoria) παρακολουθείται ανεξάρτητα· επειδή το backup είναι πάντα ολόκληρη η βάση (ένα SQLite αρχείο, όχι per-κατηγορία), αρκεί ΜΙΑ κατηγορία να περάσει το κατώφλι για να τρέξει backup — αυτό υλοποιεί φυσικά το "το χειρότερο αποφασίζει".
- **Naming**: αρχικά όλα τα backups (manual, auto-on-close, ετήσιο, ανά άδεια) παρήγαγαν το ίδιο filename pattern — καμία διάκριση στη λίστα backups για το ποιο προήλθε από πού. Προστέθηκε προαιρετικό `reason` σε `do_backup()`/`run_all_backups()`: `annual` για το ετήσιο, `adeia1`/`adeia2` για το ανά άδεια (backup#1/#2) — γίνεται suffix στο filename (`expvault_backup_<ts>_annual.db` κ.λπ.). Manual/auto-on-close backups παραμένουν χωρίς suffix (backward compatible, ίδιο format με πριν). Το parsing/pruning στο `list_backups`/`_do_local_backup` δεν επηρεάζεται (το timestamp παραμένει στην ίδια θέση, ο glob `*` καλύπτει τον νέο suffix).

Επαληθεύτηκε με Python integration test (idempotency, backup#1 vs backup#2, reset μετά από renewal, annual boundary στις 365 μέρες) και με το `run-expvault` driver πάνω στην πραγματική dev εφαρμογή (πραγματικό state transition σε πραγματικά configured backup paths, self-healing state μετά τη διαγραφή δοκιμαστικής άδειας).

## Ευρήματα από static review (επιβεβαιωμένα)

Πρόταση εξωτερικού review (ChatGPT), ελεγμένη πάνω στο πραγματικό repo — μόνο τα επιβεβαιωμένα σημεία.

- **Destructive migration στο `adeia_ylika`** (`backend/database.py`) — Οι παλιές εγκεκριμένες ποσότητες σώζονται πριν το `DROP TABLE` (αθροιστικά ανά νόμιμη κατηγορία μέσω `classify_nomiki_katigoria`) και ξαναγράφονται μετά το `CREATE TABLE`. Επαληθεύτηκε με test script.
- **`restore_backup` χωρίς προστασία** (`backend/backup.py`) — Προστέθηκε `PRAGMA integrity_check` στο πηγαίο αρχείο πριν το restore, αυτόματο `expvault_prerestore_<ts>.db` snapshot της τρέχουσας βάσης, και atomic αντικατάσταση (`os.replace`). Επαληθεύτηκε με test script (άκυρο αρχείο απορρίπτεται χωρίς να πειράξει την ενεργή βάση).
- **`requirements.txt` λείπε** — Προστέθηκε με pinned εκδόσεις (pyinstaller 6.21.0, reportlab 5.0.0, openpyxl 3.1.5, python-docx 1.2.0), `build.ps1` και `CLAUDE.md` ενημερώθηκαν να το χρησιμοποιούν. (Το `package-lock.json` υπήρχε ήδη — αυτό το κομμάτι του αρχικού review ήταν λάθος.)
- **`max_keep` του backup χωρίς validation** (`backend/backup.py`) — Το `save_config()` κάνει τώρα clamp σε ακέραιο 1–365, με fallback σε 30 για μη έγκυρες τιμές.

## Static review — μικρής προτεραιότητας (ολοκληρώθηκαν)

- **Εύθραυστο pattern `onclick='fn(${escapeHtml(JSON.stringify(obj))})'`** — Αντικαταστάθηκε σε 7 αρχεία (`kiniseis.js`, `adeies.js`, `promitheftes.js`, `ylika.js`, `backup.js`, `pdf-import.js`, `templates.js`) με `data-*` attributes + `addEventListener`, ώστε τα δεδομένα να μην περνάνε ποτέ μέσα από HTML attribute string. Επαληθεύτηκε στην πραγματική εφαρμογή (row-click σε Άδειες/Υλικά/Προμηθευτές, edit button στις Κινήσεις, delete button στα PDF πρότυπα, delete button στα backup remotes) χωρίς regressions.
- **`backup.py`'s `_is_rclone(path)` λανθασμένη ταξινόμηση Windows paths** — Κάνει `':' in path`, οπότε κάθε Windows local path (`C:\...`) περιέχει `:` και ταξινομούνταν λανθασμένα ως rclone remote (δούλευε τυχαία επειδή το rclone μπορεί να διευθυνσιοδοτήσει και τοπικά paths, αλλά περνούσε άσκοπα από subprocess). Διορθώθηκε με αποκλεισμό του Windows drive-letter pattern (`^[A-Za-z]:[\\/]`) πριν τον έλεγχο `:`. Επαληθεύτηκε: τοπικό backup σε Windows path πλέον τρέχει σε ~10ms (`shutil.copy2`) αντί για subprocess σε rclone.exe.

## IPC hardening (backend-only, χωρίς αλλαγή renderer/preload)

Το `window.api.call(cmd, payload)` περνάει οποιοδήποτε `cmd` ατόφιο στο ήδη fixed allowlist των ~58 bridge commands — δεν ήταν ενεργά exploitable (καμία γνωστή XSS), αλλά αρκετά destructive commands ήταν προσβάσιμα χωρίς επιπλέον έλεγχο. Αντί για το πλήρες (και ριψοκίνδυνο) split σε allowlisted μεθόδους σε preload.js/renderer, στοχευμένο backend-only hardening σε 2 σημεία:

- **`restore_backup`** (`backend/backup.py`): δεχόταν οποιοδήποτε path string. Τώρα το `_known_backup_paths()` περιορίζει το restore μόνο σε paths που εμφανίζονται στο αποτέλεσμα του `list_backups()` για κάποιο από τα configured backup paths — δηλαδή μόνο ό,τι η ίδια η εφαρμογή έχει ήδη δείξει ως δικό της backup. Κλείνει το σενάριο "αντικατάσταση ενεργής βάσης με αυθαίρετο αρχείο από compromised renderer". Καμία αλλαγή στο UI χρειάστηκε — το `js/backup.js` ήδη περνάει το path ακριβώς όπως το επέστρεψε το `list_backups`.
- **`delete_*` οικογένεια** (`backend/bridge.py`): νέο `_int_id(payload)` επιβεβαιώνει θετικό ακέραιο πριν φτάσει σε `delete_yliko`, `delete_promitheftis`, `delete_adeia_yliko`, `delete_adeia`, `delete_kinisi`, `delete_pdf_template`. Οι υπόλοιπες delete εντολές (`delete_ypologismos`, `delete_kiniseis_by_parstatiko`, `delete_parstatiko_with_related`, `delete_remote`) δουλεύουν με string keys, όχι int ids — δεν εφαρμόζεται.

Επαληθεύτηκε με Python test (invalid ids απορρίπτονται, restore εκτός configured folder απορρίπτεται χωρίς να πειράξει την ενεργή βάση) και με το run-expvault driver πάνω στην πραγματική εφαρμογή (προσομοίωση επίθεσης με `restore_backup` σε αυθαίρετο Windows path → απορρίφθηκε· κανονικό delete μέσω UI → δούλεψε κανονικά).
