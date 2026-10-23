"""Tests automatiques du codage par l'IA, SANS appel réel au LLM : réponses simulées passées à web/codage.js (Node).

Cas : passage manquant ; numéro inconnu ; passage dans deux ensembles ; deux pathologies principales ; code sans
extension (Z992, codable mais affinable) ; code arrondi (M142, non codable → correction) ; code avec point (I10.0) ;
code père interdit (C50 → correction) ; JSON invalide ; compteurs entre deux versions ; message utilisateur ;
appels répétés révisés (§3.6, 23 octobre 2026) : nouveau surlignage, rien à envoyer, chevauchement, code rejeté puis
reproposé, réponse v2 avec nature, réponse v1, passage cité par plus de deux codes.

Usage : uv run python -I scripts/tests/tester_codage.py   (Node requis)
"""
import json
import subprocess
import sys
from pathlib import Path

RACINE = Path(__file__).resolve().parents[2]
RESULTATS = []

PASSAGES = [
    {"debut": 10, "fin": 21, "texte": "HTA traitée"},
    {"debut": 40, "fin": 63, "texte": "hernie inguinale droite"},
    {"debut": 80, "fin": 118, "texte": "appendicectomie dans l'enfance"},
    {"debut": 130, "fin": 160, "texte": "dépendant d'une hémodialyse"},
    {"debut": 170, "fin": 196, "texte": "arthropathie diabétique"},
]
INDEX = {
    "I10": {"codable": True, "libelle": "Hypertension essentielle (primitive)", "statut": "codable"},
    "I100": None,
    "K409": {"codable": True, "libelle": "Hernie inguinale unilatérale ou SAI, sans occlusion ni gangrène", "statut": "codable"},
    "Z992": {"codable": True, "libelle": "Dépendance envers une dialyse rénale", "statut": "codable"},
    "Z992+0": {"codable": True, "libelle": "Dépendance envers une hémodialyse (rénale)", "statut": "codable"},
    "M142": {"codable": False, "libelle": "Arthropathie diabétique", "statut": "pere_interdit"},
    "M1427": {"codable": True, "libelle": "Arthropathie diabétique - Cheville et pied", "statut": "codable"},
    "C50": {"codable": False, "libelle": "Tumeur maligne du sein", "statut": "pere_interdit"},
    "C504": {"codable": True, "libelle": "Tumeur maligne du quadrant supéro-externe du sein", "statut": "codable"},
}
INDEX = {k: v for k, v in INDEX.items() if v is not None}
DESC = {
    "Z992": [{"code": "Z992+0", "libelle": "Dépendance envers une hémodialyse (rénale)"}, {"code": "Z992+1", "libelle": "Dépendance envers une dialyse péritonéale"}],
    "M142": [{"code": "M1427", "libelle": "Arthropathie diabétique - Cheville et pied"}, {"code": "M1426", "libelle": "Arthropathie diabétique - Jambe"}],
    "C50": [{"code": "C504", "libelle": "Tumeur maligne du quadrant supéro-externe du sein"}, {"code": "C509", "libelle": "Tumeur maligne du sein, sans précision"}],
}


def node(cas: dict) -> dict:
    r = subprocess.run(["node", str(RACINE / "scripts" / "tests" / "codage_node.js")], input=json.dumps(cas), capture_output=True, text=True, check=True)
    return json.loads(r.stdout)


def controle(nom, condition, detail=""):
    RESULTATS.append(bool(condition))
    print(f"  [{'OK' if condition else 'ÉCHEC'}] {nom}" + (f" — {detail}" if detail else ""))


def reponse(ensembles, non_codes=()):
    return json.dumps({"ensembles": ensembles, "passages_non_codes": list(non_codes)}, ensure_ascii=False)


