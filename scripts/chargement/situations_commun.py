"""Lecture du guide des situations cliniques (brief 8, étape 3) : du tableau CSV à la version lue par la machine.

Conventions du tableau (docs/referentiels/situations_cliniques/README.md) : l'espace sépare une liste (`Z43 Z44`), le tiret
marque un intervalle (`Z80-Z99`), « chapitres I à XVII » désigne des chapitres, « Aucun » signifie aucune exigence, « Aucun Z42 »
se lit « Aucun ou Z42 », un nom de liste renvoie à `listes_codes`. Décisions du 23 octobre 2026 : D6 ← liste
icd_codes_chronic_attack ; T1 chargée telle quelle avec la mention « liste à compléter » ; T10-irradiations non évaluable ;
IVG et ITG (règle officielle IMG) sans étiquette dans le guide.
"""
import csv
import re
import sys
from pathlib import Path

RACINE = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(RACINE / "scripts" / "chargement"))
from synthetiques_commun import lire_index  # noqa: E402

GUIDE = RACINE / "docs" / "referentiels" / "situations_cliniques" / "guide_situations_cliniques.csv"
EXTRAITS = RACINE / "docs" / "referentiels" / "situations_cliniques" / "extraits_guide_methodologique_2026.csv"
CHAPITRES = RACINE / "docs" / "referentiels" / "cim" / "chapitres.csv"
VERSION = "1 (23 octobre 2026)"
TYPES = {"HOSPITALISATION POUR DIAGNOSTIC": "diagnostic", "HOSPITALISATION POUR TRAITEMENT": "traitement",
         "HOSPITALISATION POUR SURVEILLANCE": "surveillance", "HOSPITALISATION POUR ACCOUCHEMENT": "accouchement",
         "HOSPITALISATION D'UN NOUVEAU NE": "nouveau_ne", "HOSPITALISATION POUR IVG": "ivg", "HOSPITALISATION POUR ITG": "itg"}
LIBELLES = {"T12": "Accouchement normal", "T13": "Naissance d'un enfant séjournant en maternité avec sa mère",
            "IVG": "Interruption volontaire de grossesse", "ITG": "Interruption médicale de grossesse"}
REGLE_OFFICIELLE = {"IVG": "IVG", "ITG": "IMG"}
PATHOLOGIE_SPECIALE = {"D6": "icd_codes_chronic_attack"}   # « Code spécifique poussée aigue » → la liste des poussées aiguës
NOTES = {"T1": "liste des modes de prise en charge à compléter (décision du 23 octobre 2026)",
         "IVG": "sans étiquette dans le guide (§1.2.3, 5°)", "ITG": "sans étiquette dans le guide (§1.2.3, 6°)"}
NON_EVALUABLES = {"T10-irradiations": "fondée sur des listes d'actes CCAM (procedure_curitherapy, procedure_single_irradiation) absentes : la compatibilité ne peut pas se juger sur la pathologie principale"}
ROMAINS = ["I", "II", "III", "IV", "V", "VI", "VII", "VIII", "IX", "X", "XI", "XII", "XIII", "XIV", "XV", "XVI", "XVII", "XVIII", "XIX", "XX", "XXI", "XXII"]


def lire_chapitres():
    return list(csv.DictReader(open(CHAPITRES, encoding="utf-8")))


def lire_listes_base():
    """Les listes de codes chargées dans la base : {nom: {code: libelle}}."""
    import psycopg
    sys.path.insert(0, str(RACINE / "scripts" / "tests"))
    from connexion import charger_env, url_postgres
    listes = {}
    with psycopg.connect(url_postgres(charger_env())) as cx, cx.cursor() as cur:
        cur.execute("select liste, code, libelle from public.listes_codes")
        for l, c, lib in cur.fetchall():
            listes.setdefault(l, {})[c] = lib
    return listes


def chapitres_de(texte: str) -> list[str]:
    """« chapitres I à XVII et XIX » -> ['I', …, 'XVII', 'XIX'] ; « chapitre XVIII » -> ['XVIII']."""
    t = texte.replace("chapitres", "").replace("chapitre", "").strip()
    out = []
    for part in re.split(r"\s+et\s+|\s*,\s*", t):
        part = part.strip()
        if not part: continue
        m = re.fullmatch(r"([IVX]+)\s+à\s+([IVX]+)", part)
        if m:
            a, b = ROMAINS.index(m.group(1)), ROMAINS.index(m.group(2)); out += ROMAINS[a:b + 1]
        elif part in ROMAINS:
            out.append(part)
        else:
            raise ValueError(f"chapitre illisible : {part!r} dans {texte!r}")
    return out


