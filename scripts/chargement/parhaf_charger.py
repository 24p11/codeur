"""Charge PARHAF préparé (donnees/prepare/parhaf/) dans la base, avec la clé secrète.

Charge : une ligne dans `lots`, une ligne dans `documents` par dossier (version 1), une ligne dans `codages`
(étape scenario) par document. Référence : docs/SCHEMA.md §2, §3.4, §3.7, §6.

Relançable sans risque : un dossier déjà chargé (même lot, id_source, version) est signalé et passé ;
un document chargé mais sans codage scenario (interruption précédente) reçoit son codage.
Charge par paquets ; s'arrête à la première erreur en indiquant où il en est. Ne modifie ni ne supprime rien.

Usage :
  uv run python -I scripts/chargement/parhaf_charger.py            # chargement complet
  uv run python -I scripts/chargement/parhaf_charger.py --essai    # 10 dossiers variés seulement
  uv run python -I scripts/chargement/parhaf_charger.py --paquet 50
"""
import argparse
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

from supabase import create_client

RACINE = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(RACINE / "scripts" / "tests"))
from connexion import charger_env  # noqa: E402

PREPARE = RACINE / "donnees" / "prepare" / "parhaf"
LOT = {
    "id": "parhaf-1.0.0",
    "source": "Hugging Face, HealthDataHub/PARHAF, version JSON standalone (patients.json + textes), projet PARTAGES",
    "version": "1.0.0",
    "description": "Comptes rendus fictifs rédigés par des internes (PARHAF 1.0.0). Un dossier = un patient, documents "
                   "d'origine concaténés dans l'ordre du fichier avec un intitulé devant chacun. Patients dont le dossier "
                   "n'est que de l'anatomopathologie exclus. Codage initial : le diagnostic principal du scénario, sans preuves.",
    "contenu": {
        "texte": True,
        "pathologie_principale": True,
        "diagnostics_associes": False,
        "regle_hierarchisation": False,
        "mode_prise_en_charge": False,
        "preuves": False,
        "documents_par_dossier": "1 à 3 (consultation, compte rendu opératoire, hospitalisation, urgences, accouchement, maternité)",
    },
    "regles_nettoyage": [
        {"regle": "selection", "description": "exclusion des patients dont tous les documents sont de type ANAPATH"},
        {"regle": "A", "description": "retrait d'une ligne « Résumé structuré » et de tout ce qui la suit"},
        {"regle": "B", "description": "retrait d'une ligne « Diagnostics fréquemment associés » et de tout ce qui la suit"},
        {"regle": "C", "description": "CANCERO-ADULTE-01016 (consultation) : retrait de la liste de diagnostics codés qui suit la signature"},
        {"regle": "normalisation", "description": "NFC ; suppression de U+200B, U+FEFF, U+00AD ; U+00A0 et U+202F remplacés par une espace ; blancs de fin de document retirés"},
        {"regle": "intitules", "description": "intitulé normalisé sur sa ligne devant chaque document d'origine quand le dossier en compte plusieurs"},
        {"regle": "a_corriger", "description": "5 CRH contenant des codes CIM-10 dans leur corps, chargés tels quels et signalés dans nettoyage.anomalies"},
    ],
}


def empreinte(texte: str) -> str:
    return hashlib.sha256(texte.encode("utf-8")).hexdigest()


def choisir_essai(dossiers: list[Path]) -> list[Path]:
    """Dix dossiers variés : compositions différentes, règle A, règle B, cas C, dossier à corriger."""
    voulus = [
        ("CRH seul, neurologie", lambda d: d["id_source"].startswith("NEUROLOGIE") and comp(d) == "CRH" and not d["nettoyage"]["retraits"]),
        ("CRH seul, pneumologie", lambda d: d["id_source"].startswith("PNEUMOLOGIE") and comp(d) == "CRH"),
        ("CRH seul, pédiatrie", lambda d: d["id_source"].startswith("MEDECINE-PEDIATRIQUE") and comp(d) == "CRH"),
        ("chirurgie 3 documents, viscérale", lambda d: d["id_source"].startswith("CHIRURGIE-VISCERALE") and comp(d) == "CRC > CRO > CRH"),
        ("chirurgie 3 documents, orthopédie", lambda d: d["id_source"].startswith("CHIR-ORTHO") and comp(d) == "CRC > CRO > CRH"),
        ("consultation seule, oncologie, règle B", lambda d: comp(d) == "CRC" and any(r["regle"] == "B" for r in d["nettoyage"]["retraits"])),
        ("parcours obstétrical", lambda d: comp(d) == "URGENCES > ACCOUCHEMENT > MATERNITE"),
        ("règle A", lambda d: any(r["regle"] == "A" for r in d["nettoyage"]["retraits"])),
        ("cas C", lambda d: any(r["regle"] == "C" for r in d["nettoyage"]["retraits"])),
        ("à corriger", lambda d: d["nettoyage"]["anomalies"].get("a_corriger")),
    ]
    choisis, pris = [], set()
    for nom, critere in voulus:
        for f in dossiers:
            if f in pris:
                continue
            d = json.load(open(f, encoding="utf-8"))
            if critere(d):
                choisis.append(f); pris.add(f)
                print(f"  essai : {nom:40s} -> {d['id_source']}")
                break
    return choisis


