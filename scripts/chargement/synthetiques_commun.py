"""Fonctions partagées par les scripts de chargement des CRH synthétiques (lot B2).

Reprises des scripts d'exploration 09, 12, 13 et 14 : lecture et réparation du JSON `report`, normalisation des codes,
rattachement des clés du JSON aux codes du scénario (SCHEMA.md §3.8), recherche tolérante des citations.
"""
import json
import re
import unicodedata
from pathlib import Path

RACINE = Path(__file__).resolve().parents[2]
SOURCE = RACINE / "donnees" / "synthetiques" / "run08_scenarios_reports_merged_20261007_160916.parquet"
PREPARE = RACINE / "donnees" / "prepare" / "synthetiques"
LOT = "synthetiques-run08-e500"
CODE_FIN = re.compile(r"\(([A-Z]\d{2}[A-Za-z0-9.+]{0,5})\)\s*$")


# ---------------------------------------------------------------- JSON `report`
def lire_report(brut: str):
    """Analyse le JSON de `report`, avec les trois réparations simples de l'exploration (§2.3 de l'inventaire).
    Retourne (objet, réparation) ou (None, raison)."""
    essais = (("aucune", brut), ("accolade ajoutée", brut.rstrip() + "}"), ("accolade retirée", brut.rstrip()[:-1]),
              ("clôture ``` retirée", re.sub(r"\s*```\s*$", "", brut.rstrip())))
    for nom, texte in essais:
        try:
            obj = json.loads(texte, strict=False)
            if isinstance(obj, dict) and isinstance(obj.get("CR"), str):
                return obj, nom
        except json.JSONDecodeError:
            continue
    return None, "JSON non réparable simplement"


# ---------------------------------------------------------------- codes
def normaliser_code(c: str) -> str:
    """Forme codeur : majuscules, sans point ni espace, extension « + » conservée."""
    return re.sub(r"[^A-Z0-9+]", "", (c or "").upper().replace(".", ""))


def racine(c: str) -> str:
    """Code sans extension PMSI : « K635+0 » -> « K635 »."""
    return normaliser_code(c).split("+")[0]


def code_de_cle(cle: str):
    """Le code d'une clé « libellé (CODE) » de formulations.diagnostics, normalisé ; None si absent."""
    m = CODE_FIN.search(cle)
    return normaliser_code(m.group(1)) if m else None


def rattacher(code_json: str, codes_scenario: list[str]):
    """SCHEMA.md §3.8 : rattache une clé du JSON à un code du scénario : égalité, puis extension ignorée,
    puis le code du scénario qui commence par la clé. Retourne le code du scénario (forme complète) ou None."""
    if code_json in codes_scenario:
        return code_json
    r = racine(code_json)
    for s in codes_scenario:
        if racine(s) == r:
            return s
    for s in codes_scenario:
        if racine(s).startswith(r):
            return s
    return None


# ---------------------------------------------------------------- citations
NIVEAUX = ("identique", "casse_espaces", "accents", "markdown")


def _sans_accents(s: str) -> str:
    return "".join(ch for ch in unicodedata.normalize("NFD", s) if unicodedata.category(ch) != "Mn")


def _compacter(s: str, sans_markdown: bool = False) -> tuple[str, list[int]]:
    """Forme « casse et espaces » : minuscules, suites de blancs réduites à une espace, blancs de fin retirés ;
    avec sans_markdown, les marques * et _ sont aussi retirées. Renvoie, pour chaque caractère du résultat,
    l'index (en points de code) du caractère d'origine."""
    sortie, index = [], []
    blanc = False
    for i, ch in enumerate(s):
        if sans_markdown and ch in "*_":
            continue
        if ch.isspace():
            if not blanc and sortie:
                sortie.append(" "); index.append(i)
            blanc = True
        else:
            sortie.append(ch.lower()); index.append(i); blanc = False
    while sortie and sortie[-1] == " ":
        sortie.pop(); index.pop()
    return "".join(sortie), index


def _borne(texte: str, debut: int, fin: int) -> bool:
    """Vrai si l'occurrence est bornée par des non-lettres (mot entier)."""
    avant = texte[debut - 1] if debut > 0 else ""
    apres = texte[fin] if fin < len(texte) else ""
    return not (avant.isalnum() or apres.isalnum())


