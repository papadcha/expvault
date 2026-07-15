ΒΙΒΛΙΟ ΕΚΡΗΚΤΙΚΩΝ ΥΛΩΝ (EXPVAULT) — CHECKLIST ΓΙΑ ΝΕΟ RELEASE
================================================================

## Σε κάθε νέο release

1. `VERSIONS.md` — πρόσθεσε νέα εγγραφή στην κορυφή: `vX.Y.Z — YYYY-MM-DD`
   ακολουθούμενο από γραμμή παυλών (5+ `-`), μετά ελεύθερο κείμενο με τις
   αλλαγές. Ενημέρωσε και το "Τρέχουσα έκδοση" στην κορυφή του αρχείου.
2. `allowed-versions.json` — **ΑΝΤΙΚΑΤΕΣΤΗΣΕ** το `versions[]` array ώστε να
   περιέχει ΜΟΝΟ το entry της νέας έκδοσης (μην κρατάς τα παλιά — η πολιτική
   εδώ είναι "μόνο η τρέχουσα έκδοση θεωρείται επιβεβαιωμένα ασφαλής για
   downgrade", ρητά τεκμηριωμένη στο ίδιο το `notice` πεδίο· ο παλιός
   κώδικας δεν είναι επαληθευμένος έναντι του τρέχοντος schema της βάσης).
   Πρόσθεσε το πραγματικό `downloadUrl` (μορφή:
   `https://github.com/papadcha/expvault/releases/download/vX.Y.Z/ExpVault.Setup.X.Y.Z.exe`),
   και ενημέρωσε `latestRecommendedVersion`/`safeDowngradeFloor` σε αυτήν —
   ΕΚΤΟΣ αν η νέα έκδοση θεωρείται δοκιμαστική/όχι έτοιμη για όλους.
   (Ιστορικό: αυτό ξέφυγε ανάμεσα σε v1.1.3 και v1.1.8 — τα releases απλά
   πρόσθεταν νέα entries χωρίς να αφαιρούν τα παλιά, με αποτέλεσμα το
   "Ιστορικό Εκδόσεων" modal να δείχνει πολλές εκδόσεις ως "ασφαλές
   downgrade" ενώ το banner έλεγε "μόνο η τρέχουσα" — διορθώθηκε στην v1.1.9.)
3. `package.json` — bump `version`.
4. Commit + push στο `main` (branch που διαβάζει το raw.githubusercontent.com
   fetch — αν αλλάξει ποτέ το default branch, ενημέρωσε και το URL μέσα στο
   `version-check.js`).
5. `.\build.ps1` — παράγει τον installer.
6. Δημιούργησε το GitHub release `vX.Y.Z` με το asset
   `ExpVault Setup X.Y.Z.exe` (attention: το build.ps1 βγάζει το αρχείο με
   κενά, το `allowed-versions.json`/downloadUrl περιμένει τελείες —
   έλεγξε το πραγματικό filename στο GitHub release πριν κλειδώσεις το URL).

## Αν μια έκδοση αποδειχτεί προβληματική

**Δεν αρκεί να αλλάξεις μόνο το `allowed-versions.json`.** Το expvault έχει
πραγματικό `electron-updater` (main.js `setupAutoUpdater()`) που κατεβάζει
και εγκαθιστά αυτόματα ό,τι το GitHub releases API αναφέρει ως "latest" —
ανεξάρτητα από το τι λέει το `allowed-versions.json`. Αν αφήσεις το
προβληματικό release ως "Latest" στο GitHub, το electron-updater θα
συνεχίσει να το προωθεί σε όποιον δεν έχει ενημερωθεί ακόμα, ό,τι κι αν
δείχνει το banner/modal.

Βήματα:
1. Στο GitHub → Releases → το προβληματικό release → **Edit** →
   σημείωσέ το ως **"Set as a pre-release"** (ή κατέβασέ το εντελώς αν
   είναι πολύ πρόσφατο) ώστε να πάψει να είναι το "latest" για το
   electron-updater feed.
2. Στο `allowed-versions.json`: όρισε `notice` με σύντομη περιγραφή του
   προβλήματος, χαμήλωσε `latestRecommendedVersion` στην τελευταία γνωστά
   καλή έκδοση, και άφησε την προβληματική έκδοση εκτός του `versions[]`
   array (ή μέσα με σαφή σημείωση) — απουσία της από το `versions[]` την
   κάνει να εμφανίζεται κόκκινη ("δεν συνιστάται downgrade") στο modal.
3. Commit + push.
4. Αν έχει ήδη κυκλοφορήσει σε κάποιους χρήστες: θα δουν το rollback
   banner στην επόμενη εκκίνηση (μόνο σε packaged/`app.isPackaged` build,
   ελέγχεται ~4s μετά το άνοιγμα του παραθύρου).

## Fine-grained GitHub PAT για το "Αναφορά Προβλήματος"

Το `report-version-issue` IPC (στο `version-check.js`) δημιουργεί πραγματικό
GitHub Issue μέσω ενός token bundled στο πακεταρισμένο app
(`github-token.json`, gitignored — ΔΕΝ μπαίνει στο git). Το token αυτό
είναι **διαφορετικό από του lab-galatista** — scoped αποκλειστικά στο
`papadcha/expvault`.

### Δημιουργία (πρώτη φορά / rotation)

1. GitHub → Settings (προσωπικό λογαριασμό) → Developer settings →
   Fine-grained tokens → Generate new token.
2. **Repository access**: Only select repositories → `papadcha/expvault`.
3. **Permissions**: Repository permissions → **Issues: Read and write**.
   Τίποτα άλλο — όχι Contents, όχι Actions, όχι κανένα άλλο scope.
4. Generate, αντέγραψε την τιμή.
5. Αποθήκευσε τοπικά ως `C:\expvault\github-token.json`:
   ```json
   { "token": "github_pat_..." }
   ```
   Το αρχείο είναι ήδη στο `.gitignore` και στο `package.json`'s
   `build.files` (μπαίνει στο packaged app, όχι στο git repo).
6. Αν χρειαστεί ανάκληση αργότερα (π.χ. spam issues από κάποια παλιά
   διαρρευσμένη έκδοση): revoke το token από το ίδιο μενού, δημιούργησε
   νέο με το ΙΔΙΟ στενό scope, αντικατέστησε την τιμή στο
   `github-token.json`, νέο release. Οι ήδη εγκατεστημένες παλιές εκδόσεις
   κρατάνε το ανενεργό token μέχρι να αναβαθμιστούν — το
   `report-version-issue` απλά θα αποτυγχάνει σιωπηλά γι' αυτές.

### Γιατί embedded token και όχι server-side proxy

Η εφαρμογή δεν έχει δικό της backend server — μόνο τοπικές εγκαταστάσεις
χωρίς κοινή υποδομή. Ένα proxy θα σήμαινε να στηθεί/συντηρείται ξεχωριστός
server μόνο για αυτή τη λειτουργία. Το token είναι σκόπιμα scoped ΜΟΝΟ σε
"Issues: write" σε αυτό το ένα repo — ακόμα κι αν εξαχθεί από το .exe, το
χειρότερο δυνατό είναι spam issues, όχι αλλαγή κώδικα/releases/δεδομένων.
