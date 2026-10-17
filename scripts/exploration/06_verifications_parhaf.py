"""Vérifications complémentaires sur PARHAF (version JSON), à la suite des décisions du §4.2 du cadrage.

1. Patients retenus : tous sauf ceux dont le dossier ne comprend que de l'anatomopathologie.
2. Règles de repérage des blocs à retirer du texte (résumé structuré recopié, liste de
   « diagnostics fréquemment associés »), contrôle qu'elles ne retirent rien d'autre, exemples.
3. Recherche d'autres résidus de gabarit de rédaction.
4. Diagnostics associés des CRH dont le résumé structuré est recopié (information à part).
5. Valeurs distinctes de type_of_care, admission_mode, discharge_mode.

Usage : uv run python -I scripts/exploration/06_verifications_parhaf.py
Aucun fichier n'est modifié.
"""
import json
import re
from collections import Counter
from pathlib import Path

RACINE = Path(__file__).resolve().parents[2]
PARHAF = RACINE / "donnees" / "parhaf"
TEXTES = PARHAF / "standalone" / "textes"

# Règle A : une ligne entière « Résumé structuré » (tolère accents, casse, deux-points), jusqu'à la fin du texte.
REGLE_A = re.compile(r"^[ \t]*r[ée]sum[ée] structur[ée][ \t]*:?[ \t]*$", re.I | re.M)
# Règle B : une ligne entière commençant par « Diagnostics fréquemment associés », jusqu'à la fin du texte.
REGLE_B = re.compile(r"^[ \t]*diagnostics? fr[ée]quemment associ[ée]s?.*$", re.I | re.M)
CODE_CROCHETS = re.compile(r"\[([A-Z]\d{2}[A-Za-z0-9.+]{0,4})\]")


def titre(t):
    print(f"\n===== {t} =====")


