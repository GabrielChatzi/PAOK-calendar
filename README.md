# ΠΑΟΚ – Ημερολόγια αγώνων

Ημερολόγια iCal για τους αγώνες του ΠΑΟΚ σε **βόλεϊ**, **ποδόσφαιρο** και **μπάσκετ**, χωριστά για εντός και εκτός έδρας. Ενημερώνονται αυτόματα κάθε 6 ώρες.

**Συνδρομή από iPhone:** https://gabrielchatzi.github.io/PAOK-calendar/

| Άθλημα | Εντός έδρας | Εκτός έδρας |
|---|---|---|
| 🏐 Βόλεϊ | `volley-home.ics` | `volley-away.ics` |
| ⚽ Ποδόσφαιρο | `football-home.ics` | `football-away.ics` |
| 🏀 Μπάσκετ | `basketball-home.ics` | `basketball-away.ics` |

Αγώνες χωρίς ορισμένη ώρα μπαίνουν στις 18:00 (ώρα Ελλάδας) με την ένδειξη «(ώρα TBC)».

## Πηγές

- Βόλεϊ: [volleyleague.gr](https://www.volleyleague.gr/) (Volley League, League Cup)
- Ποδόσφαιρο: ESPN (Super League, ευρωπαϊκές διοργανώσεις)
- Μπάσκετ: [esake.gr](https://www.esake.gr/) (Basket League) και Euroleague (EuroCup)

## Πώς δουλεύει

Το [`build_calendars.py`](build_calendars.py) διαβάζει τις πηγές και γράφει τα `.ics` στο `docs/`, που δημοσιεύεται μέσω GitHub Pages. Το workflow [`update.yml`](.github/workflows/update.yml) το τρέχει κάθε 6 ώρες και αποθηκεύει μόνο όταν αλλάξει κάτι. Αν μια πηγή αποτύχει, τα αρχεία του αθλήματος μένουν ως είχαν και το workflow σημειώνεται αποτυχημένο.

Χειροκίνητη ενημέρωση: Actions → «Ενημέρωση ημερολογίων» → Run workflow.
