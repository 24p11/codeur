"""Codes de `formulations.diagnostics` absents du scénario (CRH synthétiques).

Pour chaque ligne analysable, compare les codes des clés de `formulations.diagnostics` aux colonnes
icd_primary_code, icd_secondary_code et case_management_type. Classe chaque code « en plus » :
  (a) autre forme d'un code du scénario (extension « +0 », suffixe « ni », troncature ou précision),
  (b) code tabac / alcool / obésité (F17, F10, E66, Z720, Z721),
  (c) autre code.
Puis affiche 5 exemples variés : codes du scénario, clés du JSON avec les codes absents signalés,
et pour chaque code absent ses formulations et la phrase du texte où elles apparaissent.

Usage : uv run python -I scripts/exploration/14_codes_hors_scenario_synthetiques.py
Aucun fichier n'est modifié.
"""
import json
import re
from collections import Counter
from pathlib import Path

import polars as pl

RACINE = Path(__file__).resolve().parents[2]
FICHIER = RACINE / "donnees" / "synthetiques" / "run08_scenarios_reports_merged_20261007_160916.parquet"
CODE_FIN = re.compile(r"\(([A-Z]\d{2}[A-Za-z0-9.+]{0,5})\)\s*$")
TAO = re.compile(r"^(F17|F10|E66|Z720|Z721)")


def norm(c: str) -> str:
    return c.replace(".", "").upper()


def racine(c: str) -> str:
    """Code sans extension PMSI : « K635+0 » -> « K635 », « E11NI » -> « E11 »."""
    c = norm(c).split("+")[0]
    return re.sub(r"(NI|I)$", "", c) if re.match(r"^E1[0-4]", c) else c


def classer(code: str, scen: set[str]) -> str:
    """Retourne « a-extension », « a-diabète », « a-moins précis », « a-plus précis », « b » ou « c »."""
    n = norm(code)
    r = racine(code)
    for s in scen:
        ns, rs = norm(s), racine(s)
        if r == rs:
            if "+" in ns:
                return "a-extension"
            if re.match(r"^E1[0-4]", ns) and re.search(r"(NI|I)$", ns):
                return "a-diabète"
            return "a-extension"
        if rs.startswith(r):
            return "a-moins précis"
        if r.startswith(rs):
            return "a-plus précis"
    if TAO.match(n):
        return "b"
    return "c"


def phrase_contenant(cr: str, formulation: str) -> str:
    """Première phrase (ou ligne) du texte qui contient la formulation, à la casse et aux espaces près."""
    f = re.sub(r"\s+", " ", formulation).strip().lower()
    for bloc in re.split(r"(?<=[.!?])\s+|\n+", cr):
        if f in re.sub(r"\s+", " ", bloc).lower():
            return bloc.strip()
    return "(introuvable dans le texte)"


