"""Étape 3 du lot B2 : tirage reproductible de l'échantillon de 500 CRH synthétiques.

Lignes éligibles : règle de docs/chargement.md §3.1 (JSON réparable, codes du scénario codables, clés rattachées),
texte présent, une seule variante par scénario. Trois répartitions entre les six gabarits : proportionnelle, égale,
mixte (minimum par gabarit, le reste au prorata). Graine fixe. Sans --ecrire, affiche seulement les répartitions.

Usage : uv run python -I scripts/chargement/synthetiques_echantillon.py [--repartition proportionnelle|egale|mixte] [--ecrire]
"""
import argparse
import random
import sys
from collections import Counter
from pathlib import Path

import polars as pl

sys.path.insert(0, str(Path(__file__).resolve().parent))
from synthetiques_commun import PREPARE, SOURCE, affinables, lire_index, motifs_exclusion

GRAINE = 20261022          # date de la décision (AAAAMMJJ)
TAILLE = 500
MINIMUM_MIXTE = 40         # minimum par gabarit dans la répartition mixte
GABARITS = ["medical_outpatient", "medical_inpatient", "surgery_outpatient", "surgery_inpatient", "medical_outpatient_onco", "medical_inpatient_onco"]
COLONNES = ["generation_id", "id_scenario", "variante", "template_name", "report", "icd_primary_code", "icd_secondary_code",
            "case_management_type", "coding_rule", "specialty", "specialite_source", "nb_das", "mode_hospit", "TPEC"]


def lignes_eligibles(fiches, desc) -> pl.DataFrame:
    df = pl.read_parquet(SOURCE, columns=COLONNES)
    garder, motifs, nb_aff = [], Counter(), []
    for rep, dp, das, z in zip(df["report"], df["icd_primary_code"], df["icd_secondary_code"], df["case_management_type"]):
        das_l = das.to_list() if das is not None else []
        raisons, obj = motifs_exclusion(rep, dp, das_l, z, fiches, desc)
        if not raisons and not (obj.get("CR") or "").strip():
            raisons.add("texte vide")
        motifs.update(raisons)
        garder.append(not raisons)
        nb_aff.append(len(affinables(dp, das_l, z, fiches, desc)))
    df = df.with_columns(pl.Series("eligible", garder), pl.Series("nb_affinables", nb_aff),
                         pl.col("template_name").str.replace(r"\.txt$", "").alias("gabarit"))
    el = df.filter(pl.col("eligible"))
    print(f"Lignes éligibles : {el.height} / {df.height} ; motifs d'exclusion : {dict(motifs)}")
    # une variante par scénario : la plus petite valeur de `variante` (après tri stable), proposition à valider
    el = el.sort(["id_scenario", "variante", "generation_id"]).unique(subset=["id_scenario"], keep="first", maintain_order=True)
    print(f"Après une variante par scénario : {el.height} lignes (scénarios distincts)")
    return el.drop("report")


def quotas(repartition: str, effectifs: dict[str, int]) -> dict[str, int]:
    total = sum(effectifs.values())
    if repartition == "proportionnelle":
        q = {g: round(TAILLE * effectifs[g] / total) for g in GABARITS}
    elif repartition == "egale":
        base, reste = divmod(TAILLE, len(GABARITS))
        q = {g: base + (1 if i < reste else 0) for i, g in enumerate(GABARITS)}
    elif repartition == "mixte":
        reste = TAILLE - MINIMUM_MIXTE * len(GABARITS)
        q = {g: MINIMUM_MIXTE + round(reste * effectifs[g] / total) for g in GABARITS}
    else:
        raise SystemExit(f"répartition inconnue : {repartition}")
    # ajustement des arrondis sur le gabarit le plus nombreux
    plus_gros = max(GABARITS, key=lambda g: effectifs[g])
    q[plus_gros] += TAILLE - sum(q.values())
    return q


def tirer(el: pl.DataFrame, repartition: str) -> pl.DataFrame:
    effectifs = {g: el.filter(pl.col("gabarit") == g).height for g in GABARITS}
    q = quotas(repartition, effectifs)
    rng = random.Random(GRAINE)
    tires = []
    for g in GABARITS:
        ids = el.filter(pl.col("gabarit") == g)["generation_id"].sort().to_list()
        tires += rng.sample(ids, q[g])
    return el.filter(pl.col("generation_id").is_in(tires)).sort("generation_id")


def decrire(ech: pl.DataFrame, nom: str) -> None:
    print(f"\n=== Répartition « {nom} » : {ech.height} lignes ===")
    for g in GABARITS:
        print(f"  {g:26s} {ech.filter(pl.col('gabarit') == g).height:4d}")
    cr = Counter(ech["coding_rule"].fill_null("(vide)").to_list())
    print(f"  coding_rule : {len(cr)} valeurs distinctes ; " + ", ".join(f"{k} {v}" for k, v in cr.most_common(8)))
    sp = Counter(ech["specialty"].fill_null("(nul)").to_list())
    print(f"  specialty : {len(sp)} valeurs distinctes ; " + ", ".join(f"{k} {v}" for k, v in sp.most_common(6)))
    nd = Counter(ech["nb_das"].to_list())
    print(f"  nb_das : " + ", ".join(f"{k} → {v}" for k, v in sorted(nd.items())))
    cm = Counter(ech["mode_hospit"].to_list()); tp = Counter(ech["TPEC"].to_list())
    print(f"  mode_hospit : {dict(cm)} ; TPEC : {dict(tp)} ; code Z (hors « DP ») : {ech.filter(pl.col('case_management_type') != 'DP').height}")
    print(f"  lignes avec au moins un code affinable : {ech.filter(pl.col('nb_affinables') > 0).height}")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--repartition", choices=["proportionnelle", "egale", "mixte"])
    ap.add_argument("--ecrire", action="store_true")
    a = ap.parse_args()
    fiches, desc = lire_index()
    el = lignes_eligibles(fiches, desc)
    print("Effectifs éligibles par gabarit : " + ", ".join(f"{g} {el.filter(pl.col('gabarit') == g).height}" for g in GABARITS))
    for nom in ([a.repartition] if a.repartition else ["proportionnelle", "egale", "mixte"]):
        ech = tirer(el, nom)
        decrire(ech, nom)
        if a.ecrire and a.repartition:
            PREPARE.mkdir(parents=True, exist_ok=True)
            sortie = PREPARE / "echantillon_500.csv"
            ech.select(["generation_id", "id_scenario", "variante", "gabarit", "coding_rule", "specialty", "nb_das", "nb_affinables"]).write_csv(sortie)
            print(f"\nÉcrit : {sortie} ({ech.height} lignes, graine {GRAINE}, répartition {nom})")


if __name__ == "__main__":
    main()
