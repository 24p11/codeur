"""Analyse le JSON du champ `report` des CRH synthétiques sur toutes les lignes.

Mesure : lignes dont `report` est un JSON valide, clés de premier niveau et leur fréquence,
structure des clés de codage (niveaux 2 et 3), types et effectifs.

Usage : uv run python -I scripts/exploration/08_json_synthetiques.py
"""
import json
from collections import Counter, defaultdict
from pathlib import Path

import polars as pl

RACINE = Path(__file__).resolve().parents[2]
FICHIER = RACINE / "donnees" / "synthetiques" / "run08_scenarios_reports_merged_20261007_160916.parquet"


def type_de(v):
    if isinstance(v, dict):
        return "objet"
    if isinstance(v, list):
        return "liste" + ("(vide)" if not v else f"[{type_de(v[0])}]")
    return type(v).__name__


def main() -> None:
    df = pl.read_parquet(FICHIER, columns=["report", "template_name"])
    n = df.height
    ok = 0
    echecs = Counter()
    cles1 = Counter()
    types1 = defaultdict(Counter)
    cles2 = defaultdict(Counter)        # par clé de niveau 1 -> clés de niveau 2
    types2 = defaultdict(Counter)       # (clé1, clé2) -> types
    cles3 = defaultdict(Counter)        # (clé1, clé2) -> clés de niveau 3 (si objet) ou types d'éléments
    exemples_cle2 = {}
    par_gabarit = defaultdict(Counter)
    for rep, gab in zip(df["report"], df["template_name"]):
        try:
            obj = json.loads(rep)
        except json.JSONDecodeError as e:
            echecs[str(e)[:60]] += 1
            continue
        if not isinstance(obj, dict):
            echecs["pas un objet : " + type_de(obj)] += 1
            continue
        ok += 1
        cles1.update(obj.keys())
        par_gabarit[gab].update(obj.keys())
        for k, v in obj.items():
            types1[k][type_de(v)] += 1
            if isinstance(v, dict):
                for k2, v2 in v.items():
                    cles2[k][k2] += 1
                    types2[(k, k2)][type_de(v2)] += 1
                    if isinstance(v2, dict):
                        cles3[(k, k2)].update(v2.keys())
                    elif isinstance(v2, list) and v2 and isinstance(v2[0], dict):
                        for el in v2:
                            cles3[(k, k2)].update(el.keys())
                    exemples_cle2.setdefault((k, k2), repr(v2)[:160])
            elif isinstance(v, list) and v and isinstance(v[0], dict):
                for el in v:
                    cles2[k].update(el.keys())
                    for k2, v2 in el.items():
                        types2[(k, k2)][type_de(v2)] += 1
                        if isinstance(v2, dict):
                            cles3[(k, k2)].update(v2.keys())
                        exemples_cle2.setdefault((k, k2), repr(v2)[:160])

    print(f"lignes : {n} ; JSON valide et objet : {ok} ; échecs : {sum(echecs.values())}")
    for e, c in echecs.most_common(5):
        print("   ", c, e)
    print("\n=== clés de premier niveau (effectif sur", ok, "objets) ===")
    for k, c in cles1.most_common():
        print(f"  {k:40s} {c:7d}  types : {dict(types1[k])}")
    print("\n=== clés de premier niveau par gabarit ===")
    for gab, c in par_gabarit.items():
        print(f"  {gab:32s} n={sum(1 for _ in [0])} ", dict(c))
    print("\n=== clés de niveau 2 (sous chaque clé de niveau 1 qui est un objet ou une liste d'objets) ===")
    for k, c in cles2.items():
        print(f"\n  [{k}] : {len(c)} clés de niveau 2")
        for k2, c2 in c.most_common(60):
            t = dict(types2[(k, k2)])
            sous = cles3.get((k, k2))
            sous_txt = f" | clés niveau 3 : {dict(sous.most_common(12))}" if sous else ""
            print(f"    {k2:45s} {c2:7d}  {t}{sous_txt}")
            print(f"      ex : {exemples_cle2.get((k, k2), '')}")
        if len(c) > 60:
            print(f"    ... ({len(c) - 60} autres clés)")


if __name__ == "__main__":
    main()
