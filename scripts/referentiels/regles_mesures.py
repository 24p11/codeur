"""Brief 8, étape 4 : mesures sur les 500 CRH synthétiques chargés (lot synthetiques-run08-e500), clé secrète, lecture seule.

1. Règles compatibles avec le DP de référence (fonction regles_compatibles) : distribution du nombre ; la règle de référence
   (coding_rule du scénario, telle que chargée dans codages.scenario.regle_hierarchisation) est-elle parmi les compatibles ?
2. Confrontation des scénarios au guide : la règle existe-t-elle dans regles_situations ? le code Z du dossier appartient-il à la
   liste de sa règle ? (règle null : coding_rule « other » ou vide, non confrontable.)
3. Taille du second appel : préambule + extraits propres des règles compatibles + chaque passage commun concerné une fois,
   en caractères et tokens approximatifs (caractères / 4) : médiane et maximum, sans le texte du dossier ni le codage.
Écrit donnees/prepare/situations/mesures_regles.md (hors git ; les exemples y portent l'identifiant du dossier) et affiche le bilan.
"""
import csv
import json
import statistics
import sys
from collections import Counter
from pathlib import Path

import psycopg

RACINE = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(RACINE / "scripts" / "tests"))
from connexion import charger_env, url_postgres  # noqa: E402

EXTRAITS = RACINE / "docs" / "referentiels" / "situations_cliniques" / "extraits_guide_methodologique_2026.csv"
SORTIE = RACINE / "donnees" / "prepare" / "situations" / "mesures_regles.md"
LOT = "synthetiques-run08-e500"


def main() -> None:
    extraits = list(csv.DictReader(open(EXTRAITS, encoding="utf-8")))
    preambule = sum(len(e["extrait"]) for e in extraits if e["type"] == "preambule")
    cx = psycopg.connect(url_postgres(charger_env())); cur = cx.cursor()
    if True:
        cur.execute("""select d.id_source, c.codage->'ensembles'->0->>'code', c.codage->>'regle_hierarchisation', c.codage->>'mode_prise_en_charge'
                       from public.documents d join public.codages c on c.document = d.id and c.etape = 'scenario'
                       where d.lot = %s order by d.id_source""", (LOT,))
        dossiers = cur.fetchall()
        cur.execute("select code, regle_officielle, details from public.regles_situations"); regles = {r[0]: (r[1], r[2]) for r in cur.fetchall()}
        cache = {}
        def compat(code):
            if code not in cache:
                cur.execute("select regle from public.regles_compatibles(%s)", (code,)); cache[code] = [r[0] for r in cur.fetchall()]
            return cache[code]
    nb = Counter(); ref_dans = Counter(); ecarts = []; absentes = Counter(); z_hors = []; z_ok = Counter(); tailles = []
    for ids, dp, regle, mode in dossiers:
        comp = compat(dp); nb[len(comp)] += 1
        # taille du second appel
        comp_off = {regles[c][0] for c in comp}
        propres = [e for e in extraits if e["type"] == "regle" and e["regle_officielle"] in comp_off and (not e["lignes"] or set(e["lignes"].split()) & set(comp))]
        communs = [e for e in extraits if e["type"] == "commun" and ((set(e["lignes"].split()) & set(comp)) if e["lignes"] else (set(e["regle_officielle"].split()) & comp_off))]
        listes_z = sum(len(json.dumps(regles[c][1]["mode_prise_en_charge"]["codes"], ensure_ascii=False)) for c in comp)
        tailles.append(preambule + sum(len(e["extrait"]) for e in propres) + sum(len(e["extrait"]) for e in communs) + listes_z)
        if regle is None: ref_dans["règle null (other ou vide)"] += 1; continue
        if regle not in regles: absentes[regle] += 1; ref_dans["règle inconnue du guide"] += 1; continue
        if regle in comp: ref_dans["oui"] += 1
        else: ref_dans["non"] += 1; ecarts.append((ids, dp, regle, comp))
        d = regles[regle][1]["mode_prise_en_charge"]
        codes_z = {c["code"] for c in d["codes"]}
        if mode == "DP": (z_ok if d["dp"] else z_hors).__setitem__("DP avec " + regle, z_ok.get("DP avec " + regle, 0) + 1) if d["dp"] else z_hors.append((ids, regle, "DP", "la règle impose un code Z"))
        elif mode in codes_z: z_ok["code Z dans la liste"] += 1
        else: z_hors.append((ids, regle, mode, "hors de la liste de la règle"))
    L = [f"# Mesures sur les {len(dossiers)} CRH synthétiques (lot {LOT})", "",
         "## 1. Règles compatibles avec le DP de référence", "",
         "| nombre de règles compatibles | dossiers |", "|---|---|"] + [f"| {k} | {v} |" for k, v in sorted(nb.items())] + [
         "", f"- médiane : {statistics.median([k for k, v in nb.items() for _ in range(v)])} ; minimum {min(nb)} ; maximum {max(nb)}",
         f"- la règle de référence est parmi les compatibles : {dict(ref_dans)}",
         f"- règles de référence inconnues du guide : {dict(absentes) or 'aucune'}", "",
         "### Écarts (règle de référence hors des compatibles)", "", "| dossier | DP | règle de référence | compatibles |", "|---|---|---|---|"] + [
         f"| {i} | {dp} | {r} | {', '.join(c)} |" for i, dp, r, c in ecarts] + [
         "", "## 2. Confrontation des scénarios au guide (mode de prise en charge)", "", f"- conformes : {dict(z_ok)}", f"- écarts : {len(z_hors)}", "",
         "| dossier | règle | mode | écart |", "|---|---|---|---|"] + [f"| {i} | {r} | {m} | {e} |" for i, r, m, e in z_hors] + [
         "", "## 3. Taille du second appel (préambule + extraits des règles compatibles + passages communs + listes de codes Z, hors texte du dossier)", "",
         f"- caractères : médiane {int(statistics.median(tailles))}, maximum {max(tailles)}, minimum {min(tailles)}",
         f"- tokens approximatifs (/4) : médiane {int(statistics.median(tailles)) // 4}, maximum {max(tailles) // 4}"]
    cx.close()
    SORTIE.parent.mkdir(parents=True, exist_ok=True); SORTIE.write_text("\n".join(L) + "\n", encoding="utf-8")
    # bilan sans identifiant
    print("\n".join(l for l in L if not l.startswith("| ") or l.startswith("| nombre") or l.startswith("| ---") or l[2:4].strip().isdigit() and "|" in l[:8] and l.count("|") == 3))
    print(f"\nécarts de règle : {len(ecarts)} ; écarts de mode : {len(z_hors)} (détail avec identifiants dans {SORTIE.relative_to(RACINE)})")
    print("exemples d'écarts de règle (DP, référence → compatibles) :", [(dp, r, c[:6]) for _, dp, r, c in ecarts[:5]])
    print("exemples d'écarts de mode (règle, mode, écart) :", [(r, m, e) for _, r, m, e in z_hors[:5]])


if __name__ == "__main__":
    main()
