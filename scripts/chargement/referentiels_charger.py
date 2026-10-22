"""Charge l'index des codes et les formulations de la livraison recode-icd dans la base (lot B3, partie index).

Sources (hors git) : donnees/referentiels/recode-icd/<version>/extrait/<livraison>/{codes.csv, formulations.csv,
descendants_codables.csv}. Tables : fiches (tous les codes, codables ou non, contenu vide), synonymes
(formulations + une ligne de libellé officiel par code), descendants_codables.

Rechargeable sans doublon : « insérer ou mettre à jour » sur les clés (fiches.code ; synonymes code+formulation+source ;
descendants noeud+code). Le script NE SUPPRIME JAMAIS RIEN : changer de livraison est une opération à part.

Usage :
  uv run python -I scripts/chargement/referentiels_charger.py --controler      # contrôles seuls, sans base
  uv run python -I scripts/chargement/referentiels_charger.py                  # contrôles puis chargement (clé secrète)
  uv run python -I scripts/chargement/referentiels_charger.py --paquet 2000
"""
import argparse
import csv
import re
import sys
from pathlib import Path

import polars as pl

RACINE = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(RACINE / "scripts" / "tests"))

VERSION = "65701d6_atih-2025"
LIV = RACINE / "donnees" / "referentiels" / "recode-icd" / "65701d6_atih-2025" / "extrait" / "recode-icd_fiches_generation_65701d6_atih-2025"
SORTIE = RACINE / "donnees" / "prepare" / "referentiels"
FORME = re.compile(r"^[A-Z][0-9]{2}[0-9]{0,3}(\+[0-9]{1,2})?$")
SOURCE_LIBELLE = "ATIH kit 2025"


