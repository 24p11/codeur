"""Brief 8, étape 4 : rapport chiffré des incohérences des scénarios des CRH synthétiques (les 100 000 lignes de la source),
au regard du guide des situations cliniques version 1, pour le projet de génération.

Quatre défauts : (1) un code Z (chapitre XXI) en DP ; (2) une règle de référence incompatible avec le DP (fonction
regles_compatibles) ; (3) un code Z de prise en charge hors de la liste de sa règle (ou « DP » quand la règle impose un code Z) ;
(4) T1 avec « DP ». Les lignes de règle « other » ou vide ne sont pas confrontables.
Écrit docs/exploration/defauts_scenarios_synthetiques.md (chiffres seulement, aucun identifiant) et
donnees/prepare/situations/defauts_scenarios.csv (détail par ligne, hors git).
"""
import csv
import sys
from collections import Counter
from pathlib import Path

import polars as pl
import psycopg

RACINE = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(RACINE / "scripts" / "tests")); sys.path.insert(0, str(RACINE / "scripts" / "chargement"))
from connexion import charger_env, url_postgres  # noqa: E402
from synthetiques_commun import SOURCE, normaliser_code  # noqa: E402

DOC = RACINE / "docs" / "exploration" / "defauts_scenarios_synthetiques.md"
DETAIL = RACINE / "donnees" / "prepare" / "situations" / "defauts_scenarios.csv"


