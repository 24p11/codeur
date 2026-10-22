"""Étapes 4 à 6 du lot B2 : préparation des 500 CRH synthétiques de l'échantillon.

Pour chaque ligne de donnees/prepare/synthetiques/echantillon_500.csv : nettoyage (règles D et E), normalisation (SCHEMA.md §2),
contrôle final des formes de code, codage `scenario` (SCHEMA.md §3.4 et §3.8) avec les preuves positionnées (toutes les
occurrences, mot entier, quatre niveaux de tolérance), colonnes de recherche. Écrit un JSON par document dans
donnees/prepare/synthetiques/documents/, puis rapport.md, preuves_introuvables.csv et codes_ajoutes.csv (hors git).
Ne touche ni à la source ni à la base (l'index est seulement lu).

Usage : uv run python -I scripts/chargement/synthetiques_preparer.py
"""
import csv
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

import polars as pl

sys.path.insert(0, str(Path(__file__).resolve().parent))
from synthetiques_commun import (LOT, PREPARE, SOURCE, _Formes, affinables, classer_code, code_de_cle, lire_index, lire_report,
                                 motifs_exclusion, nettoyer, normaliser, normaliser_code, rattacher, restes_de_codes, toutes_occurrences)

COLONNES = ["generation_id", "report", "icd_primary_code", "icd_secondary_code", "case_management_type", "coding_rule",
            "specialty", "specialite_source", "department", "TPEC", "DPEC", "mode_hospit", "template_name"]


def valeur(v):
    """Valeur brute nettoyée des blancs ; None si absente (jamais une chaîne vide)."""
    if v is None:
        return None
    v = " ".join(str(v).split())
    return v or None


def type_prise_en_charge(ligne: dict):
    """Décision du 22 octobre 2026 (docs/chargement.md §3.3) : « <DPEC>, <mode_hospit en clair> », valeurs brutes."""
    mode = {"HC": "en hospitalisation complète", "HP": "en hospitalisation partielle"}.get(ligne["mode_hospit"], valeur(ligne["mode_hospit"]))
    dpec = valeur(ligne["DPEC"])
    return f"{dpec}, {mode}" if dpec and mode else (dpec or mode)


def preparer(ligne: dict, fiches: dict, desc: dict, stats: dict, intro_csv: list) -> dict:
    gid = ligne["generation_id"]
    das_l = list(ligne["icd_secondary_code"] or [])
    raisons, obj = motifs_exclusion(ligne["report"], ligne["icd_primary_code"], das_l, ligne["case_management_type"], fiches, desc)
    assert not raisons, f"{gid} : ligne non éligible {raisons}"
    origine = obj["CR"]
    texte, retraits = nettoyer(origine)
    compteurs = Counter()
    texte = normaliser(texte, compteurs)
    for r in retraits:
        stats["retraits"][r["regle"]] += 1
    stats["normalisations"].update(compteurs)
    stats["restes"].update(restes_de_codes(texte))
    # codage scenario
    dp = normaliser_code(ligne["icd_primary_code"])
    das = [normaliser_code(d) for d in das_l]
    z = ligne["case_management_type"]
    mode = "DP" if z == "DP" else normaliser_code(z)
    if mode != "DP":
        stats["codes_z"][classer_code(mode, fiches, desc)] += 1
    regle = valeur(ligne["coding_rule"])
    regle = None if regle in (None, "other") else regle
    stats["regles"][regle or "(null)"] += 1
    scen = [dp] + das + ([mode] if mode != "DP" else [])
    citations = defaultdict(list)   # code du scénario -> citations (dédoublonnées, ordre conservé)
    for cle, cits in obj["formulations"]["diagnostics"].items():
        cj = code_de_cle(cle)
        cible = rattacher(cj, scen)
        assert cible is not None
        stats["rattachement"]["égalité" if cible == cj else "extension ou préfixe"] += 1
        for c in (cits if isinstance(cits, list) else [cits]):
            if isinstance(c, str) and c.strip() and c not in citations[cible]:
                citations[cible].append(c)
    formes = _Formes(texte)
    ensembles = []
    for code, categorie in [(dp, "pathologie_principale")] + [(d, "diagnostic_associe") for d in das]:
        preuves = []
        trouvees = 0
        for c in citations.get(code, []):
            occ = toutes_occurrences(texte, c, formes)
            if occ:
                trouvees += 1
                stats["niveaux"][occ[0][2]] += 1
                stats["occurrences"][min(len(occ), 4)] += 1
                for a, b, niveau in occ:
                    assert 0 <= a < b <= len(texte)
                    preuves.append({"debut": a, "fin": b, "texte": texte[a:b]})
                    stats["preuves_par_niveau"][niveau] += 1
            else:
                stats["niveaux"]["introuvable"] += 1
                preuves.append({"texte": c, "introuvable": True})
                intro_csv.append([gid, code, categorie, c])
        preuves.sort(key=lambda p: (p.get("debut", 10**9), p.get("fin", 10**9)))
        stats["citations_par_code"][categorie][("sans citation" if not citations.get(code) else "aucune retrouvée" if not trouvees else "au moins une retrouvée")] += 1
        if citations.get(code) and not trouvees:
            stats["exemples_sans_preuve"][categorie].append((code, fiches[code]["libelle"], citations[code][:3]))
        ensembles.append({"code": code, "libelle": fiches[code]["libelle"], "categorie": categorie, "preuves": preuves,
                          "confiance": None, "explication": None, "commentaires": []})
    if mode != "DP" and citations.get(mode):
        stats["citations_du_code_z"] += 1
    if affinables(ligne["icd_primary_code"], das_l, z, fiches, desc):
        stats["docs_affinables"] += 1
    stats["specialite"][valeur(ligne["specialty"]) or "(null)"] += 1
    stats["tpec"][(valeur(ligne["TPEC"]), valeur(ligne["DPEC"]), ligne["mode_hospit"])] += 1
    stats["type_pec"][type_prise_en_charge(ligne)] += 1
    return {
        "lot": LOT,
        "id_source": gid,
        "version": 1,
        "specialite": valeur(ligne["specialty"]),
        "type_prise_en_charge": type_prise_en_charge(ligne),
        "texte": texte,
        "nettoyage": {
            "documents_origine": [{"index": 1, "type": "CRH", "titre": None, "chemin": f"report[generation_id={gid}]",
                                   "intitule": None, "debut": 0, "debut_texte": 0, "fin": len(texte)}],
            "retraits": retraits,
            "normalisations": {k: v for k, v in compteurs.items() if v},
            "anomalies": {},
        },
        "codage": {"regle_hierarchisation": regle, "mode_prise_en_charge": mode, "commentaires": [], "ensembles": ensembles},
    }


