"""Compare la version Hugging Face (parquet) et la version standalone (JSON + .txt) de PARHAF.

Vérifie : nombre de patients, nombre de documents, identifiants présents d'un seul côté,
et identité des textes (parquet contre fichier .txt) pour les patients communs.

Usage : uv run python -I scripts/exploration/02_comparer_versions_parhaf.py
"""
import json
from collections import Counter
from pathlib import Path

import polars as pl

RACINE = Path(__file__).resolve().parents[2]
PARHAF = RACINE / "donnees" / "parhaf"
PARQUET = PARHAF / "data" / "train-00000-of-00001.parquet"
INDEX_JSON = PARHAF / "standalone" / "patients.json"
TEXTES = PARHAF / "standalone" / "textes"


def main() -> None:
    pq = pl.read_parquet(PARQUET)
    with open(INDEX_JSON, encoding="utf-8") as f:
        brut = json.load(f)
    print("clés de premier niveau du JSON :", list(brut.keys()))
    for k, v in brut.items():
        if k != "data":
            print(f"  {k} = {v!r}"[:300])
    patients_json = brut["data"]

    # Dans le parquet, `documents` est un dictionnaire de listes (une liste par champ),
    # et non une liste de documents : on compte les types pour avoir le nombre de documents.
    n_docs_pq = pq.select(pl.col("documents").struct.field("type").list.len().sum()).item()
    print(f"\nparquet : {pq.height} patients, {n_docs_pq} documents")
    print(f"json    : {len(patients_json)} patients, {sum(len(p['documents']) for p in patients_json)} documents")

    ids_pq = set(pq["id"].to_list())
    ids_js = {p["id"] for p in patients_json}
    print(f"\nidentifiants uniques : parquet {len(ids_pq)}, json {len(ids_js)}")
    seulement_js = sorted(ids_js - ids_pq)
    seulement_pq = sorted(ids_pq - ids_js)
    print(f"présents seulement dans le JSON    : {len(seulement_js)} -> {seulement_js}")
    print(f"présents seulement dans le parquet : {len(seulement_pq)} -> {seulement_pq}")

    # Détail des patients absents du parquet
    par_id = {p["id"]: p for p in patients_json}
    if seulement_js:
        print("\n--- patients absents du parquet ---")
        for pid in seulement_js:
            p = par_id[pid]
            docs = p["documents"]
            print(f"{pid} | {p['specialty']} | pool={p['pool']} | {len(docs)} doc(s)")
            for d in docs:
                chemin = TEXTES / d["path"]
                existe = chemin.exists()
                taille = chemin.stat().st_size if existe else None
                print(f"    {d['type']:12s} {d['path']}  fichier présent={existe} taille={taille} word_count={d.get('word_count')}")
            print(f"    scénario DP : {p['suggested_scenario'].get('primary_diagnosis')}")
            print(f"    clés présentes : {sorted(p.keys())}")

    # Comparaison des textes pour les patients communs
    print("\n--- comparaison des textes (patients communs) ---")
    communs = ids_pq & ids_js
    n_docs = 0
    identiques = 0
    diff_apres_strip = 0
    differents = []
    types_differents = 0
    nb_docs_differents = 0
    for ligne in pq.filter(pl.col("id").is_in(list(communs))).iter_rows(named=True):
        p = par_id[ligne["id"]]
        d = ligne["documents"]  # dictionnaire de listes -> on le remet en liste de documents
        docs_pq = [dict(zip(d.keys(), valeurs)) for valeurs in zip(*d.values())]
        docs_js = p["documents"]
        if len(docs_pq) != len(docs_js):
            nb_docs_differents += 1
            continue
        for dpq, djs in zip(docs_pq, docs_js):
            n_docs += 1
            if dpq["type"] != djs["type"]:
                types_differents += 1
            texte_fichier = (TEXTES / djs["path"]).read_text(encoding="utf-8")
            if dpq["text"] == texte_fichier:
                identiques += 1
            elif dpq["text"].strip() == texte_fichier.strip():
                diff_apres_strip += 1
            else:
                differents.append((ligne["id"], djs["path"], len(dpq["text"]), len(texte_fichier)))
    print(f"patients communs : {len(communs)} ; patients dont le nombre de documents diffère : {nb_docs_differents}")
    print(f"documents comparés : {n_docs}")
    print(f"  texte strictement identique        : {identiques}")
    print(f"  identique après suppression des blancs de bord : {diff_apres_strip}")
    print(f"  texte différent                    : {len(differents)}")
    print(f"  type différent                     : {types_differents}")
    for d in differents[:10]:
        print("   ", d)

    # Les clés présentes dans le JSON mais pas dans le parquet (et inversement)
    cles_js = Counter()
    for p in patients_json:
        cles_js.update(p.keys())
        for d in p["documents"]:
            cles_js.update("documents." + k for k in d.keys())
    print("\nclés du JSON (nombre de patients/documents qui les portent) :")
    for k, n in sorted(cles_js.items()):
        print(f"  {k:30s} {n}")
    print("\ncolonnes du parquet :", pq.columns)
    print("champs de documents dans le parquet :", pq.schema["documents"])


if __name__ == "__main__":
    main()
