# TODO — branch `v2`

Εκκρεμότητες της νέας ανάπτυξης (δεν εμφανίζονται στο v1/main — εκεί μόνο διορθώσεις λαθών).

- [ ] Νέος σχεδιασμός σελίδων export Word/Excel — εκκρεμεί αποστολή reference αρχείων από τον
      χειριστή (#18)

- [ ] Presence detection μέσω MEGA/rclone sync — κάθε client γράφει periodic
      heartbeat (`presence.json`: user, last_seen, computer) στο ίδιο MEGA
      remote που ήδη χρησιμοποιείται για DB backup/sync (βλ. `js/backup.js`).
      Sync στην εκκίνηση + κάθε 1-2 λεπτά όσο τρέχει η εφαρμογή. UI: "●
      online" αν `last_seen` < 2 λεπτά, αλλιώς "τελευταία σύνδεση: πριν Χ".
      Reference implementation: `modules/cloud-sync.js` στο
      `lab-galatista-v2` worktree (IPC handlers `cloud-test`/`cloud-sync`,
      rclone sync pattern).

Ολοκληρωμένα items αυτού του branch στο [`DONE-v2.md`](DONE-v2.md).