def main() -> None:
    fiches, desc = lire_index()
    ech = pl.read_csv(PREPARE / "echantillon_500.csv")
    ids = ech["generation_id"].to_list()
    df = pl.read_parquet(SOURCE, columns=COLONNES).filter(pl.col("generation_id").is_in(ids))
    assert df.height == len(ids) == 500, df.height
    gabarit = dict(zip(ech["generation_id"], ech["gabarit"]))
    stats = {"retraits": Counter(), "normalisations": Counter(), "restes": Counter(), "codes_z": Counter(), "regles": Counter(),
             "rattachement": Counter(), "niveaux": Counter(), "occurrences": Counter(), "preuves_par_niveau": Counter(),
             "citations_par_code": {"pathologie_principale": Counter(), "diagnostic_associe": Counter()},
             "exemples_sans_preuve": {"pathologie_principale": [], "diagnostic_associe": []}, "citations_du_code_z": 0,
             "docs_affinables": 0, "specialite": Counter(), "tpec": Counter(), "type_pec": Counter()}
    intro_csv = []
    dossier = PREPARE / "documents"
    dossier.mkdir(parents=True, exist_ok=True)
    docs = []
    for ligne in df.iter_rows(named=True):
        d = preparer(ligne, fiches, desc, stats, intro_csv)
        docs.append(d)
    # contrôle automatique : chaque preuve positionnée relit exactement son texte, dans un codage conforme
    for d in docs:
        assert sum(e["categorie"] == "pathologie_principale" for e in d["codage"]["ensembles"]) == 1
        for e in d["codage"]["ensembles"]:
            assert fiches[e["code"]]["codable"]
            for p in e["preuves"]:
                if not p.get("introuvable"):
                    assert d["texte"][p["debut"]:p["fin"]] == p["texte"]
        assert not d["texte"].endswith(("\n", " ")) and " " not in d["texte"]
    for d in docs:
        (dossier / f"{d['id_source']}.json").write_text(json.dumps(d, ensure_ascii=False, indent=1), encoding="utf-8")
    with open(PREPARE / "preuves_introuvables.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f); w.writerow(["generation_id", "code", "categorie", "citation"]); w.writerows(intro_csv)
    with open(PREPARE / "codes_ajoutes.csv", "w", newline="", encoding="utf-8") as f:
        csv.writer(f).writerow(["generation_id", "code", "libelle", "citations", "decision"])
    n_ens = sum(len(d["codage"]["ensembles"]) for d in docs)
    n_preuves = sum(len(e["preuves"]) for d in docs for e in d["codage"]["ensembles"])
    n_intro = sum(1 for d in docs for e in d["codage"]["ensembles"] for p in e["preuves"] if p.get("introuvable"))
    tot_cit = sum(stats["niveaux"].values())
    L = [f"# Préparation du lot {LOT}", "",
         f"Source : {SOURCE.name} ; échantillon : {len(docs)} documents (echantillon_500.csv, graine 20261022, répartition mixte) ; "
         f"gabarits : " + ", ".join(f"{g} {n}" for g, n in Counter(gabarit.values()).most_common()) + ".", "",
         "## Nettoyage (étape 4)", "",
         f"- Retraits : " + ", ".join(f"règle {k} : {v}" for k, v in sorted(stats["retraits"].items())) + " (positions dans le texte d'origine, dans `nettoyage.retraits`).",
         f"- Normalisations (caractères) : {dict(stats['normalisations']) or 'aucune'}.",
         f"- Contrôle final, formes de code et mentions CIM-10 restantes (à juger à chaque exécution) : " + ", ".join(f"{k} {v}" for k, v in stats["restes"].most_common()) + ".", "",
         "## Codage `scenario` (étape 5)", "",
         f"- {n_ens} ensembles ({len(docs)} pathologies principales, {n_ens - len(docs)} diagnostics associés), {n_preuves} preuves dont {n_intro} introuvables.",
         f"- Clés du JSON rattachées : {dict(stats['rattachement'])} ; codes ajoutés par le générateur : 0 (exclus par la règle de l'étape 2) ; clés rattachées au code Z de prise en charge (citations non reprises, le code Z n'étant pas un ensemble) : {stats['citations_du_code_z']} documents.",
         f"- Citations distinctes : {tot_cit} ; par niveau : " + ", ".join(f"{k} {v} ({100 * v / tot_cit:.1f} %)" for k, v in stats["niveaux"].most_common()) + ".",
         f"- Occurrences par citation retrouvée (toutes gardées, mot entier) : " + ", ".join(f"{k}{'+' if k == 4 else ''} : {v}" for k, v in sorted(stats["occurrences"].items())) + f" ; preuves positionnées par niveau : {dict(stats['preuves_par_niveau'])}.",
         f"- Mode de prise en charge : {len(docs) - sum(stats['codes_z'].values())} « DP », {sum(stats['codes_z'].values())} codes Z, tous codables ({dict(stats['codes_z'])}).",
         f"- Règle de hiérarchisation (`null` quand `coding_rule` vaut `other` ou est vide ; confrontation au guide des situations cliniques à faire à sa livraison) : " + ", ".join(f"{k} {v}" for k, v in stats["regles"].most_common()) + ".",
         f"- Documents avec au moins un code affinable (SCHEMA §3.10, docs/chargement.md §3.1) : {stats['docs_affinables']}.", "",
         "### Codes dont aucune citation n'a été retrouvée", ""]
    for cat in ("pathologie_principale", "diagnostic_associe"):
        c = stats["citations_par_code"][cat]
        L.append(f"- {cat} : {c['au moins une retrouvée']} avec au moins une preuve positionnée, **{c['aucune retrouvée']} sans aucune citation retrouvée**, {c['sans citation']} sans citation dans le JSON.")
        for code, lib, cits in stats["exemples_sans_preuve"][cat][:3]:
            L.append(f"  - `{code}` {lib[:50]} : " + " | ".join(f"« {x[:60]} »" for x in cits))
    L += ["", "## Colonnes de recherche (étape 6)", "",
          f"- `specialite` ← `specialty`, null sans spécialité ({len(stats['specialite'])} valeurs, dont (null) {stats['specialite']['(null)']}) : " + ", ".join(f"{k} {v}" for k, v in stats["specialite"].most_common(8)) + "…",
          "- Combinaisons (TPEC, DPEC, mode_hospit) :"]
    for (a, b, c), n in stats["tpec"].most_common():
        L.append(f"  - {a} | {b} | {c} : {n}")
    L.append("- `type_prise_en_charge` (« DPEC, mode en clair ») : " + " ; ".join(f"{k} : {v}" for k, v in stats["type_pec"].most_common()))
    (PREPARE / "rapport.md").write_text("\n".join(L) + "\n", encoding="utf-8")
    print("\n".join(L))
    print(f"\nÉcrit : {len(docs)} fichiers dans {dossier}, rapport.md, preuves_introuvables.csv ({len(intro_csv)} lignes), codes_ajoutes.csv (vide)")


if __name__ == "__main__":
    main()
