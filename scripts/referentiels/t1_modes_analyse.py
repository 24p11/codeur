"""Brief 8, étape 3 : de quoi compléter la liste des modes de prise en charge de la règle T1 (traitement répétitif).

1. Tous les codes codables des catégories Z49 et Z51, avec leur libellé officiel et la ou les lignes du guide où ils figurent déjà
   (modes de prise en charge résolus), ou « aucune ».
2. Sur les 100 000 lignes de la source des CRH synthétiques, les codes Z de mode de prise en charge (case_management_type) employés
   avec la règle T1 (coding_rule), avec leur effectif, en signalant ceux qui ne sont pas dans la liste T1 du guide.
Écrit donnees/prepare/situations/t1_codes_Z49_Z51.csv et t1_synthetiques_codes_Z.csv (hors git) et affiche les deux résultats.
"""
import csv
import sys
from collections import Counter
from pathlib import Path

import polars as pl

RACINE = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(RACINE / "scripts" / "chargement"))
from situations_commun import lire_guide  # noqa: E402
from synthetiques_commun import SOURCE, lire_index, normaliser_code  # noqa: E402

SORTIE = RACINE / "donnees" / "prepare" / "situations"


def main() -> None:
    fiches, desc = lire_index()
    lignes, _ = lire_guide(fiches, desc)
    ou = {}
    for l in lignes:
        for c in l["details"]["mode_prise_en_charge"]["codes"]:
            ou.setdefault(c["code"], []).append(l["code"])
    t1 = {c["code"] for l in lignes if l["code"] == "T1" for c in l["details"]["mode_prise_en_charge"]["codes"]}
    tableau = [(c, fiches[c]["libelle"], ", ".join(ou.get(c, [])) or "aucune") for c in sorted(fiches) if c[:3] in ("Z49", "Z51") and fiches[c]["codable"]]
    SORTIE.mkdir(parents=True, exist_ok=True)
    with open(SORTIE / "t1_codes_Z49_Z51.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f); w.writerow(["code", "libelle", "lignes_du_guide"]); w.writerows(tableau)
    print(f"=== 1. Codes codables de Z49 et Z51 ({len(tableau)}) et lignes du guide où ils figurent ===")
    for c, lib, l in tableau:
        print(f"  {c:8s} {lib[:70]:70s} {l}")
    df = pl.read_parquet(SOURCE, columns=["coding_rule", "case_management_type"]).filter(pl.col("coding_rule") == "T1")
    cpt = Counter(normaliser_code(z) if z and z != "DP" else "DP" for z in df["case_management_type"])
    print(f"\n=== 2. CRH synthétiques : lignes de règle T1 : {df.height} ; codes de mode de prise en charge ===")
    with open(SORTIE / "t1_synthetiques_codes_Z.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f); w.writerow(["code", "libelle", "effectif", "dans_liste_T1"])
        for c, n in cpt.most_common():
            lib = "(pathologie principale)" if c == "DP" else fiches.get(c, {}).get("libelle", "inconnu de l'index")
            dans = "oui" if c in t1 else "NON"
            w.writerow([c, lib, n, dans]); print(f"  {c:8s} {n:6d}  {dans:4s} {lib[:70]}")
    print(f"\nliste T1 du guide (résolue) : {', '.join(sorted(t1))}")


if __name__ == "__main__":
    main()
