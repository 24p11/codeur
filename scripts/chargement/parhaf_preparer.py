"""Prépare PARHAF pour le chargement : un fichier JSON par dossier (= patient) dans donnees/prepare/parhaf/.

Ne se connecte pas à la base. Ne modifie jamais les fichiers sources de donnees/parhaf/.
Référence : docs/SCHEMA.md §2 (texte de référence), §3.4 et §3.7 (codage initial) ; CADRAGE.md §4.2 ;
docs/exploration/inventaire_corpus.md §1.6 (règles A, B, C) et §1.7 (patients retenus).

Pour chaque patient retenu (tous sauf ceux dont le dossier n'est que de l'anatomopathologie) :
  1. nettoyage de chaque document d'origine (règles A, B, cas C), positions dans le texte d'origine ;
  2. normalisation : NFC, suppression de U+200B, U+FEFF, U+00AD, remplacement de U+00A0 et U+202F
     par une espace, retrait des blancs de fin ;
  3. concaténation dans l'ordre du fichier, avec un intitulé normalisé devant chaque document
     quand le dossier en compte plusieurs ;
  4. colonnes de recherche, champ `nettoyage`, codage initial (étape scenario).

Usage : uv run python -I scripts/chargement/parhaf_preparer.py
"""
import json
import re
import unicodedata
from collections import Counter
from pathlib import Path
from statistics import median

RACINE = Path(__file__).resolve().parents[2]
SOURCE = RACINE / "donnees" / "parhaf" / "standalone"
TEXTES = SOURCE / "textes"
SORTIE = RACINE / "donnees" / "prepare" / "parhaf"
LOT = "parhaf-1.0.0"

INTITULES = {
    "CRC": "— Consultation —",
    "CRO": "— Compte rendu opératoire —",
    "CRH": "— Compte rendu d'hospitalisation —",
    "URGENCES": "— Urgences —",
    "ACCOUCHEMENT": "— Accouchement —",
    "MATERNITE": "— Maternité —",
}
# Règle A : une ligne entière « Résumé structuré » ; règle B : une ligne commençant par « Diagnostics fréquemment associés ».
REGLE_A = re.compile(r"^[ \t]*r[ée]sum[ée] structur[ée][ \t]*:?[ \t]*$", re.I | re.M)
REGLE_B = re.compile(r"^[ \t]*diagnostics? fr[ée]quemment associ[ée]s?.*$", re.I | re.M)
# Cas C : CANCERO-ADULTE-01016, consultation : liste de diagnostics codés après la signature, sans titre.
CAS_C = {("CANCERO-ADULTE-01016", "CRC"): ("Dr TUMAB", re.compile(r"^-   .*\[[A-Z]\d{2}[A-Za-z0-9.+]*\][ \t]*$", re.M))}
CODE_CROCHETS = re.compile(r"\[([A-Z]\d{2}[A-Za-z0-9.+]{0,4})\]")
# Les 5 CRH dont le corps contient des codes (inventaire §1.6) : chargés tels quels, signalés « à corriger ».
A_CORRIGER = {"HEMATOLOGIE-CLINIQUE-00049", "HEMATOLOGIE-CLINIQUE-00072", "HEMATOLOGIE-CLINIQUE-00105",
              "MEDECINE-GERIATRIQUE-00038", "MEDECINE-GERIATRIQUE-00192"}
MOTIF_A_CORRIGER = "codes CIM-10 entre crochets dans le corps du texte (inventaire §1.6) ; à corriger avec la page d'édition"


def nettoyer(texte: str, pid: str, typ: str, index: int) -> tuple[str, list[dict]]:
    """Applique A, B et C au texte d'origine d'un document. Retourne le texte conservé et les retraits."""
    retraits = []
    debut = None
    regle = None
    for nom, r in (("A", REGLE_A), ("B", REGLE_B)):
        m = r.search(texte)
        if m and (debut is None or m.start() < debut):
            debut, regle = m.start(), nom
    if (pid, typ) in CAS_C:
        ancre, motif = CAS_C[(pid, typ)]
        pos_ancre = texte.find(ancre)
        m = motif.search(texte, pos_ancre) if pos_ancre >= 0 else None
        if m and (debut is None or m.start() < debut):
            debut, regle = m.start(), "C"
    if debut is not None:
        debut = len(texte[:debut].rstrip())  # on retire aussi les blancs qui précèdent le bloc
        retraits.append({"document": index, "type": typ, "regle": regle, "debut": debut, "fin": len(texte),
                         "texte": texte[debut:]})
        texte = texte[:debut]
    return texte, retraits


