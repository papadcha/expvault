# TODO

Ολοκληρωμένα items έχουν μετακομίσει στο [`DONE.md`](DONE.md).

## Static review — μικρής προτεραιότητας / defense-in-depth

Δεν είναι ενεργά exploitable με τον τρόπο που περιγράφτηκαν αρχικά, αλλά αξίζει σκλήρυνση/εκσυγχρονισμός όταν βρεθεί χρόνος:

- **`window.api.call(cmd, payload)` περνάει οποιοδήποτε `cmd` string ατόφιο** (`preload.js:4` → `main.js:139` → `backend/bridge.py`): το bridge έχει ήδη fixed allowlist ~58 hardcoded commands (όχι πραγματικό αυθαίρετο RPC), αλλά αρκετά από αυτά είναι destructive (`delete_*`, `restore_backup` με ελεύθερο path, `delete_remote`) και προσβάσιμα χωρίς επιπλέον έλεγχο. Αξίζει σκλήρυνση ως defense-in-depth — ειδικά επειδή το `pdf_parser.py` επεξεργάζεται εξωτερικά PDF τιμολόγια προμηθευτή, ένα πιο ρεαλιστικό μελλοντικό attack surface από χειρόγραφα πεδία σημειώσεων. Scope ασαφές (πλήρες split σε allowlisted μεθόδους αγγίζει δεκάδες call sites στο renderer) — να αποφασιστεί πριν ξεκινήσει.
