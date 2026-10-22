"""Charge l'échantillon de CRH synthétiques préparé (donnees/prepare/synthetiques/documents/) dans la base, clé secrète.

Charge : une ligne dans `lots`, une ligne dans `documents` par CRH (version 1), une ligne dans `codages` (étape scenario,
utilisateur vide) par document. Référence : docs/SCHEMA.md §2, §3.4, §3.8, §6 ; docs/chargement.md §3.

Relançable sans risque : un document déjà chargé (même lot, id_source, version) est signalé et passé, son texte vérifié
par l'empreinte ; un document chargé sans codage scenario reçoit son codage. Ne modifie ni ne supprime jamais rien.

Usage :
  uv run python -I scripts/chargement/synthetiques_charger.py --blanc   # essai à blanc : bilan complet, aucune écriture
  uv run python -I scripts/chargement/synthetiques_charger.py           # chargement (après accord)
  uv run python -I scripts/chargement/synthetiques_charger.py --paquet 50
"""
import argparse
import hashlib
import json
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

from supabase import create_client

RACINE = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(RACINE / "scripts" / "tests"))
sys.path.insert(0, str(Path(__file__).resolve().parent))
from connexion import charger_env  # noqa: E402
from synthetiques_commun import LOT as ID_LOT, PREPARE  # noqa: E402

LOT = {
    "id": ID_LOT,
    "source": "CRH synthétiques, run08, fichier run08_scenarios_reports_merged_20261007_160916.parquet "
              "(100 000 lignes, SHA-256 bc6a7ed59cfc35dc…)",
    "version": "run08-20261007",
    "description": "Échantillon de 500 CRH synthétiques (une variante par scénario, répartition mixte entre six gabarits, "
                   "graine 20261022) avec codage de référence complet et preuves positionnées.",
    "contenu": {
        "texte": True,
        "pathologie_principale": True,
        "diagnostics_associes": True,
        "regle_hierarchisation": "coding_rule du scénario ; null quand other ou vide ; non confrontée au guide des situations cliniques",
        "mode_prise_en_charge": "case_management_type du scénario : DP ou code Z",
        "preuves": "citations du JSON formulations.diagnostics positionnées dans le texte nettoyé : toutes les occurrences, "
                   "mot entier, tolérance casse/espaces, accents, gras markdown ; citations introuvables conservées avec introuvable",
        "libelles": "libellés officiels de l'index recode-icd 65701d6_atih-2025",
        "documents_par_dossier": "1 (un CRH par ligne de la source)",
        "echantillon": {
            "graine": 20261022,
            "generateur": "random.Random(graine).sample sur la liste triée des generation_id de chaque gabarit",
            "variante": "une par scénario : la plus petite valeur de `variante` (generation_id croissant en cas d'égalité)",
            "repartition": "mixte : 40 au minimum par gabarit, le reste au prorata des lignes éligibles",
            "minimum_par_gabarit": 40,
            "lignes_eligibles": 86346,
            "lignes_tirees": 500,
            "par_gabarit": {  # lignes éligibles (une variante par scénario) et lignes tirées, docs/chargement.md §3.2
                "medical_outpatient": {"eligibles": 34131, "tirees": 143},
                "medical_inpatient": {"eligibles": 26784, "tirees": 121},
                "surgery_outpatient": {"eligibles": 11345, "tirees": 74},
                "surgery_inpatient": {"eligibles": 9315, "tirees": 68},
                "medical_outpatient_onco": {"eligibles": 4038, "tirees": 52},
                "medical_inpatient_onco": {"eligibles": 733, "tirees": 42},
            },
            "ponderation": "un résultat global se pondère par eligibles / lignes_eligibles de chaque gabarit",
        },
    },
    "regles_nettoyage": [
        {"regle": "eligibilite", "description": "JSON réparable ; DP, DAS et code Z codables dans le kit ; toutes les clés du JSON "
                                                "avec un code reconnu et rattaché au scénario (docs/chargement.md §3.1)"},
        {"regle": "D", "description": "retrait d'une ligne « Dictionnaire(s) des formulations » et de tout ce qui la suit, "
                                      "avec la ligne --- collée au bloc et les lignes vides qui précèdent"},
        {"regle": "E", "description": "retrait d'un code CIM-10 entre parenthèses ou crochets dans le corps du texte, avec l'espace qui le précède"},
        {"regle": "normalisation", "description": "NFC ; suppression de U+200B, U+FEFF, U+00AD ; U+00A0 et U+202F remplacés "
                                                  "par une espace ; blancs de fin retirés"},
        {"regle": "controle_final", "description": "aucune forme de code ni mention CIM-10 ne subsiste (liste jugée à chaque exécution)"},
    ],
}


def empreinte(texte: str) -> str:
    return hashlib.sha256(texte.encode("utf-8")).hexdigest()


