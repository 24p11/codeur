"""Teste des réparations simples sur les champs `report` qui ne sont pas un JSON valide.

Usage : uv run python -I scripts/exploration/12_reparation_json_synthetiques.py
Aucun fichier n'est modifié : le test est fait en mémoire.
"""
import json
import re
from collections import Counter
from pathlib import Path

import polars as pl

RACINE = Path(__file__).resolve().parents[2]
FICHIER = RACINE / "donnees" / "synthetiques" / "run08_scenarios_reports_merged_20261007_160916.parquet"

STRATEGIES = {
    "strict=False (sauts de ligne bruts dans les chaînes)": lambda s: s,
    "ajouter une accolade fermante": lambda s: s.rstrip() + "}",
    "retirer la dernière accolade": lambda s: s.rstrip()[:-1],
    "retirer la clôture ``` de fin": lambda s: re.sub(r"\s*```\s*$", "", s.rstrip()),
}


def valide(s: str) -> bool:
    try:
        json.loads(s, strict=False)
        return True
    except json.JSONDecodeError:
        return False


def main() -> None:
    df = pl.read_parquet(FICHIER, columns=["report", "template_name"])
    strict_ok = 0
    res = Counter()
    par_gabarit = Counter()
    fins = Counter()
    for rep, gab in zip(df["report"], df["template_name"]):
        try:
            json.loads(rep)
            strict_ok += 1
        except json.JSONDecodeError:
            pass
        for nom, f in STRATEGIES.items():
            if valide(f(rep)):
                res[nom] += 1
                break
        else:
            res["non réparé"] += 1
            par_gabarit[gab] += 1
            fins[rep.rstrip()[-3:]] += 1
    print(f"lignes : {df.height} ; JSON strict valide : {strict_ok}")
    for k, v in res.items():
        print(f"  {v:6d}  {k}")
    print("  non réparés par gabarit :", par_gabarit.most_common())
    print("  trois derniers caractères des non réparés :", fins.most_common(5))


if __name__ == "__main__":
    main()