class _Formes:
    """Les formes dérivées d'un texte, calculées une fois par document."""

    def __init__(self, texte: str):
        self.texte = texte
        self.compact, self.idx = _compacter(texte)
        self.accents = _sans_accents(self.compact)
        self.md, self.idx_md = _compacter(texte, sans_markdown=True)
        self.md_accents = _sans_accents(self.md)
        self.ok_accents = len(self.accents) == len(self.compact)
        self.ok_md_accents = len(self.md_accents) == len(self.md)


def _chercher_dans(forme: str, idx: list[int], cible: str, depuis: int):
    """Cherche la cible dans une forme dérivée à partir de la position d'origine `depuis` ; retourne (debut, fin) d'origine."""
    if not cible:
        return None
    k0 = 0
    for k, orig in enumerate(idx):
        if orig >= depuis:
            k0 = k; break
    else:
        return None
    j = forme.find(cible, k0)
    if j < 0:
        return None
    return idx[j], idx[j + len(cible) - 1] + 1


def chercher_citation(texte: str, citation: str, depuis: int = 0, formes: "_Formes | None" = None):
    """Cherche la citation (points de code) : 1. identique ; 2. casse et espaces près ; 3. accents près ;
    4. marques de gras markdown (* et _) ignorées. Retourne (debut, fin, niveau) ou None.
    Les positions sont celles du texte d'origine ; la preuve prendra texte[debut:fin]."""
    if not citation or not citation.strip():
        return None
    i = texte.find(citation, depuis)
    if i >= 0:
        return i, i + len(citation), "identique"
    f = formes or _Formes(texte)
    cc, _ = _compacter(citation)
    r = _chercher_dans(f.compact, f.idx, cc, depuis)
    if r:
        return r[0], r[1], "casse_espaces"
    ca = _sans_accents(cc)
    if f.ok_accents and len(ca) == len(cc):
        r = _chercher_dans(f.accents, f.idx, ca, depuis)
        if r:
            return r[0], r[1], "accents"
    cm, _ = _compacter(citation, sans_markdown=True)
    r = _chercher_dans(f.md, f.idx_md, cm, depuis)
    if r:
        return r[0], r[1], "markdown"
    cma = _sans_accents(cm)
    if f.ok_md_accents and len(cma) == len(cm):
        r = _chercher_dans(f.md_accents, f.idx_md, cma, depuis)
        if r:
            return r[0], r[1], "markdown"
    return None


def toutes_occurrences(texte: str, citation: str, formes: "_Formes | None" = None, mot_entier: bool = True):
    """Toutes les occurrences, sans chevauchement, chacune bornée par des non-lettres si mot_entier.
    Le niveau est cherché à chaque occurrence (une citation peut être identique ici et en gras plus loin)."""
    f = formes or _Formes(texte)
    res, depuis = [], 0
    while depuis < len(texte):
        r = chercher_citation(texte, citation, depuis, f)
        if not r:
            break
        if not mot_entier or _borne(texte, r[0], r[1]):
            res.append(r); depuis = r[1]
        else:
            depuis = r[0] + 1
    return res


# ---------------------------------------------------------------- index (lu dans la base, clé secrète)
def lire_index():
    """Retourne (fiches, descendants) : fiches[code] = {libelle, codable, statut_mco} ; descendants[noeud] = [codes]."""
    import sys
    sys.path.insert(0, str(RACINE / "scripts" / "tests"))
    import psycopg
    from connexion import charger_env, url_postgres
    fiches, desc = {}, {}
    with psycopg.connect(url_postgres(charger_env())) as cx, cx.cursor() as cur:
        cur.execute("select code, libelle, codable, statut_mco from public.fiches")
        for code, lib, codable, statut in cur.fetchall():
            fiches[code] = {"libelle": lib, "codable": codable, "statut_mco": statut}
        cur.execute("select noeud, code from public.descendants_codables order by noeud, ordre_kit")
        for noeud, code in cur.fetchall():
            desc.setdefault(noeud, []).append(code)
    return fiches, desc


def classer_code(code: str, fiches: dict, desc: dict) -> str:
    """codable | affinable (codable, avec descendants plus précis) | pere_interdit | supprime | non_codable_autre | inconnu."""
    f = fiches.get(code)
    if not f:
        return "inconnu"
    if f["codable"]:
        return "affinable" if desc.get(code) else "codable"
    return {"pere_interdit": "pere_interdit", "supprime": "supprime"}.get(f["statut_mco"], "non_codable_autre")


# ---------------------------------------------------------------- éligibilité (règle du 22 octobre 2026, docs/chargement.md §3.1)
NON_CODABLES = ("pere_interdit", "supprime", "inconnu", "non_codable_autre")


