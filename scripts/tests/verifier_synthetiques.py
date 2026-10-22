"""Vérifications finales du chargement des CRH synthétiques (lecture seule, clé secrète).

Contrôle : ligne lots présente ; autant de documents et de codages scenario que de fichiers préparés ; aucun document sans
codage scenario ni avec plusieurs ; empreintes conformes aux textes et aux fichiers préparés ; aucun caractère interdit, aucun
bloc « Dictionnaire des formulations », aucun code entre parenthèses ; specialite et type_prise_en_charge sans chaîne vide ;
codages conformes (valide faux, utilisateur vide, une seule pathologie principale, codes codables, preuves relisibles) ;
le testeur ne voit ni le codage scenario ni nettoyage (vue dossiers_disponibles).

Usage : uv run python -I scripts/tests/verifier_synthetiques.py
"""
import hashlib
import json
import re
import sys
from pathlib import Path

from supabase import create_client

RACINE = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(RACINE / "scripts" / "chargement"))
from connexion import charger_env  # noqa: E402
from synthetiques_commun import LOT, PREPARE, REGLE_D, REGLE_E, lire_index  # noqa: E402

INTERDITS = {"U+00A0": " ", "U+202F": " ", "U+200B": "​", "U+FEFF": "﻿", "U+00AD": "­"}
RESULTATS = []


def controle(nom, attendu, obtenu):
    ok = attendu == obtenu
    RESULTATS.append(ok)
    print(f"  [{'OK' if ok else 'ÉCHEC'}] {nom} : attendu {attendu!r}, obtenu {obtenu!r}")


def tout(base, table, colonnes, filtre, pas=200):
    lignes, debut = [], 0
    while True:
        page = filtre(base.table(table).select(colonnes)).order("id").range(debut, debut + pas - 1).execute().data
        lignes.extend(page)
        if len(page) < pas:
            return lignes
        debut += pas