def main() -> None:
    base = {"passages": PASSAGES, "index": INDEX, "descendants": DESC}

    # 1. Réponse conforme : chaque passage présent, une PP, preuves recopiées
    r = node({**base, "reponse": reponse([
        {"code": "K409", "libelle": "Hernie", "categorie": "pathologie_principale", "passages": [2], "confiance": 0.95, "explication": "motif"},
        {"code": "I10", "libelle": "HTA", "categorie": "diagnostic_associe", "passages": [1], "confiance": 0.9, "explication": "HTA"},
        {"code": "Z992+0", "libelle": "hémodialyse", "categorie": "diagnostic_associe", "passages": [4], "confiance": 0.8, "explication": ""},
        {"code": "M1427", "libelle": "arthropathie", "categorie": "diagnostic_associe", "passages": [5], "confiance": 0.6, "explication": ""},
    ], [{"passage": 3, "raison": "antécédent ancien"}])})
    a = r["analyse"]; c = r["codage"]
    controle("réponse conforme : analyse ok, aucun manquant ni inconnu", a["ok"] and not a["anomalies"]["passagesManquants"] and not a["anomalies"]["passagesInconnus"])
    controle("preuves recopiées des passages (positions et texte)", c["ensembles"][0]["preuves"] == [PASSAGES[1]] and c["ensembles"][1]["preuves"] == [PASSAGES[0]])
    controle("libellé enregistré = libellé officiel de l'index, pas celui du modèle", c["ensembles"][0]["libelle"] == INDEX["K409"]["libelle"])
    controle("passage non codé avec position, raison et auteur ia", c["passages_non_codes"] == [{**PASSAGES[2], "raison": "antécédent ancien", "auteur": "ia"}])
    controle("une seule pathologie principale, en tête", sum(1 for e in c["ensembles"] if e["categorie"] == "pathologie_principale") == 1)

    # 2. Passage manquant
    r = node({**base, "reponse": reponse([{"code": "I10", "categorie": "diagnostic_associe", "passages": [1], "confiance": 0.9}])})
    controle("passage manquant signalé (2, 3, 4, 5)", r["analyse"]["anomalies"]["passagesManquants"] == [2, 3, 4, 5], str(r["analyse"]["anomalies"]["passagesManquants"]))
    controle("passages manquants rangés en non codés, auteur outil", all(x["auteur"] == "outil" for x in r["codage"]["passages_non_codes"]) and len(r["codage"]["passages_non_codes"]) == 4)

    # 3. Numéro inconnu
    r = node({**base, "reponse": reponse([{"code": "I10", "categorie": "diagnostic_associe", "passages": [1, 9, "x"], "confiance": 0.9}], [{"passage": 2}, {"passage": 3}, {"passage": 4}, {"passage": 5}])})
    controle("numéros inconnus ignorés et signalés", r["analyse"]["anomalies"]["passagesInconnus"] == [9, "x"] and r["analyse"]["ensembles"][0]["passages"] == [1])
    r = node({**base, "reponse": reponse([{"code": "I10", "categorie": "diagnostic_associe", "passages": [42], "confiance": 0.9}])})
    controle("ensemble sans aucun passage valide écarté", r["analyse"]["anomalies"]["ensemblesSansPassage"] == 1 and r["analyse"]["ensembles"] == [])

    # 4. Passage dans deux ensembles
    r = node({**base, "reponse": reponse([
        {"code": "I10", "categorie": "diagnostic_associe", "passages": [1, 5], "confiance": 0.9},
        {"code": "M1427", "categorie": "diagnostic_associe", "passages": [5], "confiance": 0.7}], [{"passage": 2}, {"passage": 3}, {"passage": 4}])})
    controle("passage dans deux ensembles accepté et signalé", r["analyse"]["anomalies"]["passagesMultiEnsembles"] == [5] and len(r["codage"]["ensembles"]) == 2)

    # 4 bis. Passage à la fois dans un ensemble et déclaré non codé : l'ensemble l'emporte
    r = node({**base, "reponse": reponse([{"code": "I10", "categorie": "diagnostic_associe", "passages": [1, 2, 3, 4, 5], "confiance": 0.9}], [{"passage": 2, "raison": "déjà inclus"}])})
    controle("passage dans un ensemble ET non codé : non codé écarté et signalé", r["analyse"]["anomalies"]["nonCodesRedondants"] == [2] and r["codage"]["passages_non_codes"] == [])

    # 5. Deux pathologies principales
    r = node({**base, "reponse": reponse([
        {"code": "K409", "categorie": "pathologie_principale", "passages": [2], "confiance": 0.6},
        {"code": "I10", "categorie": "pathologie_principale", "passages": [1], "confiance": 0.9}], [{"passage": 3}, {"passage": 4}, {"passage": 5}])})
    cats = {e["code"]: e["categorie"] for e in r["codage"]["ensembles"]}
    controle("deux PP : la plus confiante gardée (I10), l'autre en diagnostic associé, signalé",
             cats == {"K409": "diagnostic_associe", "I10": "pathologie_principale"} and r["analyse"]["anomalies"]["pathologiesPrincipalesMultiples"] == ["I10", "K409"])
    r = node({**base, "reponse": reponse([{"code": "I10", "categorie": "diagnostic_associe", "passages": [1, 2, 3, 4, 5], "confiance": 0.9}])})
    controle("aucune pathologie principale : accepté", r["analyse"]["ok"] and all(e["categorie"] == "diagnostic_associe" for e in r["codage"]["ensembles"]))

    # 6. Code sans extension : codable mais affinable (option B)
    r = node({**base, "reponse": reponse([{"code": "Z992", "categorie": "diagnostic_associe", "passages": [4], "confiance": 0.8}], [{"passage": 1}, {"passage": 2}, {"passage": 3}, {"passage": 5}])})
    e = r["codage"]["ensembles"][0]
    controle("Z992 : enregistré tel quel, signalé « code plus précis possible »", e["code"] == "Z992" and r["statuts"][0][2] is True and any("plus précis" in x["texte"] for x in e["commentaires"]), str(e["commentaires"]))

    # 7. Code arrondi M142 (père interdit) : boucle de correction, puis code corrigé
    cas = {**base, "reponse": reponse([{"code": "M142", "categorie": "diagnostic_associe", "passages": [5], "confiance": 0.7}], [{"passage": 1}, {"passage": 2}, {"passage": 3}, {"passage": 4}]),
           "reponseCorrection": json.dumps({"corrections": {"M142": "M1427"}})}
    r = node(cas)
    controle("M142 : message de correction contient ses descendants codables", "M1427" in r["messageCorrection"] and "M1426" in r["messageCorrection"])
    controle("M142 → M1427 après correction, commentaire de traçabilité", r["correction"]["restants"] == [] and r["codage"]["ensembles"][0]["code"] == "M1427"
             and any("M142 → M1427" in x["texte"] for x in r["codage"]["ensembles"][0]["commentaires"]))
    r = node({**cas, "reponseCorrection": json.dumps({"corrections": {"M142": "M1499"}})})
    controle("correction hors liste ignorée : code toujours à corriger, enregistré à null", r["correction"]["ignores"] == [{"code": "M142", "choisi": "M1499"}]
             and r["codage"]["ensembles"][0]["code"] is None and r["codage"]["ensembles"][0]["code_propose_non_codable"] == "M142")
    r = node({**cas, "reponseCorrection": json.dumps({"corrections": {"M142": None}})})
    controle("correction null : code à choisir (null), preuves conservées", r["codage"]["ensembles"][0]["code"] is None and r["codage"]["ensembles"][0]["preuves"] == [PASSAGES[4]])

    # 7 bis. Code inconnu sans descendant : candidats de la catégorie puis par ressemblance au libellé, titrés
    cas = {**base, "reponse": reponse([{"code": "M8590+1", "libelle": "Fracture pathologique au cours d'une tumeur maligne secondaire de l'os", "categorie": "diagnostic_associe", "passages": [5], "confiance": 0.8}],
                                      [{"passage": 1}, {"passage": 2}, {"passage": 3}, {"passage": 4}]),
           "categorie": {"M85": [{"code": "M8500", "libelle": "Dysplasie fibreuse (localisée) - Sièges multiples"}]},
           "ressemblance": {"M8590+1": [{"code": "M9070", "libelle": "Fracture osseuse au cours de maladies tumorales - Sièges multiples"}, {"code": "M8500", "libelle": "doublon"}]},
           "reponseCorrection": json.dumps({"corrections": {"M8590+1": "M9070"}})}
    INDEX["M9070"] = {"codable": True, "libelle": "Fracture osseuse au cours de maladies tumorales - Sièges multiples", "statut": "codable"}
    cas["index"] = INDEX
    r = node(cas)
    m = r["messageCorrection"]
    controle("code inconnu : message titré « catégorie » puis « ressemble à votre libellé », sans doublon",
             "Codes codables de la catégorie M85" in m and "ressemble à votre libellé" in m and m.count("M8500") == 1 and "M9070" in m)
    controle("code inconnu corrigé par un candidat de ressemblance (M9070)", r["codage"]["ensembles"][0]["code"] == "M9070")
    r = node({**cas, "reponse": reponse([{"code": "M142", "libelle": "Arthropathie diabétique", "categorie": "diagnostic_associe", "passages": [5], "confiance": 0.7}], [{"passage": 1}, {"passage": 2}, {"passage": 3}, {"passage": 4}]),
              "ressemblance": {"M142": [{"code": "M9070", "libelle": "x"}]}})
    controle("code tronqué (père interdit) : seuls ses descendants sont proposés, pas la ressemblance", "M1427" in r["messageCorrection"] and "ressemble" not in r["messageCorrection"] and "M9070" not in r["messageCorrection"])

    # 8. Code avec point
    r = node({**base, "reponse": reponse([{"code": "I10.0", "categorie": "diagnostic_associe", "passages": [1], "confiance": 0.9}], [{"passage": 2}, {"passage": 3}, {"passage": 4}, {"passage": 5}])})
    controle("I10.0 : normalisé en I100, inconnu de l'index → à corriger", r["analyse"]["ensembles"][0]["code"] == "I100" and r["statuts"][0][1] == "inconnu")
    r = node({**base, "reponse": reponse([{"code": "z99.2+0", "categorie": "diagnostic_associe", "passages": [4], "confiance": 0.9}], [{"passage": 1}, {"passage": 2}, {"passage": 3}, {"passage": 5}])})
    controle("z99.2+0 : normalisé en Z992+0, codable", r["statuts"][0][:2] == ["Z992+0", "codable"])

    # 9. C50 père interdit : correction
    r = node({**base, "reponse": reponse([{"code": "C50", "categorie": "pathologie_principale", "passages": [2], "confiance": 0.9}], [{"passage": 1}, {"passage": 3}, {"passage": 4}, {"passage": 5}]),
              "reponseCorrection": json.dumps({"corrections": {"C50": "C504"}})})
    controle("C50 → C504 après correction, reste pathologie principale", r["codage"]["ensembles"][0]["code"] == "C504" and r["codage"]["ensembles"][0]["categorie"] == "pathologie_principale")

    # 10. JSON invalide ou mal formé
    r = node({**base, "reponse": "Voici le codage : I10 pour l'HTA."})
    controle("JSON invalide : refusé avec message", r["analyse"]["ok"] is False and "JSON" in r["analyse"]["erreur"])
    r = node({**base, "reponse": json.dumps({"codes": []})})
    controle("JSON sans liste ensembles : refusé", r["analyse"]["ok"] is False)
    r = node({**base, "reponse": "```json\n" + reponse([{"code": "I10", "categorie": "diagnostic_associe", "passages": [1, 2, 3, 4, 5], "confiance": 0.9}]) + "\n```"})
    controle("JSON entouré de ``` accepté", r["analyse"]["ok"] is True)

    # 11. Compteurs
    avant = {"regle_hierarchisation": None, "mode_prise_en_charge": None, "ensembles": [
        {"code": "K409", "categorie": "pathologie_principale", "preuves": [PASSAGES[1]]},
        {"code": "I10", "categorie": "diagnostic_associe", "preuves": [PASSAGES[0]]},
        {"code": "Z992", "categorie": "diagnostic_associe", "preuves": [PASSAGES[3]]},
        {"code": "M1427", "categorie": "diagnostic_associe", "preuves": [PASSAGES[4]]},
    ]}
    apres = {"regle_hierarchisation": "T3", "mode_prise_en_charge": None, "ensembles": [
        {"code": "K409", "categorie": "pathologie_principale", "preuves": [PASSAGES[1]]},                      # conservé
        {"code": "I10", "categorie": "diagnostic_associe", "preuves": [PASSAGES[0], {"debut": 300, "fin": 310, "texte": "Losartan"}]},  # preuves modifiées
        {"code": "Z992+0", "categorie": "diagnostic_associe", "preuves": [PASSAGES[3]]},                     # modifié
        {"code": "E1198", "categorie": "diagnostic_associe", "preuves": [PASSAGES[2]]},                       # ajouté
        {"code": "R51", "categorie": "diagnostic_associe", "preuves": []},                                     # incertain (sans preuve)
    ]}
    r = node({"passages": PASSAGES, "index": INDEX, "descendants": DESC, "compteursSeuls": {"avant": avant, "apres": apres}})
    attendu = {"conserves": 1, "modifies": 1, "preuves_modifiees": 1, "retires": 1, "ajoutes": 1, "incertains": 1, "regle_modifiee": True, "mode_prise_en_charge_modifie": False}
    controle("compteurs §3.7 : conservé, modifié, preuves modifiées, retiré, ajouté, incertain, règle modifiée", r["compteurs"] == attendu, str(r["compteurs"]))
    r = node({"passages": PASSAGES, "index": INDEX, "descendants": DESC, "compteursSeuls": {"avant": None, "apres": avant}})
    controle("compteurs sans ligne précédente : tout ajouté", r["compteurs"]["ajoutes"] == 4 and r["compteurs"]["retires"] == 0)
    # Cas réel du 22 octobre : C795 et un code à choisir partagent la même preuve ; la revue remplace le code à choisir par M907.
    preuve = {"debut": 3005, "fin": 3113, "texte": "…"}
    av = {"regle_hierarchisation": None, "mode_prise_en_charge": None, "ensembles": [
        {"code": "C795", "categorie": "diagnostic_associe", "preuves": [preuve]},
        {"code": None, "categorie": "diagnostic_associe", "preuves": [preuve], "code_propose_non_codable": "M8590+1"}]}
    ap = {"regle_hierarchisation": None, "mode_prise_en_charge": None, "ensembles": [
        {"code": "C795", "categorie": "diagnostic_associe", "preuves": [preuve]},
        {"code": "M907", "categorie": "diagnostic_associe", "preuves": [preuve]}]}
    r = node({"passages": PASSAGES, "index": INDEX, "descendants": DESC, "compteursSeuls": {"avant": av, "apres": ap}})
    controle("appariement par même code d'abord : C795 conservé, code à choisir → M907 modifié, aucun incertain",
             r["compteurs"]["conserves"] == 1 and r["compteurs"]["modifies"] == 1 and r["compteurs"]["incertains"] == 0, str(r["compteurs"]))

    # 11 bis. Appel répété : assemblage par la page
    retenu = {"regle_hierarchisation": None, "mode_prise_en_charge": None, "commentaires": [], "passages_non_codes": [], "ensembles": [
        {"code": "K409", "libelle": "Hernie", "categorie": "pathologie_principale", "preuves": [PASSAGES[1]], "confiance": None, "explication": None, "commentaires": []},
        {"code": "I10", "libelle": "HTA", "categorie": "diagnostic_associe", "preuves": [PASSAGES[0]], "confiance": None, "explication": None, "commentaires": []}]}
    nouveau = {"regle_hierarchisation": None, "mode_prise_en_charge": None, "commentaires": [], "ensembles": [
        {"code": "Z992+0", "libelle": "Hémodialyse", "categorie": "pathologie_principale", "preuves": [PASSAGES[3]], "confiance": 0.8, "explication": "", "commentaires": []},
        {"code": "I10", "libelle": "HTA", "categorie": "diagnostic_associe", "preuves": [{"debut": 300, "fin": 310, "texte": "Losartan"}], "confiance": 0.9, "explication": "", "commentaires": []},
        {"code": "E1198", "libelle": "Diabète", "categorie": "diagnostic_associe", "preuves": [], "confiance": 0.7, "explication": "", "commentaires": []}],
        "passages_non_codes": [{**PASSAGES[2], "raison": "antécédent", "auteur": "ia"}]}
    r = node({**base, "repete": {"retenu": retenu, "nouveau": nouveau}})["repete"]
    codes = [(e["code"], e["categorie"], len(e["preuves"])) for e in r["codage"]["ensembles"]]
    controle("appel répété : codes retenus inchangés, nouveau code ajouté en associé (PP déjà prise), preuve ajoutée à I10, proposition sans preuve écartée",
             codes == [("K409", "pathologie_principale", 1), ("I10", "diagnostic_associe", 2), ("Z992+0", "diagnostic_associe", 1)] and r["ecartes"] == ["E1198"] and len(r["codage"]["passages_non_codes"]) == 1, str(codes))
    i10 = r["codage"]["ensembles"][1]
    controle("preuve ajoutée par l'IA à un code retenu : commentaire outil visible et code signalé",
             any("ajouté aux preuves par l'IA lors d'un appel répété" in k["texte"] and k["auteur"] == "outil" for k in i10["commentaires"]) and r["completes"] == ["I10"])
    # Préparation : chevauchement -> complète le code sans envoi ; sinon envoyé
    prep = node({**base, "preparer": {"courant": retenu, "passages": [{"debut": 45, "fin": 70, "texte": "inguinale droite depuis"}, PASSAGES[3]]}})["preparer"]
    controle("préparation d'un appel répété : le passage chevauchant complète K409 (modification du codeur, non envoyée), l'autre est envoyé",
             [p["debut"] for p in prep["aEnvoyer"]] == [PASSAGES[3]["debut"]] and prep["completes"] == ["K409"] and prep["modifie"] is True and len(prep["courant"]["ensembles"][0]["preuves"]) == 2)

    # 13. Appels répétés révisés (SCHEMA.md §3.6, 23 octobre 2026) et prompt v2
    E1198 = {"codable": True, "libelle": "Diabète sucré de type 2, sans complication", "statut": "codable"}
    index2 = {**INDEX, "E1198": E1198}
    existant = {"regle_hierarchisation": None, "mode_prise_en_charge": None, "commentaires": [], "passages_non_codes": [], "codes_rejetes": [], "ensembles": [
        {"code": "K409", "libelle": "Hernie", "categorie": "pathologie_principale", "preuves": [PASSAGES[1]], "confiance": 0.9, "explication": "x", "commentaires": []},
        {"code": "I10", "libelle": "HTA", "categorie": "diagnostic_associe", "preuves": [PASSAGES[0]], "confiance": 0.9, "explication": "x", "commentaires": []}]}
    nouveau_passage = {"debut": 300, "fin": 320, "texte": "diabète de type 2"}
    # a. relance après un nouveau surlignage : seul le nouveau passage part, tous les codes restent (le défaut constaté)
    rep_v2 = reponse([{"code": "E1198", "categorie": "diagnostic_associe", "passages": [{"numero": 1, "preuve": "directe"}], "confiance": 0.8}])
    r = node({"passages": PASSAGES, "index": index2, "descendants": DESC, "preparer": {"courant": existant, "passages": [PASSAGES[0], PASSAGES[1], nouveau_passage], "reponse": rep_v2}})["preparer"]
    codes = [e["code"] for e in r["assemblage"]["codage"]["ensembles"]]
    controle("relance après un nouveau surlignage : un seul passage envoyé, les deux codes conservés, le nouveau code ajouté",
             [p["debut"] for p in r["aEnvoyer"]] == [300] and codes == ["K409", "I10", "E1198"] and r["modifie"] is False, str(codes))
    controle("message de l'appel répété : codage existant en lecture seule avec le texte des preuves", "CODAGE EXISTANT" in r["message"] and "preuve : « HTA traitée »" in r["message"] and "K409 — Hernie (pathologie principale" in r["message"])
    # b. relance sans nouveau passage : rien à envoyer, pas d'appel
    r = node({"passages": PASSAGES, "index": index2, "descendants": DESC, "preparer": {"courant": existant, "passages": [PASSAGES[0], PASSAGES[1]]}})["preparer"]
    controle("relance sans nouveau passage : aucun passage à envoyer (la page n'appelle pas le modèle)", r["aEnvoyer"] == [] and r["modifie"] is False)
    # c. nouveau surlignage qui chevauche une preuve : rattaché au code, signalé, non envoyé
    r = node({"passages": PASSAGES, "index": index2, "descendants": DESC, "preparer": {"courant": existant, "passages": [{"debut": 45, "fin": 70, "texte": "inguinale droite depuis"}]}})["preparer"]
    controle("surlignage chevauchant une preuve : ajouté aux preuves de K409 (signalé), rien n'est envoyé",
             r["aEnvoyer"] == [] and r["completes"] == ["K409"] and r["modifie"] is True and len(r["courant"]["ensembles"][0]["preuves"]) == 2)
    # d. code supprimé puis relance : ses passages renvoyés avec la consigne ; code reproposé signalé
    rejete = {**existant, "ensembles": existant["ensembles"][:1], "codes_rejetes": [{"code": "I10", "libelle": "HTA", "categorie": "diagnostic_associe", "preuves": [PASSAGES[0]], "etape": "revue_humain"}]}
    rep_i10 = reponse([{"code": "I10", "categorie": "diagnostic_associe", "passages": [{"numero": 1, "preuve": "directe"}], "confiance": 0.9}])
    r = node({"passages": PASSAGES, "index": index2, "descendants": DESC, "preparer": {"courant": rejete, "passages": [PASSAGES[0], PASSAGES[1]], "reponse": rep_i10}})["preparer"]
    controle("code supprimé puis relance : son passage est renvoyé et le modèle reçoit la consigne « ne le repropose pas »",
             [p["debut"] for p in r["aEnvoyer"]] == [10] and r["rejetes"] == [{"code": "I10", "libelle": "HTA", "passages": [1]}] and "le codeur a rejeté le code I10 (HTA) pour le passage n° 1 : ne le repropose pas" in r["message"])
    i10 = r["assemblage"]["codage"]["ensembles"][-1]
    controle("code rejeté reproposé par l'IA : gardé mais signalé (commentaire outil « déjà rejeté par vous »), liste des rejets conservée",
             i10["code"] == "I10" and any("déjà rejeté par vous" in k["texte"] for k in i10["commentaires"]) and r["assemblage"]["reproposes"] == ["I10"] and len(r["assemblage"]["codage"]["codes_rejetes"]) == 1)
    r = node({"passages": PASSAGES, "index": index2, "descendants": DESC, "preparer": {"courant": rejete, "passages": [PASSAGES[1]]}})["preparer"]
    controle("code supprimé et surlignage retiré : rien n'est renvoyé, aucune consigne", r["aEnvoyer"] == [] and r["rejetes"] == [])
    # e. réponse v2 avec nature des preuves ; f. réponse au format v1
    r = node({**base, "index": index2, "reponse": reponse([{"code": "I10", "categorie": "diagnostic_associe", "passages": [{"numero": 1, "preuve": "directe"}, {"numero": 4, "preuve": "indirecte"}], "confiance": 0.9}], [{"passage": 2}, {"passage": 3}, {"passage": 5}])})
    natures = [p.get("nature") for p in r["codage"]["ensembles"][0]["preuves"]]
    controle("réponse v2 : nature recopiée sur chaque preuve (directe, indirecte)", natures == ["directe", "indirecte"], str(natures))
    r = node({**base, "reponse": reponse([{"code": "I10", "categorie": "diagnostic_associe", "passages": [1, 4], "confiance": 0.9}], [{"passage": 2}, {"passage": 3}, {"passage": 5}])})
    controle("réponse au format v1 (numéros) : acceptée, preuves sans nature", r["analyse"]["ok"] is True and all("nature" not in p for p in r["codage"]["ensembles"][0]["preuves"]))
    r = node({**base, "reponse": reponse([{"code": "I10", "categorie": "diagnostic_associe", "passages": [{"numero": 1, "preuve": "peut-être"}, {"numero": 9}], "confiance": 0.9}], [{"passage": 2}, {"passage": 3}, {"passage": 4}, {"passage": 5}])})
    controle("nature inconnue ignorée, numéro inconnu dans un objet signalé", "nature" not in r["codage"]["ensembles"][0]["preuves"][0] and r["analyse"]["anomalies"]["passagesInconnus"] == [9])
    # g. passage cité par plus de deux codes : signalé sur chaque code concerné, rien refusé
    r = node({**base, "index": index2, "reponse": reponse([
        {"code": "I10", "categorie": "diagnostic_associe", "passages": [{"numero": 1, "preuve": "directe"}], "confiance": 0.9},
        {"code": "K409", "categorie": "pathologie_principale", "passages": [{"numero": 1, "preuve": "indirecte"}, {"numero": 2, "preuve": "directe"}], "confiance": 0.9},
        {"code": "E1198", "categorie": "diagnostic_associe", "passages": [{"numero": 1, "preuve": "indirecte"}], "confiance": 0.6}], [{"passage": 3}, {"passage": 4}, {"passage": 5}])})
    ens = r["codage"]["ensembles"]
    controle("passage cité par trois codes : anomalie relevée, commentaire outil sur les trois codes, aucun code refusé",
             r["analyse"]["anomalies"]["passagesTropCites"] == [{"passage": 1, "nb": 3}] and len(ens) == 3
             and all(any("cité par 3 codes" in k["texte"] and k["auteur"] == "outil" for k in e["commentaires"]) for e in ens))
    r = node({**base, "reponse": reponse([{"code": "I10", "categorie": "diagnostic_associe", "passages": [1], "confiance": 0.9}, {"code": "K409", "categorie": "pathologie_principale", "passages": [1, 2], "confiance": 0.9}], [{"passage": 3}, {"passage": 4}, {"passage": 5}])})
    controle("passage cité par deux codes seulement : pas de garde-fou", r["analyse"]["anomalies"]["passagesTropCites"] == [] and not any("cité par" in k["texte"] for e in r["codage"]["ensembles"] for k in e["commentaires"]))

    # 12. Message utilisateur
    r = node({"passages": PASSAGES[:2], "index": INDEX, "descendants": DESC, "message": {"texte": "Texte du CRH.", "contexte": {"codesRetenus": [{"code": "I10", "libelle": "Hypertension essentielle (primitive)", "categorie": "pathologie_principale"}]}}})
    controle("message utilisateur : texte, passages numérotés, codes déjà retenus", "1. « HTA traitée »" in r["message"] and "2. « hernie inguinale droite »" in r["message"] and "I10 — Hypertension" in r["message"] and "déjà désignée" in r["message"])

    ok, total = sum(RESULTATS), len(RESULTATS)
    print(f"\nBILAN : {ok} contrôles réussis sur {total}")
    sys.exit(0 if ok == total else 1)


if __name__ == "__main__":
    main()
