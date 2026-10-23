"""Charge le guide des situations cliniques (version 1) dans regles_situations (brief 8, étape 3), clé secrète.

Source : docs/referentiels/situations_cliniques/guide_situations_cliniques.csv, lu par situations_commun.py ; extraits officiels
et listes de codes pour les contrôles. Contrôles avant écriture (chargement refusé si l'un échoue) : chaque code cité existe
dans l'index (codable ou catégorie à descendants codables) ; chaque liste citée existe dans listes_codes (les listes d'actes
absentes sont tolérées pour la seule règle non évaluable) ; chaque mode donne au moins un code Z codable quand il n'est pas
« Aucun » ; familles connues ; codes de règle uniques ; chaque règle officielle a au moins un extrait ; chapitres connus.
Rechargeable sans doublon : insertion ou mise à jour sur `code` ; ne supprime rien.

Usage : uv run python -I scripts/chargement/situations_charger.py [--controler]
"""
import json
import sys
from collections import Counter
from pathlib import Path

from supabase import create_client

RACINE = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(RACINE / "scripts" / "tests")); sys.path.insert(0, str(RACINE / "scripts" / "chargement"))
from connexion import charger_env  # noqa: E402
from situations_commun import ROMAINS, lire_chapitres, lire_guide, lire_listes_base  # noqa: E402
from synthetiques_commun import lire_index  # noqa: E402


def main() -> None:
    controler = "--controler" in sys.argv
    fiches, desc = lire_index()
    listes = lire_listes_base()
    chapitres = {c["numero"] for c in lire_chapitres()}
    lignes, extraits = lire_guide(fiches, desc)
    erreurs = []
    codes_regles = [l["code"] for l in lignes]
    if len(set(codes_regles)) != len(codes_regles): erreurs.append("codes de règle en double : " + str([c for c, n in Counter(codes_regles).items() if n > 1]))
    for l in lignes:
        d = l["details"]; p = d["pathologie"]; m = d["mode_prise_en_charge"]; c = l["code"]
        if not l["type"]: erreurs.append(f"{c} : famille inconnue « {l['famille']} »")
        for ch in p["chapitres"]:
            if ch not in chapitres: erreurs.append(f"{c} : chapitre inconnu {ch}")
        for code in p["codes"] + m["elements"]:
            f = fiches.get(code)
            if not f: erreurs.append(f"{c} : code {code} absent de l'index")
            elif not f["codable"] and not desc.get(code): erreurs.append(f"{c} : code {code} non codable sans descendant codable ({f['statut_mco']})")
        for a, b in p["intervalles"] + m["intervalles"]:
            if not any(a <= k[:3] <= b for k in fiches): erreurs.append(f"{c} : intervalle {a}-{b} vide")
        for nom in p["listes"]:
            if nom not in listes: erreurs.append(f"{c} : liste {nom} absente de listes_codes")
        for nom in p["actes"]:
            if nom not in listes and d["evaluable"]: erreurs.append(f"{c} : liste d'actes {nom} absente (règle évaluable)")
        if not m["dp"] and not m["codes"]: erreurs.append(f"{c} : mode de prise en charge sans aucun code Z codable ({m['brut']!r})")
        if not p["aucun"] and not (p["chapitres"] or p["intervalles"] or p["codes"] or p["listes"] or p["actes"]): erreurs.append(f"{c} : pathologie sans contenu lisible ({p['brut']!r})")
        if not d["extrait"]["sections"] and not d["extrait"]["passages_communs"]: erreurs.append(f"{c} : aucun extrait officiel pour la règle {l['regle_officielle']}")
    print(f"{len(lignes)} lignes du guide ; {len({l['regle_officielle'] for l in lignes})} règles officielles ; familles : {dict(Counter(l['type'] for l in lignes))}")
    print(f"{'code':26s} {'règle':5s} {'pathologie (lue)':52s} {'modes Z codables':>16s}  extraits propres / communs")
    for l in lignes:
        p = l["details"]["pathologie"]; m = l["details"]["mode_prise_en_charge"]
        resume = ("Aucun" if p["aucun"] else "") + (" ou " if p["aucun"] and (p["chapitres"] or p["intervalles"] or p["codes"] or p["listes"] or p["actes"]) else "")
        resume += " ".join(filter(None, ["chapitres " + "-".join([p["chapitres"][0], p["chapitres"][-1]]) if len(p["chapitres"]) > 1 else ("chapitre " + p["chapitres"][0] if p["chapitres"] else ""),
                                         " ".join(f"{a}-{b}" for a, b in p["intervalles"]), " ".join(p["codes"]), " ".join(p["listes"]), " ".join(p["actes"])]))
        nb = len(m["codes"]); mode = ("DP" + (" + " if nb else "") if m["dp"] else "") + (f"{nb} code(s) Z" if nb else "")
        marque = "" if l["evaluable"] else "  [NON ÉVALUABLE]"
        print(f"{l['code']:26s} {l['regle_officielle']:5s} {resume[:52]:52s} {mode:>16s}  {len(l['details']['extrait']['sections'])} / {len(l['details']['extrait']['passages_communs'])}{marque}" + ("  [" + l["details"]["note"] + "]" if "note" in l["details"] else ""))
    if erreurs:
        print("\nCONTRÔLES EN ÉCHEC :"); [print("  -", e) for e in erreurs]; sys.exit(1)
    print("\ncontrôles : tous passés")
    if controler:
        print("--controler : rien n'a été écrit."); return
    env = charger_env(); base = create_client(env["SUPABASE_URL"], env["SUPABASE_SECRET_KEY"])
    base.table("regles_situations").upsert([{**l, "details": l["details"]} for l in lignes], on_conflict="code", returning="minimal").execute()
    n = base.table("regles_situations").select("code", count="exact", head=True).execute().count
    print(f"chargé : {len(lignes)} règles (en base : {n})")


if __name__ == "__main__":
    main()