def controler() -> dict:
    """Lit la livraison, vérifie, prépare les trois tables et écrit les résultats dans donnees/prepare/referentiels/."""
    SORTIE.mkdir(parents=True, exist_ok=True)
    codes = pl.read_csv(LIV / "codes.csv")
    form = pl.read_csv(LIV / "formulations.csv")
    desc = pl.read_csv(LIV / "descendants_codables.csv")
    erreurs = []

    # 1. Forme des codes
    hors = codes.filter(~pl.col("code_atih").str.contains(FORME.pattern))
    if hors.height: erreurs.append(f"{hors.height} codes hors forme : {hors['code_atih'].head(5).to_list()}")
    if codes["code_atih"].n_unique() != codes.height: erreurs.append("codes en double dans codes.csv")
    if codes["libelle"].null_count(): erreurs.append("libellés vides dans codes.csv")
    print(f"codes : {codes.height} (codables {codes['codable_mco'].sum()}, non codables {(~codes['codable_mco']).sum()}) ; forme : {'OK' if not hors.height else 'ERREUR'}")

    # 2. Formulations -> codes de l'index ; descendants -> codes de l'index
    orphelines = form.join(codes.select("code_atih"), on="code_atih", how="anti")
    if orphelines.height: erreurs.append(f"{orphelines.height} formulations sans code dans l'index")
    connus = codes["code_atih"].to_list()
    d_orph = desc.filter(~pl.col("noeud_atih").is_in(connus) | ~pl.col("code_atih").is_in(connus))
    if d_orph.height: erreurs.append(f"{d_orph.height} descendants hors index")
    d_non_cod = desc.join(codes.filter(~pl.col("codable_mco")).select(pl.col("code_atih")), on="code_atih", how="semi")
    if d_non_cod.height: erreurs.append(f"{d_non_cod.height} descendants déclarés codables mais non codables dans codes.csv")
    print(f"formulations : {form.height} sur {form['code_atih'].n_unique()} codes ; toutes rattachées à l'index : {'OK' if not orphelines.height else 'ERREUR'}")
    print(f"descendants : {desc.height} couples pour {desc['noeud_atih'].n_unique()} nœuds ; rattachés à l'index : {'OK' if not d_orph.height else 'ERREUR'} ; tous codables : {'OK' if not d_non_cod.height else 'ERREUR'}")

    # 3. Tables préparées
    fiches = codes.select(
        pl.col("code_atih").alias("code"), "libelle", pl.col("codable_mco").alias("codable"),
        "statut_mco", "interdit_dp", "interdit_dr", "interdit_das", pl.lit(VERSION).alias("version_livraison"))
    synonymes = pl.concat([
        form.select(pl.col("code_atih").alias("code"), "formulation",
                    pl.when(pl.col("source") == "CIM-10 index").then(pl.lit("index")).otherwise(pl.lit("synonyme")).alias("origine"),
                    "source", pl.lit(VERSION).alias("version_livraison")),
        codes.select(pl.col("code_atih").alias("code"), pl.col("libelle").alias("formulation"), pl.lit("libelle").alias("origine"),
                     pl.lit(SOURCE_LIBELLE).alias("source"), pl.lit(VERSION).alias("version_livraison")),
    ])
    n_avant = synonymes.height
    synonymes = synonymes.unique(subset=["code", "formulation", "source"], keep="first")
    print(f"synonymes préparés : {synonymes.height} ({form.height} formulations + {codes.height} libellés, {n_avant - synonymes.height} doublons écartés) ; origine : {synonymes['origine'].value_counts(sort=True).to_dict(as_series=False)}")
    descendants = desc.select(pl.col("noeud_atih").alias("noeud"), pl.col("code_atih").alias("code"), "libelle", "ordre_kit",
                              pl.lit(VERSION).alias("version_livraison")).unique(subset=["noeud", "code"], keep="first")
    print(f"descendants préparés : {descendants.height}")

    # 4. DP de PARHAF
    dp = pl.read_csv(RACINE / "donnees" / "prepare" / "parhaf" / "codes_dp_a_verifier.csv", separator=";")
    j = dp.join(codes.select("code_atih", pl.col("libelle").alias("libelle_officiel"), "codable_mco", "statut_mco"), left_on="code", right_on="code_atih", how="left")
    a_part = j.filter(pl.col("codable_mco").is_null() | (pl.col("codable_mco") == False))  # noqa: E712
    print(f"DP de PARHAF : {dp['effectif'].sum()} dossiers, {dp.height} codes ; codables : {j.filter(pl.col('codable_mco') == True)['effectif'].sum()} dossiers ; "  # noqa: E712
          f"à traiter à part : {a_part['effectif'].sum()} dossiers ({a_part.height} codes : {a_part['code'].to_list()})")
    # Liste nominative des dossiers à traiter à part
    import json
    dossiers = []
    for f in sorted((RACINE / "donnees" / "prepare" / "parhaf" / "documents").glob("*.json")):
        d = json.load(open(f, encoding="utf-8"))
        c = d["codage"]["ensembles"][0]["code"]
        if c in set(a_part["code"]):
            st = a_part.filter(pl.col("code") == c)["statut_mco"][0]
            dossiers.append({"id_source": d["id_source"], "code_dp": c, "statut": st or "inconnu_du_kit", "libelle_parhaf": d["codage"]["ensembles"][0]["libelle"]})
    with open(SORTIE / "parhaf_dp_a_traiter_a_part.csv", "w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=["id_source", "code_dp", "statut", "libelle_parhaf"], delimiter=";")
        w.writeheader(); w.writerows(dossiers)
    print(f"  liste écrite : {SORTIE / 'parhaf_dp_a_traiter_a_part.csv'} ({len(dossiers)} dossiers)")
    for err in erreurs: print("  ERREUR :", err)
    if erreurs: raise SystemExit("contrôles en échec : chargement refusé")
    return {"fiches": fiches, "synonymes": synonymes, "descendants": descendants}


def upsert(base, table: str, lignes: list[dict], cle: str, paquet: int) -> int:
    n = 0
    for i in range(0, len(lignes), paquet):
        base.table(table).upsert(lignes[i:i + paquet], on_conflict=cle, returning="minimal").execute()
        n += len(lignes[i:i + paquet])
        print(f"  {table} : {n}/{len(lignes)}", end="\r", flush=True)
    print()
    return n


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--controler", action="store_true", help="contrôles seuls, aucune écriture")
    ap.add_argument("--paquet", type=int, default=2000)
    args = ap.parse_args()
    tables = controler()
    if args.controler:
        print("\n(contrôles seuls : rien n'a été chargé)")
        return
    from supabase import create_client
    from connexion import charger_env
    env = charger_env()
    base = create_client(env["SUPABASE_URL"], env["SUPABASE_SECRET_KEY"])
    print("\nchargement (insérer ou mettre à jour ; jamais de suppression) :")
    upsert(base, "fiches", tables["fiches"].to_dicts(), "code", args.paquet)
    upsert(base, "synonymes", tables["synonymes"].to_dicts(), "code,formulation,source", args.paquet)
    upsert(base, "descendants_codables", tables["descendants"].to_dicts(), "noeud,code", args.paquet)
    for t in ("fiches", "synonymes", "descendants_codables"):
        n = base.table(t).select("*", count="exact", head=True).execute().count
        print(f"  {t} en base : {n}")


if __name__ == "__main__":
    main()