def normaliser(texte: str, compteurs: Counter) -> str:
    """Normalisation du §2 de SCHEMA.md ; les compteurs comptent les caractères concernés."""
    nfc = unicodedata.normalize("NFC", texte)
    compteurs["nfc"] += len(texte) - len(nfc)
    texte = nfc
    for car, cle in (("​", "u200b"), ("﻿", "ufeff"), ("­", "u00ad")):
        compteurs[cle] += texte.count(car)
        texte = texte.replace(car, "")
    for car, cle in ((" ", "u00a0"), (" ", "u202f")):
        compteurs[cle] += texte.count(car)
        texte = texte.replace(car, " ")
    sans_blancs = texte.rstrip()
    compteurs["blancs_fin"] += len(texte) - len(sans_blancs)
    return sans_blancs


def espaces(valeur):
    """Valeur brute de type_of_care avec les espaces normalisés ; None si absente."""
    if not valeur:
        return None
    v = re.sub(r"\s+", " ", valeur.replace(" ", " ").replace(" ", " ")).strip()
    return v or None


def preparer_patient(p: dict, codes_vus: Counter) -> dict:
    docs = p["documents"]
    plusieurs = len(docs) > 1
    morceaux, limites, retraits = [], [], []
    compteurs = Counter()
    position = 0
    for i, d in enumerate(docs, 1):
        origine = (TEXTES / d["path"]).read_text(encoding="utf-8")
        texte, r = nettoyer(origine, p["id"], d["type"], i)
        retraits.extend(r)
        texte = normaliser(texte, compteurs)
        intitule = INTITULES[d["type"]] if plusieurs else None
        segment = (("\n\n" if morceaux else "") + intitule + "\n\n" + texte) if plusieurs else texte
        debut_segment = position + (2 if morceaux else 0)
        debut_texte = debut_segment + (len(intitule) + 2 if plusieurs else 0)
        morceaux.append(segment)
        position += len(segment)
        limites.append({"index": i, "type": d["type"], "titre": d["header"], "chemin": d["path"],
                        "intitule": intitule, "debut": debut_segment, "debut_texte": debut_texte, "fin": position})
    texte_final = "".join(morceaux)
    for lim in limites:  # contrôle : les positions retombent bien sur le texte
        assert texte_final[lim["debut_texte"]:lim["fin"]] == texte_final[lim["debut_texte"]:lim["fin"]].rstrip()
        if lim["intitule"]:
            assert texte_final[lim["debut"]:lim["debut"] + len(lim["intitule"])] == lim["intitule"]
    anomalies = {}
    codes_corps = CODE_CROCHETS.findall(texte_final)
    if p["id"] in A_CORRIGER:
        anomalies = {"a_corriger": True, "motif": MOTIF_A_CORRIGER, "codes": codes_corps}
    elif codes_corps:
        anomalies = {"codes_entre_crochets_inattendus": codes_corps}
    dp = p["suggested_scenario"]["primary_diagnosis"][0]
    code = dp["code"]
    assert "." not in code and " " not in code, f"{p['id']} : code DP inattendu {code!r}"
    codes_vus[(code, dp["description"])] += 1
    return {
        "lot": LOT,
        "id_source": p["id"],
        "version": 1,
        "specialite": p["specialty"],
        "type_prise_en_charge": espaces(p["suggested_scenario"].get("type_of_care")),
        "texte": texte_final,
        "nettoyage": {
            "documents_origine": limites,
            "retraits": retraits,
            "normalisations": {k: v for k, v in compteurs.items() if v},
            "anomalies": anomalies,
        },
        "codage": {
            "regle_hierarchisation": None,
            "mode_prise_en_charge": None,
            "commentaires": [],
            "ensembles": [{"code": code, "libelle": dp["description"], "categorie": "pathologie_principale",
                           "preuves": [], "confiance": None, "explication": None, "commentaires": []}],
        },
    }