def main():
    patients = json.load(open(PARHAF / "standalone" / "patients.json", encoding="utf-8"))["data"]
    textes = {}
    for p in patients:
        for d in p["documents"]:
            textes[d["path"]] = (TEXTES / d["path"]).read_text(encoding="utf-8")

    titre("1. Patients retenus (exclusion des dossiers ne comprenant que de l'anatomopathologie)")
    combos = Counter(tuple(d["type"] for d in p["documents"]) for p in patients)
    print("  composition des 10 cas atypiques (combinaisons rares) :")
    for combo, n in combos.most_common():
        if n < 20:
            print(f"    {n:3d}  {' > '.join(combo)}   contient ANAPATH : {'ANAPATH' in combo}")
    exclus = [p for p in patients if all(d["type"] == "ANAPATH" for d in p["documents"])]
    retenus = [p for p in patients if not all(d["type"] == "ANAPATH" for d in p["documents"])]
    print(f"  patients exclus : {len(exclus)} ({sum(len(p['documents']) for p in exclus)} documents)")
    print(f"  patients retenus : {len(retenus)} ({sum(len(p['documents']) for p in retenus)} documents)")
    print("  documents ANAPATH restant chez les patients retenus :",
          sum(d['type'] == 'ANAPATH' for p in retenus for d in p['documents']))
    print("  patients retenus par pool :", Counter(p["pool"] for p in retenus).most_common())
    print("  patients retenus par nombre de documents :", sorted(Counter(len(p["documents"]) for p in retenus).items()))

    titre("2. Règles de repérage des blocs à retirer")
    for nom, regle in (("A - Résumé structuré", REGLE_A), ("B - Diagnostics fréquemment associés", REGLE_B)):
        touches = []
        for p in retenus:
            for d in p["documents"]:
                t = textes[d["path"]]
                m = regle.search(t)
                if m:
                    bloc = t[m.start():]
                    touches.append((p["id"], d["type"], len(t), m.start(), bloc))
        print(f"\n  Règle {nom} : {len(touches)} documents touchés")
        print("   nombre d'occurrences du motif par document :",
              Counter(len(regle.findall(textes[d['path']])) for p in retenus for d in p['documents'] if regle.search(textes[d['path']])))
        for pid, typ, lon, pos, bloc in touches:
            codes = CODE_CROCHETS.findall(bloc)
            print(f"    {pid:32s} {typ:4s} texte={lon:5d} car. | bloc retiré={len(bloc):4d} car. ({100*len(bloc)/lon:4.1f} %) | codes dans le bloc={len(codes)}")
        # Contrôle : le bloc retiré ne contient-il que des lignes « de gabarit » ?
        lignes = Counter()
        for *_, bloc in touches:
            for l in bloc.splitlines():
                l = l.strip()
                if l and not CODE_CROCHETS.search(l):
                    lignes[re.sub(r"\d+", "N", l)[:70]] += 1
        print("   lignes du bloc retiré SANS code entre crochets (à lire : ne doit rien contenir du compte rendu) :")
        for l, n in lignes.most_common(40):
            print(f"     {n:3d}  {l!r}")
    # Documents avec codes entre crochets NON couverts par A ou B
    titre("   Contrôle : codes entre crochets hors des blocs A et B")
    hors = []
    for p in retenus:
        for d in p["documents"]:
            t = textes[d["path"]]
            corps = t
            for regle in (REGLE_A, REGLE_B):
                m = regle.search(corps)
                if m:
                    corps = corps[:m.start()]
            if CODE_CROCHETS.search(corps):
                i = CODE_CROCHETS.search(corps).start()
                hors.append((p["id"], d["type"], repr(corps[max(0, i-150):i+80])))
    print(f"  documents retenus ayant encore un code entre crochets après application de A et B : {len(hors)}")
    for h in hors:
        print("   ", h)

    titre("   Exemples avant / après (fin du texte)")
    montres = 0
    for p in retenus:
        for d in p["documents"]:
            t = textes[d["path"]]
            m = REGLE_A.search(t) or REGLE_B.search(t)
            if m and montres < 3 and (montres != 1 or REGLE_B.search(t)):
                montres += 1
                print(f"\n  --- {p['id']} / {d['type']} ---")
                print("  AVANT (300 derniers caractères du texte conservé + début du bloc) :")
                print("  " + repr(t[max(0, m.start()-300):m.start()+200]))
                print("  APRÈS (fin du texte nettoyé) :")
                print("  " + repr(t[:m.start()].rstrip()[-300:]))

    titre("3. Autres résidus de gabarit (recherche de phrases suspectes hors blocs A et B)")
    suspects = {
        "liste initiale": re.compile(r"liste initiale", re.I),
        "texte libre, sans codage": re.compile(r"sans codage", re.I),
        "Diagnostic principal motivant": re.compile(r"diagnostic principal motivant", re.I),
        "Mode de prise en charge (médecine": re.compile(r"mode de prise en charge \(", re.I),
        "Acte principal :": re.compile(r"^acte principal\s*:", re.I | re.M),
        "Durée de séjour :": re.compile(r"^dur[ée]e de s[ée]jour\s*:", re.I | re.M),
        "code CIM": re.compile(r"code CIM", re.I),
        "CCAM": re.compile(r"\bCCAM\b"),
        "Diagnostics associés (ligne)": re.compile(r"^[ \t]*diagnostics? associ[ée]s?[ \t]*:?[ \t]*$", re.I | re.M),
        "scénario": re.compile(r"sc[ée]nario", re.I),
        "rédacteur / relecteur": re.compile(r"r[ée]dacteur|relecteur", re.I),
        "consigne": re.compile(r"consigne", re.I),
        "fictif / fictive": re.compile(r"fictif|fictive", re.I),
        "PARTAGES": re.compile(r"PARTAGES"),
        "lorem / xxx / à compléter": re.compile(r"lorem|xxx|à compl[ée]ter|\[à ", re.I),
        "balises/markdown (**, ##)": re.compile(r"\*\*|^#{1,3} ", re.M),
    }
    for nom, regle in suspects.items():
        docs = []
        for p in retenus:
            for d in p["documents"]:
                t = textes[d["path"]]
                for r in (REGLE_A, REGLE_B):
                    m = r.search(t)
                    if m:
                        t = t[:m.start()]
                m = regle.search(t)
                if m:
                    docs.append((p["id"], d["type"], repr(t[max(0, m.start()-60):m.end()+60])))
        print(f"\n  « {nom} » : {len(docs)} documents")
        for x in docs[:4]:
            print("    ", x)

    titre("4. Diagnostics associés des CRH dont le résumé structuré est recopié")
    for p in retenus:
        for d in p["documents"]:
            t = textes[d["path"]]
            m = REGLE_A.search(t)
            if not m:
                continue
            bloc = t[m.start():]
            print(f"\n  {p['id']} (DP scénario {p['suggested_scenario']['primary_diagnosis'][0]['code']}) :")
            for l in bloc.splitlines():
                l = l.strip()
                if l:
                    print("    ", l[:140])

    titre("5. Valeurs distinctes des variables du scénario (patients retenus)")
    for champ in ("type_of_care", "admission_mode", "discharge_mode"):
        c = Counter(p["suggested_scenario"].get(champ) for p in retenus)
        print(f"\n  {champ} : {len(c)} valeurs distinctes (dont None)")
        for v, n in c.most_common():
            print(f"    {n:5d}  {v!r}")
    print("\n  type_of_care par spécialité (quelques exemples) :")
    for spe in ("CHIRURGIE VISCERALE", "PNEUMOLOGIE", "OBSTETRIQUE", "CANCERO ADULTE"):
        c = Counter(p["suggested_scenario"].get("type_of_care") for p in retenus if p["specialty"] == spe)
        print(f"    {spe} : {c.most_common(6)}")


if __name__ == "__main__":
    main()
