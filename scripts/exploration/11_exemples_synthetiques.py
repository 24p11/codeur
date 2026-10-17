"""Affiche des CRH synthétiques complets : colonnes du scénario, texte CR et partie codage du JSON.

Usage :
  uv run python -I scripts/exploration/11_exemples_synthetiques.py                # deux exemples par défaut
  uv run python -I scripts/exploration/11_exemples_synthetiques.py 281471 66135  # par source_row_id
Les exemples par défaut : une hospitalisation complète de médecine avec DAS et règle de codage,
et une chirurgie ambulatoire avec code Z.
"""
import json
import sys
from pathlib import Path

import polars as pl

RACINE = Path(__file__).resolve().parents[2]
FICHIER = RACINE / "donnees" / "synthetiques" / "run08_scenarios_reports_merged_20261007_160916.parquet"
COLONNES_SCENARIO = ["source_row_id", "template_name", "specialty", "TPEC", "DPEC", "mode_hospit", "age", "sexe",
                     "date_entry", "date_discharge", "los", "admission_mode", "discharge_disposition",
                     "icd_primary_code", "icd_primary_description", "icd_secondary_code", "case_management_type",
                     "case_management_type_description", "procedure", "text_procedure", "coding_rule", "situa",
                     "ghm2", "dp_origine", "dp_substitue", "enrichi", "codes_ajoutes", "id_scenario", "variante"]


def choisir(df):
    """Premier exemple de chaque critère dont le JSON est analysable."""
    def premier(filtre):
        for ligne in df.filter(filtre).head(50).iter_rows(named=True):
            try:
                json.loads(ligne["report"], strict=False)
                return ligne["source_row_id"]
            except json.JSONDecodeError:
                continue
        raise SystemExit("aucun exemple analysable pour ce critère")
    a = premier((pl.col("template_name") == "medical_inpatient.txt") & (pl.col("coding_rule") != "other")
                & (pl.col("coding_rule") != "") & (pl.col("icd_secondary_code").list.len() == 3))
    b = premier((pl.col("template_name") == "surgery_outpatient.txt") & (pl.col("case_management_type") != "DP")
                & (pl.col("icd_secondary_code").list.len() == 1))
    return [a, b]


def main() -> None:
    df = pl.read_parquet(FICHIER)
    ids = [int(x) for x in sys.argv[1:]] or choisir(df)
    for rid in ids:
        ligne = df.filter(pl.col("source_row_id") == rid).row(0, named=True)
        print("\n" + "#" * 100)
        print(f"# source_row_id {rid}")
        for c in COLONNES_SCENARIO:
            v = ligne[c]
            if hasattr(v, "to_list"):
                v = v.to_list()
            print(f"#   {c:34s} = {v!r}")
        obj = json.loads(ligne["report"], strict=False)
        print("\n--- texte CR (clé \"CR\") ---")
        print(obj["CR"])
        reste = {k: v for k, v in obj.items() if k != "CR"}
        print("\n--- autres clés du JSON ---")
        print(json.dumps(reste, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