def codes_scenario(dp, das_l, z) -> list[str]:
    """DP, DAS, puis le code Z de case_management_type s'il y en a un (forme codeur)."""
    return [normaliser_code(dp)] + [normaliser_code(d) for d in das_l] + ([normaliser_code(z)] if z and z != "DP" else [])


def motifs_exclusion(rep: str, dp, das_l, z, fiches: dict, desc: dict):
    """Les motifs qui écartent une ligne du tirage (vide si la ligne est propre). Retourne (motifs, obj_json)."""
    raisons = set()
    obj, _ = lire_report(rep)
    diags = (obj or {}).get("formulations", {}).get("diagnostics") if obj else None
    if not isinstance(diags, dict):
        raisons.add("JSON non réparable")
    scen = codes_scenario(dp, das_l, z)
    if any(classer_code(c, fiches, desc) in NON_CODABLES for c in scen):
        raisons.add("code du scénario non codable ou inconnu")
    if isinstance(diags, dict):
        for cle in diags:
            cj = code_de_cle(cle)
            if not cj:
                raisons.add("clé du JSON sans code reconnu")
            elif rattacher(cj, scen) is None:
                raisons.add("code ajouté par le générateur (clé non rattachée)")
    return raisons, obj


def affinables(dp, das_l, z, fiches: dict, desc: dict) -> list[str]:
    """Les codes du scénario qui ont des descendants codables plus précis."""
    return [c for c in codes_scenario(dp, das_l, z) if classer_code(c, fiches, desc) == "affinable"]


# ---------------------------------------------------------------- nettoyage du texte (étape 4)
# Règle D : une ligne-titre « Dictionnaire(s) des formulations » (en gras ou en titre markdown, avec ou sans « : »),
# et tout ce qui suit jusqu'à la fin ; la ligne « --- » qui la précède immédiatement et les blancs avant le bloc en font partie.
REGLE_D = re.compile(r"^[ \t]*(\*\*|#+ ?)?\s*dictionnaires? des formulations.*$", re.I | re.M)
SEPARATEUR_FIN = re.compile(r"(?:\r?\n)[ \t]*-{3,}[ \t]*$")
# Règle E : un code CIM-10 entre parenthèses ou crochets dans le corps du texte, retiré seul avec l'espace qui le précède.
REGLE_E = re.compile(r"[ \t]*[\(\[]\s*[A-Z]\d{2}(?:\.\d{1,3}|\d{1,3})?(?:\+\d{1,2})?\s*[\)\]]")
# Contrôle final : toute forme qui ressemble à un code (lettre, deux chiffres, point ou chiffres, extension), et « CIM-10 ».
FORME_CODE = re.compile(r"(?<![A-Za-z0-9])([A-Z]\d{2}(?:\.\d{1,3}|\d{1,3})?(?:\+\d{1,2})?)(?![A-Za-z0-9])")
MENTION_CIM = re.compile(r"CIM[- ]?10", re.I)


def nettoyer(texte: str, regle_e: bool = True) -> tuple[str, list[dict]]:
    """Applique D puis E au texte d'origine (avant normalisation). Retourne (texte conservé, retraits),
    chaque retrait = {regle, debut, fin, texte} avec les positions dans le texte d'origine (points de code)."""
    retraits = []
    m = REGLE_D.search(texte)
    if m:
        debut = m.start()
        avant = texte[:debut].rstrip()
        ms = SEPARATEUR_FIN.search(avant)
        if ms:
            avant = avant[:ms.start()]
        debut = len(avant.rstrip())
        retraits.append({"regle": "D", "debut": debut, "fin": len(texte), "texte": texte[debut:]})
        texte = texte[:debut]
    if regle_e:
        morceaux, pos, sortie = [], 0, []
        for me in REGLE_E.finditer(texte):
            retraits.append({"regle": "E", "debut": me.start(), "fin": me.end(), "texte": me.group(0)})
            sortie.append(texte[pos:me.start()]); pos = me.end()
        sortie.append(texte[pos:])
        texte = "".join(sortie)
    return texte, retraits


def normaliser(texte: str, compteurs) -> str:
    """Normalisation du §2 de SCHEMA.md (identique à PARHAF) ; les compteurs comptent les caractères concernés."""
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


def restes_de_codes(texte: str) -> list[str]:
    """Contrôle final : les formes de code et mentions CIM-10 qui subsistent (à juger : J15, B12, T10… sont des faux positifs)."""
    return [m.group(1) for m in FORME_CODE.finditer(texte)] + [m.group(0) for m in MENTION_CIM.finditer(texte)]