def main() -> None:
    df = pl.read_parquet(SOURCE, columns=["generation_id", "id_scenario", "coding_rule", "case_management_type", "icd_primary_code"])
    dps = sorted({normaliser_code(c) for c in df["icd_primary_code"].to_list()})
    with psycopg.connect(url_postgres(charger_env())) as cx, cx.cursor() as cur:
        cur.execute("select code, details->'mode_prise_en_charge' from public.regles_situations"); modes = {c: m for c, m in cur.fetchall()}
        cur.execute("select dp, coalesce((select array_agg(r.regle) from public.regles_compatibles(dp) r), '{}') from unnest(%s::text[]) dp", (dps,))
        compat = dict(cur.fetchall())
    regles = set(modes)
    n = Counter(); par_regle = Counter(); z_dp = Counter(); hors = Counter(); detail = []
    for gid, sc, regle, mode, dp in df.iter_rows():
        dp = normaliser_code(dp); mode_n = "DP" if (not mode or mode == "DP") else normaliser_code(mode); regle = (regle or "").strip()
        defauts = []
        if dp.startswith("Z"):
            # Z80 à Z99 (antécédents, états) peuvent être une pathologie principale (règle D4) : comptés à part, sans défaut
            if "Z80" <= dp[:3] <= "Z99": n["Z80-Z99 en DP (admis, règle D4)"] += 1
            else: defauts.append("code Z en DP"); z_dp[dp[:3]] += 1
        confrontable = regle and regle != "other" and regle in regles
        if regle and regle != "other" and regle not in regles: defauts.append("règle inconnue du guide")
        if confrontable:
            if regle not in compat.get(dp, []): defauts.append("règle incompatible avec le DP"); par_regle[regle] += 1
            m = modes[regle]; codes_z = {c["code"] for c in m["codes"]}
            if mode_n == "DP" and not m["dp"]: defauts.append("« DP » alors que la règle impose un code Z"); hors[(regle, "DP")] += 1
            elif mode_n != "DP" and mode_n not in codes_z: defauts.append("code Z hors de la liste de la règle"); hors[(regle, mode_n)] += 1
            if regle == "T1" and mode_n == "DP": defauts.append("T1 avec « DP »")
        n["lignes"] += 1; n["confrontables"] += bool(confrontable)
        for d in defauts: n[d] += 1
        if defauts: n["lignes avec au moins un défaut"] += 1; detail.append([gid, sc, dp, regle, mode_n, " ; ".join(defauts)])
    DETAIL.parent.mkdir(parents=True, exist_ok=True)
    with open(DETAIL, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f); w.writerow(["generation_id", "id_scenario", "dp", "regle", "mode", "defauts"]); w.writerows(detail)
    L = ["# Incohérences des scénarios des CRH synthétiques au regard du guide des situations cliniques", "",
         "*Source : les 100 000 lignes du fichier `run08_scenarios_reports_merged_20261007_160916.parquet` (colonnes `icd_primary_code`, `coding_rule`, `case_management_type`), confrontées le 24 octobre 2026 au guide des situations cliniques version 1 (`docs/referentiels/situations_cliniques/`, chapitres I à XVII, XIX et XXII) et à la fonction `regles_compatibles`. Rapport chiffré destiné au projet de génération ; le détail par ligne (identifiants) reste hors du dépôt, dans `donnees/prepare/situations/defauts_scenarios.csv`. Les dossiers concernés sont à traiter à part dans les analyses de la règle de hiérarchisation. Script : `scripts/referentiels/defauts_scenarios.py`.*", "",
         "## Chiffres", "", "| Mesure | Lignes |", "|---|---|",
         f"| Lignes de la source | {n['lignes']} |",
         f"| Lignes confrontables (règle connue du guide, ni `other` ni vide) | {n['confrontables']} |",
         f"| Règle inconnue du guide | {n['règle inconnue du guide']} |",
         f"| **1. Code Z (chapitre XXI) en DP**, hors Z80-Z99 | {n['code Z en DP']} |",
         f"| Z80-Z99 en DP (admis : antécédents et états, règle D4), pour mémoire | {n['Z80-Z99 en DP (admis, règle D4)']} |",
         f"| **2. Règle incompatible avec le DP** (lignes confrontables) | {n['règle incompatible avec le DP']} |",
         f"| **3. Code Z de prise en charge hors de la liste de sa règle** | {n['code Z hors de la liste de la règle']} |",
         f"| **3 bis. « DP » alors que la règle impose un code Z** | {n['« DP » alors que la règle impose un code Z']} |",
         f"| **4. T1 avec « DP »** (compris dans 3 bis) | {n['T1 avec « DP »']} |",
         f"| Lignes avec au moins un défaut | {n['lignes avec au moins un défaut']} |", "",
         "## Détail", "", "### 1. Codes Z en DP, par catégorie", "", "| Catégorie | Lignes |", "|---|---|"] + [f"| {k} | {v} |" for k, v in z_dp.most_common()] + [
         "", "### 2. Règle incompatible avec le DP, par règle", "", "| Règle | Lignes |", "|---|---|"] + [f"| {k} | {v} |" for k, v in par_regle.most_common()] + [
         "", "### 3. Mode de prise en charge hors de la liste de la règle (ou « DP » imposé code Z), par règle et mode", "", "| Règle | Mode | Lignes |", "|---|---|---|"] + [f"| {r} | {m} | {v} |" for (r, m), v in hors.most_common(30)] + [
         "", "## Lecture", "",
         "- Le défaut 1 vient du générateur qui place le code de prise en charge (Z45, Z04, Z47, Z49, Z51…) en DP au lieu de la pathologie ; `codeur` attend la pathologie en pathologie principale et le code Z en mode de prise en charge. Les codes Z80 à Z99 (antécédents, états) sont admis en DP par la règle D4 et ne sont pas comptés comme défaut.",
         "- Le défaut 2 signale une règle qui ne peut pas s'appliquer à la pathologie du scénario (par exemple D9, bilan d'extension d'un cancer, avec un DP hors du chapitre II).",
         "- Les défauts 3 et 4 signalent un mode de prise en charge étranger à la règle (un code Z avec T3, qui n'en prévoit aucun ; « DP » avec T1, qui impose un code Z).",
         "- Les lignes de règle `other` ou vide ne sont pas confrontables : la règle n'est pas renseignée dans le scénario."]
    DOC.write_text("\n".join(L) + "\n", encoding="utf-8")
    print("\n".join(l for l in L if l.startswith("| ") and not l.startswith("| Mesure") and not l.startswith("|---")))
    print(f"\nrapport : {DOC.relative_to(RACINE)} ; détail ({len(detail)} lignes) : {DETAIL.relative_to(RACINE)}")


if __name__ == "__main__":
    main()
