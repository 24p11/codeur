"""Étape 2 du lot B2 : confrontation des codes du générateur à l'index recode-icd, sur les 100 000 lignes.

Pour le DP, chaque DAS, le code Z de case_management_type, puis les clés du JSON formulations.diagnostics (après
rattachement aux codes du scénario) : codable ; affinable ; père interdit ; supprimé ; inconnu du kit (formes fréquentes).
Lecture seule. Écrit donnees/prepare/synthetiques/codes_confrontation.md (sans identifiant).

Usage : uv run python -I scripts/chargement/synthetiques_codes.py
"""
import sys
from collections import Counter
from pathlib import Path

import polars as pl

sys.path.insert(0, str(Path(__file__).resolve().parent))
from synthetiques_commun import PREPARE, SOURCE, classer_code, code_de_cle, lire_index, lire_report, normaliser_code, rattacher


NON_CODABLES = ("pere_interdit", "supprime", "inconnu", "non_codable_autre")


def main() -> None:
    fiches, desc = lire_index()
    df = pl.read_parquet(SOURCE, columns=["report", "icd_primary_code", "icd_secondary_code", "case_management_type", "id_scenario"])
    classes = {"DP": Counter(), "DAS": Counter(), "Z": Counter()}
    formes = {"DP": Counter(), "DAS": Counter(), "Z": Counter()}
    lignes_dp_non_codable = 0
    lignes_das_non_codable = 0
    lignes_z_non_codable = 0
    json_ok = 0
    cles_total = 0
    cles_rattachees = Counter()   # 'egal' | 'extension' | 'prefixe' | 'aucun'
    cles_non_rattachees = Counter()  # classe des codes non rattachés (codes ajoutés par le générateur)
    formes_non_rattachees = Counter()
    affinables = {"DP": Counter(), "DAS": Counter(), "Z": Counter()}
    scenarios, scenarios_das_nc = set(), set()
    cles_sans_code = Counter()
    motifs = Counter(); eligibles = 0; scenarios_eligibles = set()
    for rep, dp, das, z, sc in zip(df["report"], df["icd_primary_code"], df["icd_secondary_code"], df["case_management_type"], df["id_scenario"]):
        scenarios.add(sc)
        das_l = das.to_list() if das is not None else []
        cdp = normaliser_code(dp)
        c = classer_code(cdp, fiches, desc); classes["DP"][c] += 1
        if c == "affinable": affinables["DP"][cdp] += 1
        if c in ("pere_interdit", "supprime", "inconnu", "non_codable_autre"):
            lignes_dp_non_codable += 1; formes["DP"][cdp] += 1
        das_nc = False
        for d in das_l:
            cd = normaliser_code(d); c = classer_code(cd, fiches, desc); classes["DAS"][c] += 1
            if c == "affinable": affinables["DAS"][cd] += 1
            if c in ("pere_interdit", "supprime", "inconnu", "non_codable_autre"):
                das_nc = True; formes["DAS"][cd] += 1
        if das_nc: lignes_das_non_codable += 1; scenarios_das_nc.add(sc)
        if z and z != "DP":
            cz = normaliser_code(z); c = classer_code(cz, fiches, desc); classes["Z"][c] += 1
            if c == "affinable": affinables["Z"][cz] += 1
            if c in ("pere_interdit", "supprime", "inconnu", "non_codable_autre"):
                lignes_z_non_codable += 1; formes["Z"][cz] += 1
        else:
            classes["Z"]["DP (pas de code Z)"] += 1
        raisons = set()
        if das_nc or classes["DP"] and classer_code(cdp, fiches, desc) in NON_CODABLES or (z and z != "DP" and classer_code(normaliser_code(z), fiches, desc) in NON_CODABLES):
            raisons.add("code du scénario non codable ou inconnu")
        obj, _ = lire_report(rep)
        diags = (obj or {}).get("formulations", {}).get("diagnostics") if obj else None
        if not isinstance(diags, dict):
            raisons.add("JSON non réparable"); motifs.update(raisons); motifs["lignes écartées"] += 1
            continue
        json_ok += 1
        scen = [cdp] + [normaliser_code(d) for d in das_l] + ([normaliser_code(z)] if z and z != "DP" else [])
        for cle in diags:
            cj = code_de_cle(cle)
            if not cj:
                cles_rattachees["sans code"] += 1; cles_sans_code[cle[-45:]] += 1; raisons.add("clé du JSON sans code reconnu"); continue
            cles_total += 1
            r = rattacher(cj, scen)
            if r is None:
                cles_rattachees["aucun"] += 1; raisons.add("code ajouté par le générateur (clé non rattachée)")
                cc = classer_code(cj, fiches, desc); cles_non_rattachees[cc] += 1
                formes_non_rattachees[cj] += 1
            elif r == cj: cles_rattachees["egal"] += 1
            elif normaliser_code(r).split("+")[0] == cj.split("+")[0]: cles_rattachees["extension"] += 1
            else: cles_rattachees["prefixe"] += 1
        if raisons:
            motifs.update(raisons); motifs["lignes écartées"] += 1
        else:
            eligibles += 1; scenarios_eligibles.add(sc)

    PREPARE.mkdir(parents=True, exist_ok=True)
    L = ["# Confrontation des codes du générateur à l'index recode-icd (65701d6_atih-2025)", "",
         f"Source : 100 000 lignes ; JSON analysable (réparations simples comprises) : {json_ok}.", "",
         "## Codes du scénario (colonnes)", "",
         "| | codable | affinable (souche avec descendants) | père interdit | supprimé | autre non codable | inconnu du kit | total |",
         "|---|---|---|---|---|---|---|---|"]
    for k in ("DP", "DAS", "Z"):
        c = classes[k]; tot = sum(v for kk, v in c.items() if kk != "DP (pas de code Z)")
        L.append(f"| {k} | {c['codable']} | {c['affinable']} | {c['pere_interdit']} | {c['supprime']} | {c['non_codable_autre']} | {c['inconnu']} | {tot} |")
    L += ["", f"- Lignes dont le DP n'est pas codable : **{lignes_dp_non_codable}** ; lignes avec au moins un DAS non codable : **{lignes_das_non_codable}** ; lignes dont le code Z n'est pas codable : **{lignes_z_non_codable}** ; lignes sans code Z (« DP ») : {classes['Z']['DP (pas de code Z)']}.",
          f"- Scénarios distincts : {len(scenarios)} ; scénarios touchés par un DAS non codable ou inconnu : {len(scenarios_das_nc)}.",
          "- « Affinable » : code marqué codable par le kit mais qui a des descendants codables plus précis (`descendants_codables`) ; ce n'est pas une anomalie, c'est une information pour la revue.", ""]
    for k in ("DP", "DAS", "Z"):
        L.append(f"### Formes non codables ou inconnues les plus fréquentes — {k}")
        L.append("")
        for code, n in formes[k].most_common(15):
            L.append(f"- `{code}` : {n} ({classer_code(code, fiches, desc)}{', ' + fiches[code]['libelle'][:60] if code in fiches else ''})")
        L.append("")
    for k in ("DP", "DAS", "Z"):
        L.append(f"### Formes affinables les plus fréquentes — {k} ({sum(affinables[k].values())} occurrences, {len(affinables[k])} formes)")
        L.append("")
        for code, n in affinables[k].most_common(10):
            L.append(f"- `{code}` : {n} — {fiches[code]['libelle'][:60]} ; descendants : {', '.join(desc[code][:5])}{'…' if len(desc[code]) > 5 else ''}")
        L.append("")
    L += ["## Clés du JSON `formulations.diagnostics` (après rattachement, SCHEMA.md §3.8)", "",
          f"- clés avec code : {cles_total} ; sans code : {cles_rattachees['sans code']}",
          f"- rattachées au scénario : égalité {cles_rattachees['egal']}, extension ignorée {cles_rattachees['extension']}, préfixe {cles_rattachees['prefixe']} ; **non rattachées (codes ajoutés par le générateur) : {cles_rattachees['aucun']}**",
          f"- classes des codes non rattachés : {dict(cles_non_rattachees)}", "",
          "### Formes non rattachées les plus fréquentes", ""]
    for code, n in formes_non_rattachees.most_common(15):
        L.append(f"- `{code}` : {n} ({classer_code(code, fiches, desc)}{', ' + fiches[code]['libelle'][:60] if code in fiches else ''})")
    L += ["", "### Clés sans code reconnu (fin de la clé)", ""]
    for fin, n in cles_sans_code.most_common(12):
        L.append(f"- {n} × `…{fin}`")
    L += ["", "## Si l'on écarte du tirage toute ligne présentant l'un de ces motifs", "",
          f"- Lignes éligibles : **{eligibles}** sur 100 000 ({len(scenarios_eligibles)} scénarios distincts).",
          f"- Motifs d'exclusion (une ligne peut en cumuler) : " + " ; ".join(f"{k} : {v}" for k, v in motifs.most_common())]
    texte = "\n".join(L) + "\n"
    (PREPARE / "codes_confrontation.md").write_text(texte, encoding="utf-8")
    print(texte)


if __name__ == "__main__":
    main()