def main() -> None:
    env = charger_env()
    base = create_client(env["SUPABASE_URL"], env["SUPABASE_SECRET_KEY"])
    fiches, _ = lire_index()
    prepares = {f.stem: json.load(open(f, encoding="utf-8")) for f in (PREPARE / "documents").glob("*.json")}
    print(f"documents préparés sur le disque : {len(prepares)}")

    print("\n=== lot ===")
    lots = base.table("lots").select("id, contenu").eq("id", LOT).execute().data
    controle("ligne de lots présente", 1, len(lots))
    controle("contenu.echantillon.lignes_tirees", 500, (lots[0]["contenu"].get("echantillon", {}).get("lignes_tirees") if lots else None))

    print("\n=== documents ===")
    docs = tout(base, "documents", "id, id_source, version, texte, empreinte, nettoyage, specialite, type_prise_en_charge",
                lambda q: q.eq("lot", LOT))
    controle("nombre de documents", len(prepares), len(docs))
    controle("tous en version 1", len(docs), sum(d["version"] == 1 for d in docs))
    controle("id_source uniques et identiques aux fichiers", True, set(prepares) == {d["id_source"] for d in docs} and len(docs) == len({d["id_source"] for d in docs}))
    controle("empreinte = sha256 du texte", len(docs), sum(d["empreinte"] == hashlib.sha256(d["texte"].encode()).hexdigest() for d in docs))
    controle("texte identique au fichier préparé", len(docs), sum(d["texte"] == prepares[d["id_source"]]["texte"] for d in docs))
    controle("nettoyage identique au fichier préparé", len(docs), sum(d["nettoyage"] == prepares[d["id_source"]]["nettoyage"] for d in docs))
    for nom, car in INTERDITS.items():
        controle(f"aucun {nom}", 0, sum(car in d["texte"] for d in docs))
    controle("aucun bloc « Dictionnaire des formulations »", 0, sum(bool(REGLE_D.search(d["texte"])) for d in docs))
    controle("aucun code entre parenthèses ou crochets", 0, sum(bool(REGLE_E.search(d["texte"])) for d in docs))
    controle("aucun texte terminé par un blanc", 0, sum(d["texte"] != d["texte"].rstrip() for d in docs))
    controle("retraits D en base", sum(1 for p in prepares.values() for r in p["nettoyage"]["retraits"] if r["regle"] == "D"),
             sum(1 for d in docs for r in d["nettoyage"]["retraits"] if r["regle"] == "D"))
    controle("aucune chaîne vide dans specialite / type_prise_en_charge", 0,
             sum(d["specialite"] == "" or d["type_prise_en_charge"] == "" for d in docs))
    controle("specialite null", sum(p["specialite"] is None for p in prepares.values()), sum(d["specialite"] is None for d in docs))
    controle("type_prise_en_charge renseigné partout", len(docs), sum(bool(d["type_prise_en_charge"]) for d in docs))
    controle("aucune anomalie a_corriger", 0, sum(bool(d["nettoyage"]["anomalies"]) for d in docs))

    print("\n=== codages scenario ===")
    ids = [d["id"] for d in docs]
    codages = []
    for i in range(0, len(ids), 200):
        codages += tout(base, "codages", "id, document, etape, utilisateur, valide, codage, compteurs",
                        lambda q, lot=ids[i:i + 200]: q.eq("etape", "scenario").in_("document", lot))
    controle("un codage scenario par document", len(docs), len({c["document"] for c in codages}))
    controle("aucun document avec plusieurs codages scenario", len(codages), len({c["document"] for c in codages}))
    controle("utilisateur vide", len(codages), sum(c["utilisateur"] is None for c in codages))
    controle("valide faux", len(codages), sum(c["valide"] is False for c in codages))
    controle("compteurs vides", len(codages), sum(c["compteurs"] is None for c in codages))
    textes = {d["id"]: d["texte"] for d in docs}
    une_pp = codes_ok = preuves_ok = preuves_total = pnc_absent = regle_other = 0
    for c in codages:
        cj = c["codage"]
        une_pp += sum(e["categorie"] == "pathologie_principale" for e in cj["ensembles"]) == 1
        codes_ok += all(re.fullmatch(r"[A-Z]\d{2}[A-Z0-9]{0,3}(\+\d{1,2})?", e["code"]) and fiches.get(e["code"], {}).get("codable") for e in cj["ensembles"])
        pnc_absent += "passages_non_codes" not in cj
        regle_other += cj["regle_hierarchisation"] in ("other", "")
        for e in cj["ensembles"]:
            for p in e["preuves"]:
                preuves_total += 1
                if p.get("introuvable"):
                    preuves_ok += "debut" not in p and bool(p["texte"])
                else:
                    preuves_ok += textes[c["document"]][p["debut"]:p["fin"]] == p["texte"]
    controle("une seule pathologie principale par codage", len(codages), une_pp)
    controle("codes à la forme codeur et codables", len(codages), codes_ok)
    controle("passages_non_codes absent des codages scenario", len(codages), pnc_absent)
    controle("regle_hierarchisation jamais « other » ni vide", 0, regle_other)
    controle("preuves relisibles aux positions (ou introuvable sans positions)", preuves_total, preuves_ok)
    controle("mode_prise_en_charge renseigné", len(codages), sum(bool(c["codage"]["mode_prise_en_charge"]) for c in codages))
    controle("codages identiques aux fichiers préparés", len(codages),
             sum(c["codage"] == prepares[next(d["id_source"] for d in docs if d["id"] == c["document"])]["codage"] for c in codages))

    print("\n=== vue des testeurs ===")
    vue = tout(base, "dossiers_disponibles", "*", lambda q: q.eq("lot", LOT))
    controle("documents du lot visibles dans dossiers_disponibles", len(docs), len(vue))
    controle("ni nettoyage ni texte dans la vue", 0, sum(("nettoyage" in v) or ("texte" in v) for v in vue))

    print(f"\n{sum(RESULTATS)} contrôles réussis sur {len(RESULTATS)}")
    sys.exit(0 if all(RESULTATS) else 1)


if __name__ == "__main__":
    main()
