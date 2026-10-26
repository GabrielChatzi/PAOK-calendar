# Αγώνες ΠΑΟΚ

Πρόγραμμα, αποτελέσματα και ημερολόγια iCal για όλα τα τμήματα του ΠΑΟΚ. Ενημερώνονται αυτόματα κάθε 6 ώρες.

**Ιστοσελίδα:** https://gabrielchatzi.github.io/PAOK-calendar/

Από τη σελίδα μπορείς να φιλτράρεις ανά άθλημα, τμήμα (ανδρών, γυναικών) και έδρα, και να κάνεις συνδρομή στα ημερολόγια από iPhone ή Android.

## Τμήματα και πηγές

| Τμήμα | Διοργανώσεις | Πηγή |
|---|---|---|
| ⚽ Ποδόσφαιρο | Super League, Ευρώπη, Κύπελλο Ελλάδας | ESPN, ΕΠΟ |
| ⚽ Ποδόσφαιρο Γυναικών | Α' Εθνική, Κύπελλο | ΕΠΟ |
| 🏀 Μπάσκετ | Basket League, EuroCup | esake.gr, Euroleague |
| 🏀 Μπάσκετ Γυναικών | Women's Basketball League 1 | basket.gr |
| 🏐 Βόλεϊ | Volley League, League Cup, Κύπελλο | volleyleague.gr, ΕΟΠΕ |
| 🏐 Βόλεϊ Γυναικών | Volley League Γυναικών, Κύπελλο | ΕΟΠΕ (Data Project) |
| 🤾 Χάντμπολ (ανδρών, γυναικών) | Handball Premier, Α1 Γυναικών, Κύπελλα | ΟΧΕ |
| 🤽 Πόλο (ανδρών, γυναικών) | Water Polo League | waterpololeague.gr |

Αγώνες χωρίς ορισμένη ώρα μπαίνουν στις 18:00 (ώρα Ελλάδας) με την ένδειξη «(ώρα TBC)».

## Ημερολόγια

Κάθε τμήμα έχει δύο αρχεία στο `docs/`, `<τμήμα>-home.ics` και `<τμήμα>-away.ics`, π.χ. `football-women-away.ics`. Σύνδεσμος για συνδρομή:

```
https://gabrielchatzi.github.io/PAOK-calendar/<αρχείο>.ics
```

Οι παλιοί σύνδεσμοι `raw.githubusercontent.com/.../docs/<αρχείο>.ics` συνεχίζουν να δουλεύουν.

## Πώς δουλεύει

Το [`build_calendars.py`](build_calendars.py) διαβάζει τις πηγές και γράφει στο `docs/` τα `.ics` και το `matches.json`, που διαβάζει η σελίδα [`docs/index.html`](docs/index.html). Το workflow [`update.yml`](.github/workflows/update.yml) το τρέχει κάθε 6 ώρες και αποθηκεύει μόνο όταν αλλάξει κάτι. Αν μια πηγή αποτύχει, το τμήμα της μένει ως είχε και το workflow σημειώνεται αποτυχημένο.

Χειροκίνητη ενημέρωση: Actions → «Ενημέρωση ημερολογίων» → Run workflow. Για ένα μόνο τμήμα τοπικά: `python3 build_calendars.py handball-women`.
