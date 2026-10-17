"""Cherche les codes CIM-10 et les rubriques « Résumé structuré » présents DANS le texte des documents PARHAF.

Usage : uv run python -I scripts/exploration/05_codes_dans_texte_parhaf.py
"""
import json
import re
from collections import Counter
from pathlib import Path

RACINE = Path(__file__).resolve().parents[2]
PARHAF = RACINE / "donnees" / "parhaf"
TEXTES = PARHAF / "standalone" / "textes"

# Un code CIM-10 entre crochets, ex. [K649], [C34.1], [Z51.1]
CODE_CROCHETS = re.compile(r"\[([A-Z]\d{2}\.?\d{0,2})\]")
# Un code CIM-10 « nu » (lettre + 2 chiffres + éventuellement point + 1-2 chiffres), hors mots
CODE_NU = re.compile(r"(?<![A-Za-z0-9])([A-TV-Z]\d{2}(?:\.\d{1,2}|\d{1,2})?)(?![A-Za-z0-9])")
RESUME = re.compile(r"r[ée]sum[ée] structur[ée]", re.I)
DA = re.compile(r"diagnostics? associ[ée]s?", re.I)


def main() -> None:
    patients = json.load(open(PARHAF / "standalone" / "patients.json", encoding="utf-8"))["data"]
    n_docs = 0
    avec_resume = Counter()
    avec_crochets = Counter()
    avec_da = Counter()
    codes_crochets_par_doc = Counter()
    da_non_vides = 0
    exemples_da = []
    accord_dp = desaccord_dp = 0
    codes_nus_hors_resume = Counter()
    docs_codes_nus = 0
    for p in patients:
        dp = p["suggested_scenario"]["primary_diagnosis"][0]["code"]
        for d in p["documents"]:
            n_docs += 1
            t = (TEXTES / d["path"]).read_text(encoding="utf-8")
            m = RESUME.search(t)
            if m:
                avec_resume[(p["specialty"], d["type"])] += 1
                bloc = t[m.start():]
                if DA.search(bloc):
                    avec_da[p["specialty"]] += 1
                    apres = bloc[DA.search(bloc).end():]
                    if not re.search(r"aucun|néant|non|pas de", apres[:200], re.I) or CODE_CROCHETS.search(apres):
                        da_non_vides += 1
                        if len(exemples_da) < 4:
                            exemples_da.append((p["id"], apres.strip()[:500]))
            codes = CODE_CROCHETS.findall(t)
            if codes:
                avec_crochets[(p["specialty"], d["type"])] += 1
                codes_crochets_par_doc[len(codes)] += 1
                if dp.replace(".", "") in {c.replace(".", "") for c in codes}:
                    accord_dp += 1
                else:
                    desaccord_dp += 1
            # codes nus hors bloc résumé structuré (ex. « HTA (I10) » dans le corps du texte)
            corps = t[:m.start()] if m else t
            nus = [c for c in CODE_NU.findall(corps) if not re.fullmatch(r"[A-Z]\d{2}\d{2}", c)]  # exclut les faux positifs type C34 12
            if nus:
                docs_codes_nus += 1
                codes_nus_hors_resume.update(nus)
    print(f"documents : {n_docs}")
    print(f"\ndocuments contenant une rubrique « Résumé structuré » : {sum(avec_resume.values())}")
    for k, n in avec_resume.most_common():
        print(f"   {n:5d}  {k[0]} / {k[1]}")
    print(f"\ndocuments contenant un code CIM-10 entre crochets : {sum(avec_crochets.values())}")
    for k, n in avec_crochets.most_common():
        print(f"   {n:5d}  {k[0]} / {k[1]}")
    print("   nombre de codes entre crochets par document :", dict(sorted(codes_crochets_par_doc.items())))
    print(f"   le DP du scénario figure parmi ces codes : {accord_dp} ; ne figure pas : {desaccord_dp}")
    print(f"\nrubriques « Diagnostics associés » dans un résumé structuré : {sum(avec_da.values())} documents ; avec contenu non vide : {da_non_vides}")
    for pid, ex in exemples_da:
        print(f"   --- {pid} :\n   {ex!r}")
    print(f"\ndocuments avec un code CIM-10 « nu » dans le corps (hors résumé) : {docs_codes_nus} (approximatif, motif large)")
    print("   codes les plus fréquents :", codes_nus_hors_resume.most_common(15))

    # Les CRH très courts (ambulatoire)
    courts = [(d["word_count"], p["id"]) for p in patients for d in p["documents"] if d["type"] == "CRH" and d["word_count"] < 100]
    print(f"\nCRH de moins de 100 mots : {len(courts)} ; spécialités :",
          Counter(pid.rsplit('-', 1)[0] for _, pid in courts).most_common())


if __name__ == "__main__":
    main()
