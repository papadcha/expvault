# TODO

Ολοκληρωμένα items έχουν μετακομίσει στο [`DONE.md`](DONE.md).

## Static review — μικρής προτεραιότητας / defense-in-depth

Δεν είναι ενεργά exploitable με τον τρόπο που περιγράφτηκαν αρχικά, αλλά αξίζει σκλήρυνση/εκσυγχρονισμός όταν βρεθεί χρόνος:

- **Εύθραυστο pattern `onclick='fn(${escapeHtml(JSON.stringify(obj))})'`**: εμφανίζεται σε 8 αρχεία (`kiniseis.js`, `adeies.js`, `promitheftes.js`, `ylika.js`, `backup.js`, `pdf-import.js`, `templates.js`). Επαληθεύτηκε ότι ο συνδυασμός `JSON.stringify` + `escapeHtml` είναι σήμερα ασφαλής (το πρώτο χειρίζεται το escaping μέσα στο JS string, το δεύτερο το HTML attribute boundary), αλλά είναι εύθραυστο — μια μελλοντική απλοποίηση του `escapeHtml` θα το έσπαγε αθόρυβα. Αντικατάσταση με `addEventListener` + `data-*` attributes θα το έκανε πιο ανθεκτικό δομικά.
- **`window.api.call(cmd, payload)` περνάει οποιοδήποτε `cmd` string ατόφιο** (`preload.js:4` → `main.js:139` → `backend/bridge.py`): το bridge έχει ήδη fixed allowlist ~58 hardcoded commands (όχι πραγματικό αυθαίρετο RPC), αλλά αρκετά από αυτά είναι destructive (`delete_*`, `restore_backup` με ελεύθερο path, `delete_remote`) και προσβάσιμα χωρίς επιπλέον έλεγχο. Αξίζει σκλήρυνση ως defense-in-depth — ειδικά επειδή το `pdf_parser.py` επεξεργάζεται εξωτερικά PDF τιμολόγια προμηθευτή, ένα πιο ρεαλιστικό μελλοντικό attack surface από χειρόγραφα πεδία σημειώσεων.

## Άλλα

- **`backup.py`'s `_is_rclone(path)` λανθασμένη ταξινόμηση Windows paths**: κάνει `':' in path`, οπότε κάθε Windows local path (`C:\...`) περιέχει `:` και ταξινομείται λανθασμένα ως rclone remote. Φαίνεται να "δουλεύει" τυχαία επειδή το rclone μπορεί να διευθυνσιοδοτήσει και τοπικά paths, αλλά περνάει άσκοπα από subprocess αντί για απλό `shutil.copy2`. Εντοπίστηκε παρεμπιπτόντως κατά την υλοποίηση του backup ανά άδεια, δεν διορθώθηκε (εκτός scope τότε).
