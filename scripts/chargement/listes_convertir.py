"""Lot B-référentiels (brief 8, étape 1) : conversion des listes de codes du projet Stream au format commun de `codeur`.

Entrée : docs/referentiels/cim/listes_codes/*.csv (formats d'origine : `code;description`, `code;libelle`, `icd_code;description`).
Sortie : les mêmes fichiers réécrits au format commun `code,libelle` (virgule, UTF-8, codes à la forme codeur, libellé officiel
de l'index), plus docs/referentiels/cim/listes_codes/README.md (source, usage, retraits). L'index est lu dans la base (fiches).

Remplacements et retraits (décision du 23 octobre 2026) : un code absent du kit ou non codable sans descendant est retiré
quand ses équivalents sont déjà dans la liste (O040-O049 → O04x0..3 déjà présents ; Z94801 → Z94802/3/4/9 présents ;
E11i/E11ni → E11 et ses subdivisions présents) ou quand il n'a aucun équivalent (Z86090, Z2028). Rien n'est ajouté.

Usage : uv run python -I scripts/chargement/listes_convertir.py [--essai]   (--essai : affiche la table des retraits, n'écrit rien)
"""
import csv
import re
import sys
from pathlib import Path

RACINE = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(RACINE / "scripts" / "chargement"))
from synthetiques_commun import lire_index  # noqa: E402

DOSSIER = RACINE / "docs" / "referentiels" / "cim" / "listes_codes"
USAGES = {  # usage dans le guide des situations cliniques (version 1) ; les autres listes sont disponibles pour plus tard
    "icd_codes_legal_abortion": "règle IVG (pathologie)", "icd_codes_medical_abortion": "règle ITG (pathologie)",
    "icd_codes_diabetes_chronic": "règle T9-diabetes (pathologie)", "icd_codes_iron_deficiency_anemia": "règle T10-fer (pathologie)",
    "icd_codes_spontaneous_vertex_delivery": "règle T12 (pathologie)", "icd_codes_liveborn_infants": "règle T13 (pathologie)",
    "icd_codes_chronic_attack": "règle D6 (codes spécifiques de poussée aiguë, à confirmer à l'étape 3)",
}


def normaliser(c: str) -> str:
    return re.sub(r"[^A-Z0-9+]", "", (c or "").upper().replace(".", ""))


def main() -> None:
    essai = "--essai" in sys.argv
    fiches, desc = lire_index()
    readme = ["# Listes de codes CIM-10", "",
              "Listes issues du **projet Stream** (génération de CRH synthétiques), fournies par Rémi le 23 octobre 2026, converties au format commun "
              "`code,libelle` (virgule, UTF-8, codes à la forme `codeur` : sans point, extension PMSI collée ; libellé officiel de l'index recode-icd "
              "`65701d6_atih-2025`). Une catégorie sans point (`Z95`, `Z80`) désigne la catégorie et ses descendants codables. Chargées dans la table "
              "`listes_codes` (nature `cim`) par `scripts/chargement/listes_charger.py` ; les fichiers du dépôt restent la source.", "",
              "| Fichier | Codes | Usage (guide des situations cliniques, version 1) |", "|---|---|---|"]
    retraits = []
    for f in sorted(DOSSIER.glob("*.csv")):
        brut = [r for r in csv.reader(open(f, encoding="utf-8-sig"), delimiter=";" if ";" in open(f, encoding="utf-8-sig").readline() else ",") if r]
        lignes, vus = [], set()
        for r in brut[1:]:
            c = normaliser(r[0])
            if not c or c in vus:
                continue
            fi = fiches.get(c)
            if not fi:
                retraits.append((f.stem, r[0], "inconnu du kit 2025", "aucun équivalent" if c in ("Z2028",) else "équivalents déjà dans la liste (E11 et ses subdivisions)")); continue
            if not fi["codable"] and not desc.get(c):
                # équivalents : descendants codables (code tronqué), ou frères codables (code supprimé), déjà présents dans la liste
                presents = {normaliser(x[0]) for x in brut[1:] if x}
                freres = sorted(k for k in fiches if k != c and fiches[k]["codable"] and (k.startswith(c) or (fi["statut_mco"] == "supprime" and k[:-1] == c[:-1])) and k in presents)
                equiv = "équivalents déjà dans la liste (" + ", ".join(freres) + ")" if freres else "aucun équivalent"
                retraits.append((f.stem, r[0], "non codable sans descendant (" + fi["statut_mco"] + ")", equiv)); continue
            vus.add(c); lignes.append((c, fi["libelle"]))
        readme.append(f"| `{f.name}` | {len(lignes)} | {USAGES.get(f.stem, 'disponible, non citée par le guide')} |")
        if not essai:
            with open(f, "w", newline="", encoding="utf-8") as g:
                w = csv.writer(g); w.writerow(["code", "libelle"]); w.writerows(lignes)
    readme += ["", "## Codes retirés à la conversion (23 octobre 2026)", "",
               "Un code est retiré seulement s'il n'existe pas dans le kit ATIH 2025 ou s'il n'y est pas codable sans descendant codable, et que ses équivalents sont déjà dans la liste ou n'existent pas. Rien n'a été ajouté.", "",
               "| Liste | Code d'origine | Motif | Équivalents |", "|---|---|---|---|"]
    for l, c, m, e in retraits:
        readme.append(f"| `{l}` | `{c}` | {m} | {e} |")
    texte = "\n".join(readme) + "\n"
    print(texte)
    if not essai:
        (DOSSIER / "README.md").write_text(texte, encoding="utf-8")
        print(f"{len(list(DOSSIER.glob('*.csv')))} listes réécrites, README écrit, {len(retraits)} codes retirés")
    else:
        print("ESSAI : rien n'a été écrit.")


if __name__ == "__main__":
    main()
