#!/usr/bin/env bash
mkdir -p docs; touch docs/.keep
python3 - <<'PY'
import build_calendars as b
men = ['ΠΑΟΚ','GMC ΔΡΑΜΑ 1986','Α.Ε.Κ.','Α.Σ.Ε ΔΟΥΚΑ','ΑΘΗΝΑΙΚΟΣ Α.Σ.Β.','ΑΡΗΣ ΝΙΚΑΙΑΣ OLYMPIC DIAGNOSTIC','Γ.Α.Σ ΚΙΛΚΙΣ','ΔΙΟΜΗΔΗΣ ΑΡΓΟΥΣ','Ε.Γ.Σ.Ν ΖΑΦΕΙΡΑΚΗΣ','ΙΩΝΙΚΟΣ AUTOVALUE','ΟΛΥΜΠΙΑΚΟΣ ΟΜΙΛΟΣ ΞΥΝΗ','Χ.Α.Ν.Θ']
women = ['ΠΑΟΚ','Α.Ε.Κ.','Α.Ε.Π. ΠΑΝΟΡΑΜΑ','Α.Ε.Σ.Χ. ΠΥΛΑΙΑΣ','ΑΘΗΝΑΙΚΟΣ Α.Σ.Β.','ΑΝΑΓΕΝΝΗΣΗ ΑΡΤΑΣ','Γ.Α.Σ ΚΑΜΑΤΕΡΟΥ','ΛΕΩΝΙΔΑΣ ΑΓ.ΑΝΑΡΓ.','Ο.Φ. Ν. ΙΩΝΙΑΣ','ΠΡΟΣΟΤΣΑΝΗ ΔΡΑΜΑΣ']
for w, names in ((False, men), (True, women)):
    print("pairs found:", len(b._OXE_LOGOS.get(w, [])) if w in b._OXE_LOGOS else "-")
    for n in names: print(("W " if w else "M ") + n, "->", b.oxe_logo(n, w).split("/")[-1] or "—")
    print("slugs:", [x[0] for x in b._OXE_LOGOS[w]])
PY
