"""Valeurs des colonnes de codage et de contexte des CRH synthétiques.

Usage : uv run python -I scripts/exploration/10_colonnes_codage_synthetiques.py
"""
from pathlib import Path

import polars as pl

RACINE = Path(__file__).resolve().parents[2]
FICHIER = RACINE / "donnees" / "synthetiques" / "run08_scenarios_reports_merged_20261007_160916.parquet"


def effectifs(df, col, k=25):
    print(f"\n--- {col} : {df[col].n_unique()} valeurs distinctes, {df[col].null_count()} manquants ---")
    for v, n in df[col].value_counts(sort=True).head(k).iter_rows():
        print(f"  {n:6d}  {str(v)[:110]!r}")


def main() -> None:
    df = pl.read_parquet(FICHIER)
    for col in ("template_name", "coding_rule", "TPEC", "DPEC", "mode_hospit", "admission_type", "branche",
                "population", "cage", "admission_mode", "discharge_disposition", "specialite_source",
                "dp_substitue", "enrichi", "racine_reparee", "model", "sexe", "los", "nb_das"):
        effectifs(df, col)
    effectifs(df, "case_management_type", 15)
    print("\n--- case_management_type + description (10 premiers) ---")
    for z, d, n in df.group_by("case_management_type", "case_management_type_description").len().sort("len", descending=True).head(10).iter_rows():
        print(f"  {n:6d}  {z:8s} {d[:90]}")
    effectifs(df, "situa", 12)
    effectifs(df, "specialty", 15)
    effectifs(df, "hospital", 5)
    print("\n--- règle de codage × situa (5 règles les plus fréquentes, une situa chacune) ---")
    for r, s, n in df.group_by("coding_rule", "situa").len().sort("len", descending=True).head(8).iter_rows():
        print(f"  {n:6d}  {r:8s} {s[:100]}")
    print("\n--- codes ---")
    print("  icd_primary_code avec point :", df["icd_primary_code"].str.contains(r"\.").sum(),
          "; avec + :", df["icd_primary_code"].str.contains(r"\+").sum(),
          "; longueur :", df["icd_primary_code"].str.len_chars().value_counts(sort=True).head(6).to_dict(as_series=False))
    print("  nombre de DAS (icd_secondary_code) :", df["icd_secondary_code"].list.len().value_counts(sort=True).sort("icd_secondary_code").to_dict(as_series=False))
    print("  procedure manquante :", df["procedure"].null_count(), "; procedure vide :", (df["procedure"] == "").sum())
    print("\n--- dates ---")
    print("  date_entry :", df["date_entry"].min(), "->", df["date_entry"].max())
    duree = (df["date_discharge"] - df["date_entry"]).dt.total_days()
    print("  (date_discharge - date_entry) == los :", (duree == df["los"]).sum(), "/", df.height)
    print("  age == age2 :", (df["age"] == df["age2"]).sum())
    print("  timestamp de génération :", df["timestamp"].min(), "->", df["timestamp"].max())
    print("\n--- identifiants ---")
    print("  source_row_id uniques :", df["source_row_id"].n_unique(), "; generation_id uniques :", df["generation_id"].n_unique())
    print("  id_scenario uniques :", df["id_scenario"].n_unique(), "; lignes par id_scenario :",
          df["id_scenario"].value_counts()["count"].value_counts(sort=True, name="n").head(5).to_dict(as_series=False))
    print("  variante :", df["variante"].value_counts(sort=True).head(6).to_dict(as_series=False))
    print("\n--- gabarit × TPEC × mode_hospit ---")
    for g, t, m, n in df.group_by("template_name", "TPEC", "mode_hospit").len().sort("len", descending=True).iter_rows():
        print(f"  {n:6d}  {g:30s} {t:28s} {m}")


if __name__ == "__main__":
    main()
