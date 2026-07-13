# TODO

Ιδέες για μελλοντική υλοποίηση — ελεγμένες ως προς εφικτότητα πάνω στην τρέχουσα αρχιτεκτονική, όχι ακόμα υλοποιημένες.

## 1. Alert χαμηλού υπολοίπου άδειας

Όταν το υπόλοιπο μιας άδειας (ανά νομική κατηγορία) πέσει κάτω από **3× τον μέσο όρο των αγορών** της, εμφάνιση toast στον χρήστη.

**Trigger points:**
- Κατά την καταχώρηση κίνησης (μετά το save μιας νέας εγγραφής στο `kiniseis`).
- Σε κάθε επόμενη εκκίνηση της εφαρμογής (ίδιο μοτίβο με `checkVersionNotice`, `main.js:328`, `setTimeout` μετά το `ready-to-show`).

**Υλοποίηση:**
- Το υπόλοιπο υπολογίζεται ήδη δυναμικά: `get_adeia_katigoria_remaining()` (`backend/database.py:381`) — `egekrimeni_posotita` μείον SUM κινήσεων ανά (`adeia_id`, `nomiki_katigoria`).
- Χρειάζεται νέο query: μέσος όρος ποσότητας ανά κίνηση τύπου `ΕΙΣΑΓΩΓΗ`, group by `adeia_id`, `nomiki_katigoria` — δεν υπάρχει ήδη.
- Νέα bridge command (π.χ. `check_adeia_thresholds`) που συνδυάζει τα δύο queries και επιστρέφει λίστα αδειών/κατηγοριών κάτω από το κατώφλι.
- Toast μέσω του υπάρχοντος `window._showToast` (`index.html:1066`).

## 2. Backup ανά άδεια (event-driven, όχι ημερολογιακό) + ετήσιο backup

**Δύο backups ανά άδεια**, με trigger από **query πάνω στις κινήσεις της άδειας** (όχι από `imerominia_lixis`):
- **Backup #1**: όταν το υπόλοιπο άδειας πέσει κάτω από 3× μέσο όρο αγορών (ίδιο κατώφλι με το alert της §1).
- **Backup #2** (με toast ειδοποίησης): όταν το υπόλοιπο πλησιάζει το μηδέν (π.χ. <1× μέσο όρο αγορών).
- Μοιράζεται τη λογική υπολογισμού remaining/average με το feature #1 — ίδιο query, διαφορετικά thresholds.

**Ετήσιο backup**: παραμένει **ημερολογιακό** — 1 φορά τον χρόνο από την τελευταία φορά, ελέγχεται στο εκκίνηση εφαρμογής (πέρασε >1 χρόνος από `last_backup`; τρέχει).

**Υλοποίηση:**
- Το backup ήδη υποστηρίζει manual (`js/backup.js` → `bkNow()` → `py('run_backup')`) και auto-on-close (`main.js:333`) — δεν υπάρχει interval/cron μηχανισμός, άρα οι νέοι έλεγχοι θα τρέχουν σαν startup checks, όχι background scheduler.
- `backup_config.json` χρειάζεται νέα πεδία:
  - `last_annual_backup` (ημερομηνία) για το ετήσιο.
  - per-άδεια markers (π.χ. `{adeia_id: {backup1_done: bool, backup2_done: bool}}`) ώστε να μην ξανατρέχει backup #1/#2 επαναληπτικά μετά την πρώτη ενεργοποίηση για την ίδια άδεια/κατηγορία — πρέπει να καθοριστεί πότε γίνεται reset αυτών των markers (π.χ. σε νέα άδεια, σε ανανέωση εγκεκριμένης ποσότητας).

## Ανοιχτά σημεία πριν την υλοποίηση
- Reset λογική για τα per-άδεια backup markers (πότε "ξαναφορτίζουν").
- Αν μια άδεια έχει πολλές νομικές κατηγορίες με διαφορετικό υπόλοιπο, ποιο κατώφλι κρίνει το backup — το χειρότερο (πρώτο που πέφτει) ή όλες;

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
