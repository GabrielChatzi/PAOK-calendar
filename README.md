# PAOKalendar: δεδομένα

Αυτόν τον κλάδο τον γράφει μόνο το workflow `update.yml` (κλάδος `main`): το πρόγραμμα
(`matches.json`), τις βαθμολογίες (`standings.json`), την κατάσταση (`status.json`) και τα ημερολόγια
(`*.ics`), μαζί με ένα αντίγραφο της σελίδας για το GitHub Pages. Η Vercel δεν φτιάχνει εκδόσεις από
αυτόν (`vercel.json`)· η σελίδα διαβάζει τα αρχεία μέσω του `api/data.js`.
