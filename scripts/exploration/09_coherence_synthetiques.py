"""Cohérence entre le JSON de `report`, les colonnes du scénario et le texte du CRH synthétique.

1. Analyse JSON tolérante (strict=False : accepte les sauts de ligne bruts dans les chaînes) ; échecs restants.
2. Codes présents dans `formulations.diagnostics` (extraits des clés « libellé (CODE) ») comparés aux colonnes
   icd_primary_code, icd_secondary_code, case_management_type.
3. Les formulations (éléments de preuve) se trouvent-elles dans le texte CR ? (exact, puis insensible à la casse
   et aux espaces, puis après normalisation des accents).
4. Particularités du texte CR : markdown, sauts de ligne, doublons, longueur en mots.

Usage : uv run python -I scripts/exploration/09_coherence_synthetiques.py
"""
import hashlib
import json
import re
import unicodedata
from collections import Counter
from pathlib import Path
from statistics import median

import polars as pl

RACINE = Path(__file__).resolve().parents[2]
FICHIER = RACINE / "donnees" / "synthetiques" / "run08_scenarios_reports_merged_20261007_160916.parquet"
CODE_FIN = re.compile(r"\(([A-Z]\d{2}[A-Za-z0-9.+]{0,5})\)\s*$")


def normalise(s: str) -> str:
    s = unicodedata.normalize("NFKD", s)
    s = "".join(c for c in s if not unicodedata.combining(c))
    return re.sub(r"\s+", " ", s).strip().lower()


def main() -> None:
    df = pl.read_parquet(FICHIER, columns=["report", "icd_primary_code", "icd_secondary_code",
                                           "case_management_type", "template_name", "source_row_id"])
    n = df.height
    ok = 0
    echecs = Counter()
    echecs_ex = []
    sans_formulations = 0
    diag_par_ligne = Counter()
    form_par_diag = Counter()
    # Couverture des codes
    codes_scen_absents = 0
    lignes_codes_manquants = 0
    codes_json_en_trop = 0
    lignes_codes_en_trop = 0
    forme_code = Counter()
    cle_sans_code = 0
    # Preuves
    total_form = 0
    exact = casse = normal = introuvable = 0
    ex_introuvables = []
    # Texte
    md_titres = md_gras = 0
    crlf = 0
    mots = []
    empreintes = Counter()
    for rep, dp, das, z, gab, rid in zip(df["report"], df["icd_primary_code"], df["icd_secondary_code"],
                                         df["case_management_type"], df["template_name"], df["source_row_id"]):
        try:
            obj = json.loads(rep, strict=False)
        except json.JSONDecodeError as e:
            echecs[re.sub(r"\d+", "N", str(e))[:70]] += 1
            if len(echecs_ex) < 3:
                echecs_ex.append((rid, gab, repr(rep[-200:])))
            continue
        ok += 1
        cr = obj.get("CR", "")
        if "\r" in cr:
            crlf += 1
        if re.search(r"^#{1,4} ", cr, re.M):
            md_titres += 1
        if "**" in cr:
            md_gras += 1
        mots.append(len(cr.split()))
        empreintes[hashlib.sha1(cr.encode()).hexdigest()] += 1
        form = obj.get("formulations")
        if not isinstance(form, dict) or not isinstance(form.get("diagnostics"), dict):
            sans_formulations += 1
            continue
        diags = form["diagnostics"]
        diag_par_ligne[len(diags)] += 1
        codes_json = set()
        for cle, phrases in diags.items():
            m = CODE_FIN.search(cle)
            if not m:
                cle_sans_code += 1
                continue
            c = m.group(1)
            forme_code["avec point" if "." in c else "sans point"] += 1
            codes_json.add(c.replace(".", "").upper())
            if not isinstance(phrases, list):
                continue
            form_par_diag[len(phrases)] += 1
            cr_norm = None
            for ph in phrases:
                if not isinstance(ph, str):
                    continue
                total_form += 1
                if ph in cr:
                    exact += 1
                elif re.sub(r"\s+", " ", ph).lower() in re.sub(r"\s+", " ", cr).lower():
                    casse += 1
                else:
                    if cr_norm is None:
                        cr_norm = normalise(cr)
                    if normalise(ph) in cr_norm:
                        normal += 1
                    else:
                        introuvable += 1
                        if len(ex_introuvables) < 6:
                            ex_introuvables.append((rid, cle[:60], ph[:100]))
        codes_scen = {dp.replace(".", "").upper()} | {c.replace(".", "").upper() for c in (das.to_list() if das is not None else [])}
        if z:
            codes_scen.add(z.replace(".", "").upper())
        manquants = codes_scen - codes_json
        en_trop = codes_json - codes_scen
        if manquants:
            lignes_codes_manquants += 1
            codes_scen_absents += len(manquants)
        if en_trop:
            lignes_codes_en_trop += 1
            codes_json_en_trop += len(en_trop)

    print(f"lignes : {n} ; JSON analysé (strict=False) : {ok} ; échecs restants : {sum(echecs.values())}")
    for e, c in echecs.most_common(6):
        print("   ", c, e)
    for x in echecs_ex:
        print("    ex :", x)
    print(f"\nobjets sans `formulations.diagnostics` exploitable : {sans_formulations}")
    print("nombre de diagnostics par ligne :", sorted(diag_par_ligne.items()))
    print("nombre de formulations par diagnostic :", sorted(form_par_diag.items())[:15])
    print("clés de diagnostic sans code entre parenthèses en fin :", cle_sans_code)
    print("forme des codes dans les clés :", dict(forme_code))
    print(f"\n=== couverture des codes du scénario (DP + DAS + code Z de case_management_type) ===")
    print(f"lignes où au moins un code du scénario manque dans le JSON : {lignes_codes_manquants} ({codes_scen_absents} codes)")
    print(f"lignes où le JSON contient des codes hors scénario : {lignes_codes_en_trop} ({codes_json_en_trop} codes)")
    print(f"\n=== formulations retrouvées dans le texte CR ({total_form} formulations) ===")
    print(f"  exactes : {exact} ; à la casse/espaces près : {casse} ; aux accents près : {normal} ; introuvables : {introuvable}")
    for x in ex_introuvables:
        print("   ", x)
    print(f"\n=== texte CR ===")
    print(f"  CR avec titres markdown (#) : {md_titres} ; avec gras (**) : {md_gras} ; avec \\r : {crlf}")
    print(f"  mots : min {min(mots)} médiane {median(mots):.0f} max {max(mots)}")
    print(f"  textes CR strictement identiques entre deux lignes : {sum(1 for v in empreintes.values() if v > 1)}")


if __name__ == "__main__":
    main()
