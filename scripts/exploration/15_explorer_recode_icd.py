"""Explore la livraison recode-icd (donnees/referentiels/recode-icd/<version>/extrait/, hors git) :
codes.csv, formulations.csv, descendants_codables.csv, cards_library/index.csv ; puis confronte les DP de PARHAF
(donnees/prepare/parhaf/codes_dp_a_verifier.csv) à l'index : codables ? libellés identiques ?

Usage : uv run python -I scripts/exploration/15_explorer_recode_icd.py
"""
import re
from pathlib import Path

import polars as pl

RACINE = Path(__file__).resolve().parents[2]
LIV = RACINE / "donnees" / "referentiels" / "recode-icd" / "65701d6_atih-2025" / "extrait" / "recode-icd_fiches_generation_65701d6_atih-2025"
FORME = re.compile(r"^[A-Z][0-9]{2}[0-9]{0,3}(\+[0-9])?$")


def titre(t): print(f"\n===== {t} =====")


def main():
    titre("codes.csv")
    codes = pl.read_csv(LIV / "codes.csv")
    print("colonnes :", codes.columns, "| lignes :", codes.height)
    print(codes.head(5))
    print("code_atih uniques :", codes["code_atih"].n_unique(), "| vides :", codes["code_atih"].null_count())
    print("codable_mco :", codes["codable_mco"].value_counts(sort=True).to_dict(as_series=False))
    print("statut_mco :", codes["statut_mco"].value_counts(sort=True).to_dict(as_series=False))
    for c in ("interdit_dp", "interdit_dr", "interdit_das", "millesime_kit", "version_livraison"):
        if c in codes.columns: print(f"{c} :", codes[c].value_counts(sort=True).head(6).to_dict(as_series=False))
    hors_forme = codes.filter(~pl.col("code_atih").str.contains(FORME.pattern))
    print("code_atih hors forme attendue (lettre, 2 chiffres, 0 à 3 chiffres, +N facultatif) :", hors_forme.height, hors_forme["code_atih"].head(10).to_list())
    print("avec point :", codes["code_atih"].str.contains(r"\.").sum(), "| avec '+' :", codes["code_atih"].str.contains(r"\+").sum(),
          "| longueur :", codes["code_atih"].str.len_chars().value_counts(sort=True).to_dict(as_series=False))
    print("exemples Z992* :", codes.filter(pl.col("code_atih").str.starts_with("Z992")).select("code_atih", "code", "libelle", "codable_mco", "statut_mco").to_dicts())
    print("exemples E11* (5 premiers) :", codes.filter(pl.col("code_atih").str.starts_with("E11")).select("code_atih", "libelle", "codable_mco").head(5).to_dicts())
    print("libellés : vides", codes["libelle"].null_count(), "; en majuscules :", (codes["libelle"] == codes["libelle"].str.to_uppercase()).sum())

    titre("formulations.csv")
    form = pl.read_csv(LIV / "formulations.csv")
    print("colonnes :", form.columns, "| lignes :", form.height)
    print(form.head(5))
    print("source :", form["source"].value_counts(sort=True).to_dict(as_series=False))
    print("codes distincts :", form["code_atih"].n_unique(), "| formulations distinctes :", form["formulation"].n_unique())
    print("formulations dont le code n'est pas dans codes.csv :", form.join(codes.select("code_atih"), on="code_atih", how="anti").height)
    print("formulations sur des codes non codables :", form.join(codes.filter(~pl.col("codable_mco")).select("code_atih"), on="code_atih", how="semi").height)
    print("doublons (code, formulation) :", form.height - form.select("code_atih", "formulation").unique().height)
    print("exemples I10 :", form.filter(pl.col("code_atih") == "I10").select("formulation", "source").head(8).to_dicts())

    titre("descendants_codables.csv")
    desc = pl.read_csv(LIV / "descendants_codables.csv")
    print("colonnes :", desc.columns, "| lignes :", desc.height)
    print(desc.head(5))
    print("nœuds distincts :", desc[desc.columns[0]].n_unique())
    print("exemples Z992 :", desc.filter(pl.col(desc.columns[0]).is_in(["Z992", "Z99.2"])).to_dicts()[:6])
    print("exemples E11 :", desc.filter(pl.col(desc.columns[0]).is_in(["E11"])).head(4).to_dicts())

    titre("cards_library/index.csv")
    idx = pl.read_csv(LIV / "cards_library" / "index.csv")
    print("colonnes :", idx.columns, "| lignes :", idx.height)
    print("classe_generation :", idx["classe_generation"].value_counts(sort=True).to_dict(as_series=False))
    print("format_version :", idx["format_version"].unique().to_list(), "| statut_mco :", idx["statut_mco"].value_counts(sort=True).to_dict(as_series=False))
    print("exemple :", idx.head(1).to_dicts())
    print("codes de l'index absents de codes.csv (forme pointée -> comparer après retrait du point) :",
          idx.with_columns(pl.col("code").str.replace(r"\.", "").alias("c")).join(codes.select(pl.col("code_atih").alias("c")), on="c", how="anti").height)

    titre("DP de PARHAF contre l'index")
    dp = pl.read_csv(RACINE / "donnees" / "prepare" / "parhaf" / "codes_dp_a_verifier.csv", separator=";")
    j = dp.join(codes.select("code_atih", pl.col("libelle").alias("libelle_officiel"), "codable_mco", "statut_mco"), left_on="code", right_on="code_atih", how="left")
    print("codes DP distincts :", dp.height, "| dossiers :", dp["effectif"].sum())
    inconnus = j.filter(pl.col("codable_mco").is_null())
    print("DP inconnus de codes.csv :", inconnus.height, "codes,", inconnus["effectif"].sum(), "dossiers :", inconnus.select("code", "libelle", "effectif").head(15).to_dicts())
    non_cod = j.filter(pl.col("codable_mco") == False)  # noqa: E712
    print("DP connus mais non codables :", non_cod.height, "codes,", non_cod["effectif"].sum(), "dossiers :", non_cod.select("code", "statut_mco", "effectif").head(15).to_dicts())
    ok = j.filter(pl.col("codable_mco") == True)  # noqa: E712
    print("DP codables :", ok.height, "codes,", ok["effectif"].sum(), "dossiers")
    norm = lambda s: s.str.to_lowercase().str.replace_all(r"\s+", " ").str.strip_chars()
    diff = ok.filter(norm(pl.col("libelle")) != norm(pl.col("libelle_officiel")))
    print("DP codables dont le libellé PARHAF diffère du libellé officiel (à la casse et aux espaces près) :", diff.height, "codes,", diff["effectif"].sum(), "dossiers")
    for r in diff.head(8).to_dicts(): print(f"   {r['code']:8s} PARHAF : {r['libelle'][:70]!r}  |  officiel : {r['libelle_officiel'][:70]!r}")


if __name__ == "__main__":
    main()