def main() -> None:
    patients = json.load(open(SOURCE / "patients.json", encoding="utf-8"))["data"]
    retenus = [p for p in patients if not all(d["type"] == "ANAPATH" for d in p["documents"])]
    dossier = SORTIE / "documents"
    dossier.mkdir(parents=True, exist_ok=True)
    codes_vus = Counter()
    stats = {"retraits": Counter(), "normalisations": Counter(), "docs_normalises": Counter(), "compositions": Counter(),
             "a_corriger": [], "inattendus": [], "longueurs_car": [], "longueurs_mots": []}
    for p in retenus:
        prep = preparer_patient(p, codes_vus)
        (dossier / f"{p['id']}.json").write_text(json.dumps(prep, ensure_ascii=False, indent=1), encoding="utf-8")
        n = prep["nettoyage"]
        for r in n["retraits"]:
            stats["retraits"][r["regle"]] += 1
        for k, v in n["normalisations"].items():
            stats["normalisations"][k] += v
            stats["docs_normalises"][k] += 1  # seules les normalisations effectives figurent dans le champ
        stats["compositions"][" > ".join(d["type"] for d in n["documents_origine"])] += 1
        if n["anomalies"].get("a_corriger"):
            stats["a_corriger"].append((p["id"], n["anomalies"]["codes"]))
        if "codes_entre_crochets_inattendus" in n["anomalies"]:
            stats["inattendus"].append((p["id"], n["anomalies"]["codes_entre_crochets_inattendus"]))
        stats["longueurs_car"].append(len(prep["texte"]))
        stats["longueurs_mots"].append(len(prep["texte"].split()))

    n_docs_origine = sum(len(p["documents"]) for p in retenus)
    with open(SORTIE / "codes_dp_a_verifier.csv", "w", encoding="utf-8") as f:
        f.write("code;libelle;effectif\n")
        for (code, lib), n in sorted(codes_vus.items()):
            f.write(f"{code};{lib};{n}\n")
    lc, lm = stats["longueurs_car"], stats["longueurs_mots"]
    lignes = [
        "# Rapport de préparation de PARHAF", "",
        f"Source : `donnees/parhaf/standalone/patients.json` + textes ; lot `{LOT}` ; sortie `donnees/prepare/parhaf/documents/`.", "",
        f"- Patients lus : {len(patients)} ; patients retenus (hors anatomopathologie seule) : **{len(retenus)}** ; documents d'origine concaténés : **{n_docs_origine}**.",
        f"- Fichiers produits : {len(list(dossier.glob('*.json')))}.", "",
        "## Composition des dossiers", "",
        *[f"- {n} × {c}" for c, n in stats["compositions"].most_common()], "",
        "## Passages retirés", "",
        *[f"- règle {r} : {n} document(s)" for r, n in sorted(stats["retraits"].items())], "",
        "## Normalisations (caractères concernés ; documents concernés)", "",
        *[f"- {k} : {stats['normalisations'][k]} caractères dans {stats['docs_normalises'][k]} dossier(s)" for k in ("nfc", "u200b", "ufeff", "u00ad", "u00a0", "u202f", "blancs_fin")], "",
        "## Dossiers à corriger (codes dans le corps du texte, chargés tels quels)", "",
        *[f"- {pid} : {', '.join(c)}" for pid, c in stats["a_corriger"]], "",
        f"Dossiers avec des codes entre crochets non attendus : {len(stats['inattendus'])} {stats['inattendus'][:5]}", "",
        "## Longueur des textes préparés", "",
        f"- caractères : min {min(lc)}, médiane {median(lc):.0f}, max {max(lc)}",
        f"- mots : min {min(lm)}, médiane {median(lm):.0f}, max {max(lm)}", "",
        "## Codage initial", "",
        f"- un ensemble `pathologie_principale` par dossier ; {len({c for c, _ in codes_vus})} codes DP distincts, {len(codes_vus)} couples code + libellé distincts ; aucun code avec point ou espace (vérifié par le script).",
        f"- liste à vérifier lors du chargement de l'index (lot B3) : `codes_dp_a_verifier.csv`.",
    ]
    (SORTIE / "rapport.md").write_text("\n".join(lignes) + "\n", encoding="utf-8")
    print("\n".join(lignes))


if __name__ == "__main__":
    main()
