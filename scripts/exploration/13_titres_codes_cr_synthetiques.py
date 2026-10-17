"""Titre réel du document (ligne « Compte rendu … ») selon le gabarit, et codes CIM-10 présents dans le texte CR.

Usage : uv run python -I scripts/exploration/13_titres_codes_cr_synthetiques.py
"""
import json
import re
from collections import Counter, defaultdict
from pathlib import Path

import polars as pl

RACINE = Path(__file__).resolve().parents[2]
FICHIER = RACINE / "donnees" / "synthetiques" / "run08_scenarios_reports_merged_20261007_160916.parquet"
TITRE = re.compile(r"compte[- ]rendu[^\n]*", re.I)
CODE_PAREN = re.compile(r"[\(\[]([A-Z]\d{2}\.?\d{0,3}[A-Za-z+0-9]{0,3})[\)\]]")
RUBRIQUES = ["motif", "antécédent", "histoire de la maladie", "examen clinique", "évolution", "conclusion", "traitement de sortie"]


def main() -> None:
    df = pl.read_parquet(FICHIER, columns=["report", "template_name", "icd_primary_code"])
    titres = defaultdict(Counter)
    codes_cr = Counter()
    docs_codes = 0
    ex_codes = []
    rubriques = Counter()
    n = 0
    sections = Counter()
    for rep, gab, dp in zip(df["report"], df["template_name"], df["icd_primary_code"]):
        try:
            cr = json.loads(rep, strict=False)["CR"]
        except (json.JSONDecodeError, KeyError, TypeError):
            continue
        n += 1
        m = TITRE.search(cr)
        titres[gab][re.sub(r"\*", "", m.group(0)).strip()[:45] if m else "(aucun)"] += 1
        c = CODE_PAREN.findall(cr)
        if c:
            docs_codes += 1
            codes_cr.update(c)
            if len(ex_codes) < 4:
                i = CODE_PAREN.search(cr).start()
                ex_codes.append(repr(cr[max(0, i - 80):i + 40]))
        bas = cr.lower()
        for r in RUBRIQUES:
            if r in bas:
                rubriques[r] += 1
        for s in re.findall(r"^#{1,4} +(.+)$", cr, re.M):
            sections[s.strip()[:40]] += 1
    print(f"textes CR analysés : {n}")
    print("\n=== titre du document par gabarit ===")
    for gab, c in titres.items():
        print(f"  {gab}")
        for t, k in c.most_common(5):
            print(f"      {k:6d}  {t!r}")
    print(f"\n=== codes CIM-10 entre parenthèses ou crochets dans le texte CR : {docs_codes} textes ===")
    print("  codes les plus fréquents :", codes_cr.most_common(10))
    for e in ex_codes:
        print("   ", e)
    print("\n=== rubriques (présence du mot) ===", dict(rubriques))
    print("\n=== titres de section markdown les plus fréquents ===")
    for s, k in sections.most_common(25):
        print(f"  {k:6d}  {s}")


if __name__ == "__main__":
    main()