def lire_pathologie(code_regle: str, brut: str) -> dict:
    brut = PATHOLOGIE_SPECIALE.get(code_regle, brut or "")
    p = {"brut": brut, "aucun": False, "chapitres": [], "intervalles": [], "codes": [], "listes": [], "actes": []}
    t = brut.strip()
    if not t:
        p["aucun"] = True; p["vide_dans_le_guide"] = True; return p
    for part in [m.strip() for m in re.split(r"\s+ou\s+", t) if m.strip()]:
        if part.lower().startswith("chapitre"):
            p["chapitres"] += chapitres_de(part)   # « chapitres I à XVII, XIX et XXII » se lit en entier
            continue
        for morceau in [m.strip() for m in part.split(",") if m.strip()]:
            if morceau.lower() == "aucun": p["aucun"] = True
            elif morceau.startswith("icd_"): p["listes"].append(morceau)
            elif morceau.startswith("procedure_"): p["actes"].append(morceau)
            else:
                for tok in morceau.split():
                    if re.fullmatch(r"[A-Z]\d{2}-[A-Z]\d{2}", tok): a, b = tok.split("-"); p["intervalles"].append([a, b])
                    elif re.fullmatch(r"[A-Z]\d{2}[A-Z0-9+]*", tok): p["codes"].append(tok)
                    else: raise ValueError(f"pathologie illisible : {tok!r} ({code_regle})")
    return p


def lire_mode(brut: str, fiches: dict, desc: dict) -> dict:
    """« Aucun Z42 » -> dp possible + catégorie Z42 ; chaque élément est résolu en codes Z codables (lui-même s'il est codable,
    plus ses descendants codables ; un intervalle Z34-Z35 donne tous les codes codables de ces catégories)."""
    m = {"brut": brut or "", "dp": False, "elements": [], "intervalles": [], "codes": []}
    vus = {}
    def ajouter(c):
        if c in fiches and fiches[c]["codable"] and c not in vus: vus[c] = fiches[c]["libelle"]
        for d in desc.get(c, []):
            if d not in vus: vus[d] = fiches[d]["libelle"]
    for tok in (brut or "").split():
        if tok.lower() == "aucun": m["dp"] = True; continue
        if re.fullmatch(r"[A-Z]\d{2}-[A-Z]\d{2}", tok):
            a, b = tok.split("-"); m["intervalles"].append([a, b])
            for c in sorted(fiches):
                if a <= c[:3] <= b and fiches[c]["codable"] and c not in vus: vus[c] = fiches[c]["libelle"]
            continue
        m["elements"].append(tok); ajouter(tok)
    m["codes"] = [{"code": c, "libelle": l} for c, l in sorted(vus.items())]
    return m


def lire_guide(fiches=None, desc=None):
    """Toutes les lignes du guide, prêtes pour regles_situations : (ligne, erreurs)."""
    if fiches is None: fiches, desc = lire_index()
    extraits = list(csv.DictReader(open(EXTRAITS, encoding="utf-8")))
    lignes = []
    for r in csv.DictReader(open(GUIDE, encoding="utf-8")):
        k = list(r.keys()); code = r[k[0]].strip(); famille = r[k[1]].strip(); spec = r[k[2]].strip(); patho = r[k[3]].strip(); mode = r[k[4]].strip()
        regle_off = REGLE_OFFICIELLE.get(code, code.split("-")[0])
        # extraits qui concernent cette ligne : propres (règle officielle, et ligne si précisée) et communs
        sections = [e["section"] for e in extraits if e["type"] == "regle" and e["regle_officielle"] == regle_off and (not e["lignes"] or code in e["lignes"].split())]
        communs = [e["section"] for e in extraits if e["type"] == "commun" and (code in e["lignes"].split() if e["lignes"] else regle_off in e["regle_officielle"].split())]
        d = {"pathologie": lire_pathologie(code, patho), "mode_prise_en_charge": lire_mode(mode, fiches, desc),
             "extrait": {"regle_officielle": regle_off, "sections": sections, "passages_communs": communs},
             "evaluable": code not in NON_EVALUABLES}
        if code in NON_EVALUABLES: d["motif_non_evaluable"] = NON_EVALUABLES[code]
        if code in NOTES: d["note"] = NOTES[code]
        if code in PATHOLOGIE_SPECIALE: d["pathologie"]["note"] = f"« {patho} » dans le tableau : liste {PATHOLOGIE_SPECIALE[code]} (décision du 23 octobre 2026)"
        lignes.append({"code": code, "famille": famille, "libelle": spec or LIBELLES.get(code, code), "type": TYPES.get(famille),
                       "specificite": spec or None, "pathologie": patho or None, "code_z": mode or None, "details": d,
                       "version": VERSION, "regle_officielle": regle_off, "evaluable": code not in NON_EVALUABLES})
    return lignes, extraits