def bilan_prepare(docs: dict) -> None:
    """Le bilan de ce qui va être chargé, calculé sur les fichiers préparés."""
    c = Counter()
    for d in docs.values():
        c["documents"] += 1
        c["retraits"] += len(d["nettoyage"]["retraits"])
        for r in d["nettoyage"]["retraits"]:
            c[f"retraits règle {r['regle']}"] += 1
        c["codages"] += 1
        c["ensembles"] += len(d["codage"]["ensembles"])
        for e in d["codage"]["ensembles"]:
            c[e["categorie"]] += 1
            for p in e["preuves"]:
                c["preuves introuvables" if p.get("introuvable") else "preuves positionnées"] += 1
        c["mode Z"] += d["codage"]["mode_prise_en_charge"] != "DP"
        c["regle null"] += d["codage"]["regle_hierarchisation"] is None
        c["specialite null"] += d["specialite"] is None
        c["type_prise_en_charge null"] += d["type_prise_en_charge"] is None
    print("Bilan des fichiers préparés :")
    for k, v in c.items():
        print(f"  {k:28s} {v}")
    print(f"  gabarits : voir echantillon_500.csv ; lignes de la source écartées du tirage : 3 760 (docs/chargement.md §3.1)")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--blanc", action="store_true", help="essai à blanc : aucune écriture")
    ap.add_argument("--paquet", type=int, default=100)
    args = ap.parse_args()
    env = charger_env()
    base = create_client(env["SUPABASE_URL"], env["SUPABASE_SECRET_KEY"])
    fichiers = sorted((PREPARE / "documents").glob("*.json"))
    if not fichiers:
        raise SystemExit("aucun document préparé : lancer d'abord synthetiques_preparer.py")
    docs = {}
    for f in fichiers:
        d = json.load(open(f, encoding="utf-8"))
        assert d["lot"] == LOT["id"] and d["version"] == 1 and d["id_source"] == f.stem
        docs[d["id_source"]] = d
    print(f"{len(docs)} documents préparés ; lot {LOT['id']} ; paquets de {args.paquet}" + (" ; ESSAI À BLANC" if args.blanc else ""))
    bilan_prepare(docs)

    existant = base.table("lots").select("id, charge_le").eq("id", LOT["id"]).execute().data
    deja_tous = base.table("documents").select("id_source").eq("lot", LOT["id"]).eq("version", 1).execute().data
    print(f"\nEn base : lot {'déjà présent (chargé le ' + existant[0]['charge_le'] + ')' if existant else 'absent'} ; "
          f"documents du lot déjà chargés : {len(deja_tous)}")
    if args.blanc:
        print("Essai à blanc terminé : rien n'a été écrit.")
        return

    if not existant:
        base.table("lots").insert(LOT, returning="minimal").execute()
        print(f"lot {LOT['id']} créé")
    ids = sorted(docs)
    bilan = Counter()
    for debut in range(0, len(ids), args.paquet):
        paquet = ids[debut:debut + args.paquet]
        numero = debut // args.paquet + 1
        try:
            deja = base.table("documents").select("id, id_source, empreinte").eq("lot", LOT["id"]).eq("version", 1) \
                .in_("id_source", paquet).execute().data
            ids_docs = {r["id_source"]: r["id"] for r in deja}
            for r in deja:
                bilan["documents_deja_la"] += 1
                if r["empreinte"] != empreinte(docs[r["id_source"]]["texte"]):
                    raise RuntimeError(f"{r['id_source']} déjà chargé avec un texte DIFFÉRENT : arrêt")
            nouveaux = [{"lot": LOT["id"], "id_source": k, "version": 1, "specialite": docs[k]["specialite"],
                         "type_prise_en_charge": docs[k]["type_prise_en_charge"], "texte": docs[k]["texte"], "nettoyage": docs[k]["nettoyage"]}
                        for k in paquet if k not in ids_docs]
            if nouveaux:
                inseres = base.table("documents").insert(nouveaux).execute().data
                for r in inseres:
                    ids_docs[r["id_source"]] = r["id"]
                    if r["empreinte"] != empreinte(docs[r["id_source"]]["texte"]):
                        raise RuntimeError(f"{r['id_source']} : empreinte calculée par la base différente de l'empreinte locale : arrêt")
                bilan["documents_inseres"] += len(inseres)
            avec_codage = {r["document"] for r in base.table("codages").select("document").eq("etape", "scenario")
                           .in_("document", list(ids_docs.values())).execute().data}
            codages = [{"document": ids_docs[k], "etape": "scenario", "utilisateur": None, "codage": docs[k]["codage"], "compteurs": None}
                       for k in paquet if ids_docs[k] not in avec_codage]
            if codages:
                base.table("codages").insert(codages, returning="minimal").execute()
                bilan["codages_inseres"] += len(codages)
            print(f"paquet {numero:2d} : {len(nouveaux)} documents insérés, {len(deja)} déjà là, {len(codages)} codages insérés")
        except Exception as e:  # noqa: BLE001
            print(f"\nERREUR au paquet {numero} : {getattr(e, 'message', e)}\nLes paquets précédents sont chargés ; relancer reprend sans doublon.")
            sys.exit(1)
    print(f"\nTerminé le {datetime.now(timezone.utc).isoformat(timespec='seconds')} : {dict(bilan)}")


if __name__ == "__main__":
    main()
