"""Charge les chapitres de la CIM-10 et les listes de codes du dépôt dans la base (brief 8, étape 1), clé secrète.

Source : docs/referentiels/cim/chapitres.csv ; docs/referentiels/cim/listes_codes/*.csv (nature cim) ;
docs/referentiels/ccam/listes_actes/*.csv (nature ccam, aucun fichier pour l'instant). Tables `chapitres` et `listes_codes`.
Contrôles avant écriture (le chargement est refusé si l'un échoue) : format `code,libelle` ; codes CIM à la forme codeur et
présents dans l'index (fiches), codables ou catégories avec descendants codables ; chapitres couvrant l'index.
Rechargeable sans doublon : insertion ou mise à jour sur la clé (liste, code) et sur le numéro de chapitre ; ne supprime rien
(un code retiré d'un fichier reste en base : le signaler, retrait à la main avec l'accord du responsable).

Usage : uv run python -I scripts/chargement/listes_charger.py [--controler]   (--controler : contrôles seuls, rien n'est écrit)
"""
import csv
import subprocess
import sys
from datetime import date
from pathlib import Path

from supabase import create_client

RACINE = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(RACINE / "scripts" / "tests"))
sys.path.insert(0, str(RACINE / "scripts" / "chargement"))
from connexion import charger_env  # noqa: E402
from synthetiques_commun import lire_index  # noqa: E402

CHAPITRES = RACINE / "docs" / "referentiels" / "cim" / "chapitres.csv"
DOSSIERS = [(RACINE / "docs" / "referentiels" / "cim" / "listes_codes", "cim"), (RACINE / "docs" / "referentiels" / "ccam" / "listes_actes", "ccam")]
SOURCE = "projet Stream (listes fournies le 23 octobre 2026)"


def version_fichier(f: Path) -> str:
    """Date du dernier commit qui touche le fichier, sinon la date du jour (fichier pas encore commité)."""
    r = subprocess.run(["git", "log", "-1", "--format=%cs", "--", str(f)], capture_output=True, text=True, cwd=RACINE)
    return r.stdout.strip() or date.today().isoformat() + " (non commité)"


def main() -> None:
    controler = "--controler" in sys.argv
    fiches, desc = lire_index()
    erreurs = []
    # 1. chapitres
    chapitres = list(csv.DictReader(open(CHAPITRES, encoding="utf-8")))
    if [c["numero"] for c in chapitres] != ["I", "II", "III", "IV", "V", "VI", "VII", "VIII", "IX", "X", "XI", "XII", "XIII", "XIV", "XV", "XVI", "XVII", "XVIII", "XIX", "XX", "XXI", "XXII"]:
        erreurs.append("chapitres.csv : les 22 chapitres attendus, dans l'ordre")
    def chapitre_de(code):
        cat = code[:3]
        return [c["numero"] for c in chapitres if c["premier_code"] <= cat <= c["dernier_code"]]
    hors = [k for k in fiches if len(chapitre_de(k)) != 1]
    if hors:
        erreurs.append(f"chapitres : {len(hors)} codes de l'index hors chapitre ou dans plusieurs ({hors[:5]})")
    print(f"chapitres : {len(chapitres)} ; codes de l'index couverts une et une seule fois : {len(fiches) - len(hors)} / {len(fiches)}")
    # 2. listes
    lignes = []
    for dossier, nature in DOSSIERS:
        for f in sorted(dossier.glob("*.csv")):
            rows = list(csv.reader(open(f, encoding="utf-8")))
            if not rows or rows[0] != ["code", "libelle"]:
                erreurs.append(f"{f.name} : en-tête attendu code,libelle"); continue
            codes = [r[0] for r in rows[1:] if r]
            if len(set(codes)) != len(codes):
                erreurs.append(f"{f.name} : codes en double")
            nb_cod = nb_cat = 0
            for r in rows[1:]:
                if not r: continue
                code, libelle = r[0], (r[1] if len(r) > 1 else None)
                if nature == "cim":
                    fi = fiches.get(code)
                    if not fi: erreurs.append(f"{f.name} : {code} absent de l'index"); continue
                    if fi["codable"]: nb_cod += 1
                    elif desc.get(code): nb_cat += 1
                    else: erreurs.append(f"{f.name} : {code} non codable sans descendant codable ({fi['statut_mco']})"); continue
                    if libelle != fi["libelle"]: erreurs.append(f"{f.name} : {code} libellé différent de l'index")
                lignes.append({"liste": f.stem, "nature": nature, "code": code, "libelle": libelle or None, "source": SOURCE, "version": version_fichier(f)})
            print(f"  {f.stem:46s} {len(codes):3d} codes ({nb_cod} codables, {nb_cat} catégories à descendants) version {version_fichier(f)}")
    print(f"listes : {len({l['liste'] for l in lignes})} ; lignes : {len(lignes)}")
    if erreurs:
        print("\nCONTRÔLES EN ÉCHEC :"); [print("  -", e) for e in erreurs]; sys.exit(1)
    print("contrôles : tous passés")
    if controler:
        print("--controler : rien n'a été écrit."); return
    env = charger_env()
    base = create_client(env["SUPABASE_URL"], env["SUPABASE_SECRET_KEY"])
    base.table("chapitres").upsert([{"numero": c["numero"], "ordre": int(c["ordre"]), "intitule": c["intitule"], "premier_code": c["premier_code"], "dernier_code": c["dernier_code"]} for c in chapitres], on_conflict="numero", returning="minimal").execute()
    for i in range(0, len(lignes), 500):
        base.table("listes_codes").upsert(lignes[i:i + 500], on_conflict="liste,code", returning="minimal").execute()
    en_base = base.table("listes_codes").select("liste", count="exact", head=True).execute().count
    print(f"chargé : {len(chapitres)} chapitres, {len(lignes)} lignes de listes (en base : {en_base} ; un écart signale des codes retirés des fichiers, à traiter à la main)")


if __name__ == "__main__":
    main()
