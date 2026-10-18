"""Vérifications finales du chargement de PARHAF (lecture seule, clé secrète).

Contrôle : nombre de documents et de codages scenario égal au nombre de dossiers préparés ; aucun document
sans codage scenario (ni avec plusieurs) ; empreintes conformes aux textes et aux fichiers préparés ;
les 5 dossiers à corriger signalés, et eux seuls ; aucun caractère U+00A0, U+202F, U+200B, U+FEFF, U+00AD ;
aucun bloc « Résumé structuré » ni « Diagnostics fréquemment associés » ; codages scenario conformes
(valide faux, utilisateur vide, un seul ensemble pathologie_principale, code sans point ni espace).

Usage : uv run python -I scripts/tests/verifier_parhaf.py
"""
import hashlib
import json
import re
import sys
from pathlib import Path

from supabase import create_client

RACINE = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(Path(__file__).resolve().parent))
from connexion import charger_env  # noqa: E402

LOT = "parhaf-1.0.0"
PREPARE = RACINE / "donnees" / "prepare" / "parhaf" / "documents"
A_CORRIGER = {"HEMATOLOGIE-CLINIQUE-00049", "HEMATOLOGIE-CLINIQUE-00072", "HEMATOLOGIE-CLINIQUE-00105",
              "MEDECINE-GERIATRIQUE-00038", "MEDECINE-GERIATRIQUE-00192"}
REGLE_A = re.compile(r"^[ \t]*r[ée]sum[ée] structur[ée][ \t]*:?[ \t]*$", re.I | re.M)
REGLE_B = re.compile(r"^[ \t]*diagnostics? fr[ée]quemment associ[ée]s?.*$", re.I | re.M)
INTERDITS = {"U+00A0": " ", "U+202F": " ", "U+200B": "​", "U+FEFF": "﻿", "U+00AD": "­"}
RESULTATS = []


def controle(nom, attendu, obtenu):
    ok = attendu == obtenu
    RESULTATS.append(ok)
    print(f"  [{'OK' if ok else 'ÉCHEC'}] {nom} : attendu {attendu!r}, obtenu {obtenu!r}")


def tout(base, table, colonnes, filtre, pas=500):
    """Lit toutes les lignes d'une table par pages (PostgREST limite chaque réponse)."""
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
    prepares = {f.stem: json.load(open(f, encoding="utf-8")) for f in PREPARE.glob("*.json")}
    print(f"dossiers préparés sur le disque : {len(prepares)}")

    print("\n=== lot ===")
    controle("ligne de lots présente", 1, len(base.table("lots").select("id").eq("id", LOT).execute().data))

    print("\n=== documents ===")
    docs = tout(base, "documents", "id, id_source, version, texte, empreinte, nettoyage, specialite, type_prise_en_charge",
                lambda q: q.eq("lot", LOT))
    controle("nombre de documents du lot", len(prepares), len(docs))
    controle("toutes en version 1", len(docs), sum(1 for d in docs if d["version"] == 1))
    controle("id_source distincts (aucun doublon)", len(docs), len({d["id_source"] for d in docs}))
    controle("id_source absents des dossiers préparés ou inversement", 0, len(set(prepares) ^ {d["id_source"] for d in docs}))
    controle("empreinte en base = SHA-256 du texte en base", len(docs),
             sum(1 for d in docs if hashlib.sha256(d["texte"].encode("utf-8")).hexdigest() == d["empreinte"]))
    controle("texte en base = texte préparé", len(docs), sum(1 for d in docs if d["texte"] == prepares[d["id_source"]]["texte"]))
    for nom, car in INTERDITS.items():
        controle(f"aucun texte contenant {nom}", 0, sum(1 for d in docs if car in d["texte"]))
    controle("aucun bloc « Résumé structuré »", 0, sum(1 for d in docs if REGLE_A.search(d["texte"])))
    controle("aucun bloc « Diagnostics fréquemment associés »", 0, sum(1 for d in docs if REGLE_B.search(d["texte"])))
    controle("aucun texte se terminant par un blanc", 0, sum(1 for d in docs if d["texte"] != d["texte"].rstrip()))
    signales = {d["id_source"] for d in docs if d["nettoyage"].get("anomalies", {}).get("a_corriger")}
    controle("dossiers signalés à corriger", A_CORRIGER, signales)
    controle("intitulés présents sur les dossiers à plusieurs documents", 0,
             sum(1 for d in docs if len(d["nettoyage"]["documents_origine"]) > 1 and not d["texte"].startswith("— ")))
    controle("specialite renseignée", len(docs), sum(1 for d in docs if d["specialite"]))
    print(f"  (information) type_prise_en_charge vide : {sum(1 for d in docs if d['type_prise_en_charge'] is None)}")

    print("\n=== codages scenario ===")
    ids = {d["id"] for d in docs}
    codages = tout(base, "codages", "id, document, etape, utilisateur, valide, compteurs, codage", lambda q: q.eq("etape", "scenario"))
    codages = [c for c in codages if c["document"] in ids]
    par_doc = {}
    for c in codages:
        par_doc.setdefault(c["document"], []).append(c)
    controle("nombre de codages scenario", len(docs), len(codages))
    controle("documents sans codage scenario", 0, sum(1 for i in ids if i not in par_doc))
    controle("documents avec plusieurs codages scenario", 0, sum(1 for v in par_doc.values() if len(v) > 1))
    controle("valide = faux partout", len(codages), sum(1 for c in codages if c["valide"] is False))
    controle("utilisateur vide partout", len(codages), sum(1 for c in codages if c["utilisateur"] is None))
    controle("compteurs vide partout", len(codages), sum(1 for c in codages if c["compteurs"] is None))
    controle("un seul ensemble, pathologie_principale, sans preuves", len(codages),
             sum(1 for c in codages if len(c["codage"]["ensembles"]) == 1 and c["codage"]["ensembles"][0]["categorie"] == "pathologie_principale"
                 and c["codage"]["ensembles"][0]["preuves"] == []))
    controle("règle et mode de prise en charge à null", len(codages),
             sum(1 for c in codages if c["codage"]["regle_hierarchisation"] is None and c["codage"]["mode_prise_en_charge"] is None))
    codes = [c["codage"]["ensembles"][0]["code"] for c in codages]
    controle("codes sans point ni espace", len(codes), sum(1 for k in codes if "." not in k and " " not in k))
    ids_vers_source = {d["id"]: d["id_source"] for d in docs}
    controle("code du codage = DP préparé", len(codages),
             sum(1 for c in codages if c["codage"] == prepares[ids_vers_source[c["document"]]]["codage"]))
    print(f"  (information) codes DP distincts : {len(set(codes))}")

    ok, total = sum(RESULTATS), len(RESULTATS)
    print(f"\nBILAN : {ok} contrôles réussis sur {total}")
    sys.exit(0 if ok == total else 1)


if __name__ == "__main__":
    main()
