"""Vue d'ensemble des colonnes du parquet des CRH synthétiques.

Pour chaque colonne : type, nombre de valeurs manquantes, nombre de valeurs distinctes,
quelques exemples. Puis la fin du champ `report` sur quelques lignes, pour repérer le JSON.

Usage : uv run python -I scripts/exploration/07_colonnes_synthetiques.py
"""
from pathlib import Path

import polars as pl

RACINE = Path(__file__).resolve().parents[2]
FICHIER = RACINE / "donnees" / "synthetiques" / "run08_scenarios_reports_merged_20261007_160916.parquet"


def main() -> None:
    df = pl.read_parquet(FICHIER)
    n = df.height
    print(f"{n} lignes, {df.width} colonnes\n")
    print(f"{'colonne':40s} {'type':14s} {'manquants':>9s} {'distincts':>9s}  exemples")
    for col in df.columns:
        s = df[col]
        typ = str(s.dtype)
        manquants = s.null_count()
        if s.dtype == pl.List(pl.String):
            distincts = s.list.join("|").n_unique()
            ex = s.drop_nulls().head(2).to_list()
        else:
            distincts = s.n_unique()
            ex = s.drop_nulls().unique().head(3).to_list()
        ex_txt = ", ".join(repr(e)[:45] for e in ex)
        print(f"{col:40s} {typ[:14]:14s} {manquants:9d} {distincts:9d}  {ex_txt}")

    print("\n=== longueur de `report` (caractères) ===")
    lon = df["report"].str.len_chars()
    print(lon.describe())
    print("\n=== 400 derniers caractères de `report` sur 3 lignes (0, 50000, 99999) ===")
    for i in (0, 50000, 99999):
        print(f"\n--- ligne {i} ---")
        print(repr(df["report"][i][-400:]))
    print("\n=== 300 premiers caractères de `report` sur ces lignes ===")
    for i in (0, 50000, 99999):
        print(f"\n--- ligne {i} ---")
        print(repr(df["report"][i][:300]))


if __name__ == "__main__":
    main()