def comp(d: dict) -> str:
    return " > ".join(x["type"] for x in d["nettoyage"]["documents_origine"])


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--essai", action="store_true", help="ne charge que 10 dossiers variés")
    ap.add_argument("--paquet", type=int, default=100, help="dossiers par paquet (défaut 100)")
    args = ap.parse_args()

    env = charger_env()
    base = create_client(env["SUPABASE_URL"], env["SUPABASE_SECRET_KEY"])
    dossiers = sorted((PREPARE / "documents").glob("*.json"))
    if not dossiers:
        raise SystemExit("aucun dossier préparé : lancer d'abord parhaf_preparer.py")
    if args.essai:
        dossiers = choisir_essai(dossiers)
    print(f"{len(dossiers)} dossiers à traiter, par paquets de {args.paquet} ; lot {LOT['id']}")

    # 1. le lot
    existant = base.table("lots").select("id, charge_le").eq("id", LOT["id"]).execute().data
    if existant:
        print(f"lot {LOT['id']} déjà présent (chargé le {existant[0]['charge_le']}) : conservé tel quel")
    else:
        base.table("lots").insert(LOT, returning="minimal").execute()
        print(f"lot {LOT['id']} créé")

    # 2. et 3. les documents et leurs codages, par paquets
    bilan = {"documents_inseres": 0, "documents_deja_la": 0, "codages_inseres": 0, "codages_completes": 0, "empreintes_ok": 0}
    for debut in range(0, len(dossiers), args.paquet):
        paquet = dossiers[debut:debut + args.paquet]
        numero = debut // args.paquet + 1
        prepares = {}
        for f in paquet:
            d = json.load(open(f, encoding="utf-8"))
            prepares[d["id_source"]] = d
        try:
            # dossiers déjà chargés dans ce paquet
            deja = base.table("documents").select("id, id_source, empreinte").eq("lot", LOT["id"]).eq("version", 1) \
                .in_("id_source", list(prepares)).execute().data
            ids_docs = {r["id_source"]: r["id"] for r in deja}
            for r in deja:
                bilan["documents_deja_la"] += 1
                if r["empreinte"] != empreinte(prepares[r["id_source"]]["texte"]):
                    raise RuntimeError(f"{r['id_source']} déjà chargé avec un texte DIFFÉRENT (empreinte {r['empreinte'][:12]}…) : arrêt")
            # insertion des documents manquants
            nouveaux = [{"lot": LOT["id"], "id_source": k, "version": 1, "specialite": d["specialite"],
                         "type_prise_en_charge": d["type_prise_en_charge"], "texte": d["texte"], "nettoyage": d["nettoyage"]}
                        for k, d in prepares.items() if k not in ids_docs]
            if nouveaux:
                inseres = base.table("documents").insert(nouveaux).execute().data
                for r in inseres:
                    ids_docs[r["id_source"]] = r["id"]
                    if r["empreinte"] != empreinte(prepares[r["id_source"]]["texte"]):
                        raise RuntimeError(f"{r['id_source']} : empreinte calculée par la base différente de l'empreinte locale : arrêt")
                    bilan["empreintes_ok"] += 1
                bilan["documents_inseres"] += len(inseres)
            # codages scenario manquants (tous pour les nouveaux ; contrôle pour les anciens)
            avec_codage = {r["document"] for r in base.table("codages").select("document").eq("etape", "scenario")
                           .in_("document", list(ids_docs.values())).execute().data}
            codages = [{"document": ids_docs[k], "etape": "scenario", "utilisateur": None, "codage": d["codage"], "compteurs": None}
                       for k, d in prepares.items() if ids_docs[k] not in avec_codage]
            if codages:
                base.table("codages").insert(codages, returning="minimal").execute()
                nb_completes = sum(1 for k in prepares if k in {r["id_source"] for r in deja} and ids_docs[k] not in avec_codage)
                bilan["codages_inseres"] += len(codages) - nb_completes
                bilan["codages_completes"] += nb_completes
            print(f"paquet {numero:3d} ({paquet[0].stem} … {paquet[-1].stem}) : "
                  f"{len(nouveaux)} documents insérés, {len(deja)} déjà là, {len(codages)} codages insérés")
        except Exception as e:  # noqa: BLE001
            print(f"\nERREUR au paquet {numero} (dossiers {paquet[0].stem} à {paquet[-1].stem}) : {getattr(e, 'message', e)}")
            print("Les paquets précédents sont chargés ; relancer le script reprend sans doublon.")
            sys.exit(1)

    print(f"\nTerminé le {datetime.now(timezone.utc).isoformat(timespec='seconds')} : "
          f"{bilan['documents_inseres']} documents insérés (empreintes vérifiées : {bilan['empreintes_ok']}), "
          f"{bilan['documents_deja_la']} déjà présents, {bilan['codages_inseres']} codages scenario insérés, "
          f"{bilan['codages_completes']} codages complétés sur des documents déjà présents.")


if __name__ == "__main__":
    main()
