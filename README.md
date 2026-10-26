# ΠΑΟΚ – Ημερολόγια αγώνων

Ημερολόγια iCal για τους αγώνες του ΠΑΟΚ σε **βόλεϊ**, **ποδόσφαιρο** και **μπάσκετ**, χωριστά για εντός και εκτός έδρας. Ενημερώνονται αυτόματα κάθε 6 ώρες.

## Συνδρομή από iPhone

Ρυθμίσεις → Ημερολόγιο → Λογαριασμοί → Προσθήκη λογαριασμού → Άλλο → **Προσθήκη ημερολογίου συνδρομής**, και επικόλληση του συνδέσμου:

| Ημερολόγιο | Σύνδεσμος |
|---|---|
| 🏐 Βόλεϊ – Εντός | `webcal://raw.githubusercontent.com/GabrielChatzi/PAOK-calendar/main/docs/volley-home.ics` |
| 🏐 Βόλεϊ – Εκτός | `webcal://raw.githubusercontent.com/GabrielChatzi/PAOK-calendar/main/docs/volley-away.ics` |
| ⚽ Ποδόσφαιρο – Εντός | `webcal://raw.githubusercontent.com/GabrielChatzi/PAOK-calendar/main/docs/football-home.ics` |
| ⚽ Ποδόσφαιρο – Εκτός | `webcal://raw.githubusercontent.com/GabrielChatzi/PAOK-calendar/main/docs/football-away.ics` |
| 🏀 Μπάσκετ – Εντός | `webcal://raw.githubusercontent.com/GabrielChatzi/PAOK-calendar/main/docs/basketball-home.ics` |
| 🏀 Μπάσκετ – Εκτός | `webcal://raw.githubusercontent.com/GabrielChatzi/PAOK-calendar/main/docs/basketball-away.ics` |

Αγώνες χωρίς ορισμένη ώρα μπαίνουν στις 18:00 (ώρα Ελλάδας) με την ένδειξη «(ώρα TBC)».

## Πηγές

- Βόλεϊ: [volleyleague.gr](https://www.volleyleague.gr/) (Volley League, League Cup)
- Ποδόσφαιρο: ESPN (Super League, ευρωπαϊκές διοργανώσεις)
- Μπάσκετ: [esake.gr](https://www.esake.gr/) (Basket League) και Euroleague (EuroCup)

## Πώς δουλεύει

Το [`build_calendars.py`](build_calendars.py) διαβάζει τις πηγές και γράφει τα `.ics` στο `docs/`. Το workflow [`update.yml`](.github/workflows/update.yml) το τρέχει κάθε 6 ώρες και αποθηκεύει μόνο όταν αλλάξει κάτι. Αν μια πηγή αποτύχει, τα αρχεία του αθλήματος μένουν ως είχαν και το workflow σημειώνεται αποτυχημένο.

Χειροκίνητη ενημέρωση: Actions → «Ενημέρωση ημερολογίων» → Run workflow.