def main() -> None:
    df = pl.read_parquet(FICHIER, columns=["report", "icd_primary_code", "icd_secondary_code",
                                           "case_management_type", "template_name", "source_row_id"])
    lignes = []
    bilan = Counter()
    codes_c = Counter()
    codes_b = Counter()
    paires = Counter()
    for rep, dp, das, z, gab, rid in zip(df["report"], df["icd_primary_code"], df["icd_secondary_code"],
                                         df["case_management_type"], df["template_name"], df["source_row_id"]):
        try:
            obj = json.loads(rep, strict=False)
        except json.JSONDecodeError:
            continue
        diags = (obj.get("formulations") or {}).get("diagnostics")
        if not isinstance(diags, dict):
            continue
        das_l = das.to_list() if das is not None else []
        scen = {norm(dp)} | {norm(c) for c in das_l}
        if z and z != "DP":
            scen.add(norm(z))
        extras = {}
        for cle, phrases in diags.items():
            m = CODE_FIN.search(cle)
            if m and norm(m.group(1)) not in scen:
                extras[cle] = (m.group(1), classer(m.group(1), scen), phrases if isinstance(phrases, list) else [])
        if extras:
            for _, (code, cat, _) in extras.items():
                bilan[cat] += 1
                (codes_c if cat == "c" else codes_b if cat == "b" else Counter())[norm(code)] += 1
                if cat.startswith("a-moins") or cat.startswith("a-plus"):
                    paires[(cat, norm(code), ",".join(sorted(s for s in scen if racine(s).startswith(racine(code)) or racine(code).startswith(racine(s)))))] += 1
            lignes.append((rid, gab, dp, das_l, z, diags, extras, obj.get("CR", "")))

    print(f"lignes analysables : {sum(1 for _ in lignes) and len(lignes)} lignes avec au moins un code hors scénario")
    total = sum(bilan.values())
    print(f"codes hors scénario : {total}")
    a_total = sum(v for k, v in bilan.items() if k.startswith("a"))
    print(f"  (a) autre forme d'un code du scénario : {a_total}")
    for k in ("a-extension", "a-diabète", "a-moins précis", "a-plus précis"):
        print(f"      {k:16s} {bilan[k]}")
    print("      paires JSON -> scénario pour « moins précis » / « plus précis » :", paires.most_common(10))
    print(f"  (b) tabac / alcool / obésité           : {bilan['b']}   détail : {codes_b.most_common(8)}")
    print(f"  (c) autre code                          : {bilan['c']}   les plus fréquents : {codes_c.most_common(12)}")
    cats_par_ligne = Counter("|".join(sorted({cat[0] for _, (_, cat, _) in ex.items()})) for *_, ex, _ in lignes)
    print(f"  combinaisons de catégories par ligne : {dict(cats_par_ligne)}")
    print(f"  lignes avec 2 codes hors scénario ou plus : {sum(1 for *_, ex, _ in lignes if len(ex) >= 2)}")

    # Cinq exemples variés : (a) seul, (b) seul, (c) seul, plusieurs codes de catégories mixtes, gabarit chirurgical
    def premier(cond):
        for l in lignes:
            if cond(l):
                return l
    def cats(l):
        return {c for _, (_, c, _) in l[6].items()}
    choix = [
        ("(a) extension PMSI « +N » absente du JSON", premier(lambda l: cats(l) == {"a-extension"} and any("+" in norm(x) for x in l[3] + [l[2]]))),
        ("(a) suffixe diabète « ni » / « i » absent du JSON", premier(lambda l: cats(l) == {"a-diabète"})),
        ("(a) code du JSON moins précis que le scénario", premier(lambda l: cats(l) == {"a-moins précis"})),
        ("(a) code du JSON plus précis que le scénario, ou ligne à plusieurs codes en plus", premier(lambda l: cats(l) == {"a-plus précis"}) or premier(lambda l: len(l[6]) >= 2)),
        ("(c) autre code", premier(lambda l: "c" in cats(l) and l[1] == "medical_inpatient.txt")),
    ]
    for titre, l in choix:
        if l is None:
            print(f"\n(aucun exemple pour : {titre})")
            continue
        rid, gab, dp, das_l, z, diags, extras, cr = l
        print("\n" + "=" * 100)
        print(f"EXEMPLE — {titre}\nsource_row_id {rid} | gabarit {gab}")
        print(f"  scénario : DP = {dp} ; DAS = {das_l} ; case_management_type = {z}")
        print("  clés de formulations.diagnostics :")
        for cle in diags:
            marque = f"   <-- ABSENT DU SCÉNARIO, catégorie ({extras[cle][1]})" if cle in extras else ""
            print(f"    - {cle}{marque}")
        for cle, (code, cat, phrases) in extras.items():
            print(f"\n  code absent {code} ({cat}) — « {cle} »")
            if not phrases:
                print("    (aucune formulation)")
            for ph in phrases:
                print(f"    formulation : {ph!r}")
                print(f"    phrase      : {phrase_contenant(cr, ph)!r}")


if __name__ == "__main__":
    main()
