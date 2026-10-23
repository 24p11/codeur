"""Brief 8, étape 2 : extraits officiels du guide méthodologique MCO 2026 (chapitre VI, chapitre IV §1.1), mot pour mot.

Lit le PDF docs/referentiels/atih/guide_methodologique_mco_2026_provisoire.pdf (pdftotext -layout), découpe chaque extrait
entre un repère de début et un repère de fin (inclus), et répare seulement les coupures de l'extraction : numéros de page,
appels et textes des notes de bas de page, retours à la ligne au milieu des paragraphes, césures, lettres espacées.
Écrit docs/referentiels/situations_cliniques/extraits_guide_methodologique_2026.csv
(colonnes : regle_officielle, section, page, extrait, note) et affiche la longueur de chaque extrait.

Usage : uv run python -I scripts/referentiels/extraire_guide.py
"""
import csv
import re
import subprocess
from pathlib import Path

RACINE = Path(__file__).resolve().parents[2]
PDF = RACINE / "docs" / "referentiels" / "atih" / "guide_methodologique_mco_2026_provisoire.pdf"
SORTIE = RACINE / "docs" / "referentiels" / "situations_cliniques" / "extraits_guide_methodologique_2026.csv"
DECALAGE = 8  # page imprimée = page du PDF - 8 (la page 130 du PDF porte le numéro 122)

# Lettres espacées par l'extraction (corrigées à l'identique, signalées dans la note de l'extrait)
REPARATIONS = [
    ("n o n pris en charge", "non pris en charge"),
    ("L e DP du séjour d’IVG est codé avec la catégorie O04 de la CIM–10 int er r upt ion\nm édicale volont air e de gr ossesse", "Le DP du séjour d’IVG est codé avec la catégorie O04 de la CIM–10 interruption médicale volontaire de grossesse"),
    ("n’est pa s « le", "n’est pas « le"),
    ("classification TNM5)", "classification TNM)"),  # appel de note 5 collé au sigle
    ("tests allergologiques 80.", "tests allergologiques."),  # appel de note mal extrait
]

# Deux sortes d'extraits (relecture de Rémi, 23 octobre 2026) : l'extrait propre à une règle (type « regle » : le paragraphe de
# son étiquette et ses exemples) et le passage commun (type « commun » : un passage qui vaut pour plusieurs règles, rangé une seule
# fois avec la liste des règles qu'il concerne) ; plus les préambules (type « preambule »).
# Champs : type, règle officielle (vide pour un passage commun, un préambule, l'IVG et l'IMG), règles ou lignes du tableau concernées
# (le troisième champ ; pour un extrait propre, la ligne du tableau quand l'extrait ne vaut pas pour toute la règle officielle), section,
# pages PDF (début, fin), repère de début (regex), repère de fin (regex, inclus), note, suffixe éventuel (note du guide).
NOTE_16 = "Note du guide : La plupart des séjours pour intervention plastique réparatrice des séquelles d’une lésion traumatique ou d’une perte de substance postopératoire font en effet appel à la catégorie Z42 pour le codage du DP. Le DR peut être un code Z s’il correspond, tel Z90.1, à un « état permanent » (se reporter au point 1)."
EXTRAITS = [
    # --- préambules
    ("preambule", "", "", "IV §1.1", (71, 72), r"Le diagnostic principal \(DP\) du RUM est le problème", r"\(anatomopathologie,\s*virologie\.\.\.\)\.", "Définition du diagnostic principal (chapitre IV, §1.1), jusqu'à la fin du §1.1. « chapitre 0 » (renvoi au guide des situations cliniques) est tel quel dans la version provisoire."),
    ("preambule", "", "", "VI §1.5", (148, 148), r"EN CONCLUSION : le diagnostic principal", r"la situation de diagnostic\)\.", "Conclusion du chapitre VI : les trois situations cliniques."),
    # --- passages communs
    ("commun", "", "D1 D2 D3 D4 D5 D6 D7 D8 D9", "VI §1.1", (130, 130), r"1\.1\. HOSPITALISATION POUR DIAGNOSTIC", r"la règle est\s*la même\.", "Introduction du §1.1 : la situation de diagnostic."),
    ("commun", "", "D1 D2", "VI §1.1.3", (132, 132), r"La situation clinique de diagnostic est ainsi caractérisée", r"– hospitalisation pour état de choc ; décès précoce sans diagnostic\s*étiologique ; DP : état de choc\.", "Résumé de la situation de diagnostic, placé à la fin du §1.1.3 (après D4)."),
    ("commun", "", "D5 D6 D7 D8", "VI §1.1.4", (133, 133), r"1\.1\.4\. Situations équivalentes", r"aboutissant à l’un des diagnostics suivants\.", "Introduction du §1.1.4 : situations équivalentes chez un patient atteint d'une maladie chronique."),
    ("commun", "", "D5 D7 D8", "VI §1.1.4", (134, 134), r"Ces trois situations sont conformes à la règle D1", r"la complication ou l’affection intercurrente\.", "Dernier paragraphe du 3° (après D8)."),
    ("commun", "", "D1 D5 D9 T9 SD2", "VI §1.4", (147, 147), r"Il résulte de ce qui vient d’être exposé qu’une maladie chronique", r"– décès éventuellement\s*\.", "Encadré du §1.4 : les seules circonstances où une maladie chronique peut être le DP."),
    ("commun", "", "T1 T2 T3 T4 T5 T6 T7 T8 T9 T10 T11 T12 T13 T14 T15", "VI §1.2", (135, 135), r"1\.2\. HOSPITALISATION POUR TRAITEMENT", r"comprend le traitement répétitif et le traitement unique\.", "Introduction du §1.2 : la situation de traitement."),
    ("commun", "", "T3 T4 T5 T6 T7 T8 T9 T10 T11 T14 T15", "VI §1.2.2", (137, 137), r"1\.2\.2\. Traitement unique", r"chirurgical, « interventionnel » ou médical\.", "Introduction du §1.2.2 : le traitement unique."),
    ("commun", "", "T4 T5 T6 T7 T14 T15", "VI §1.2.2.1", (137, 137), r"•\s+Cas particuliers\s*\n\s*Certaines situations de traitement unique chirurgical", r"l’un des suivants\.", "Introduction des cas particuliers du traitement unique chirurgical (catégories Z40 à Z52)."),
    ("commun", "", "T9-initiation-tt-chronic T9-diabetes T12 T13 IVG ITG", "VI §1.2.3", (141, 141), r"1\.2\.3\. Situations équivalentes \(au traitement unique\)", r"les circonstances suivantes :", "Introduction du §1.2.3 : situations équivalentes au traitement unique (lignes du tableau)."),
    ("commun", "", "T10 T11", "VI §1.2.2.3", (141, 141), r"•\s+Cas particuliers\s*\n\s*Il existe des exceptions :", r"la maladie traitée est\s*enregistrée comme DR chaque fois qu’elle respecte sa définition\.", "Les exceptions au traitement unique médical : le passage porte les étiquettes T10 (deux fois) et T11 ; rangé une seule fois, il est le seul extrait de ces deux règles."),
    ("commun", "", "S1 S2 S3 S4 SD1 SD2", "VI §1.3", (143, 143), r"1\.3\. HOSPITALISATION POUR SURVEILLANCE", r"la surveillance négative et la surveillance\s*positive\.", "Introduction du §1.3 : la situation de surveillance."),
    ("commun", "", "S1 S2 S3", "VI §1.3.1", (144, 144), r"Dans une situation de surveillance négative l’affection surveillée", r"les kystes rénaux sont\s*un DAS\.", "Paragraphes du §1.3.1 qui suivent S3 : l'affection surveillée en DR, l'affection sans rapport découverte incidemment."),
    ("commun", "", "S1 S2 S3 S4 SD1 SD2", "VI §1.3.3", (145, 145), r"Il résulte de la définition de la situation de surveillance", r"\(point 1\.2\.3 – 2° chapitre IV\)\.", "Dernier paragraphe du §1.3.3 (après SD2) : la modification du traitement ne transforme pas une surveillance en traitement."),
    ("commun", "", "D9 S1 SD1 SD2", "VI §1.3.4", (145, 146), r"1\.3\.4\. Remarque à propos de la notion de « bilan »", r"Ce diagnostic est de la compétence du\s*médecin qui dispense les soins\.", "Remarque sur le mot « bilan »."),
    # --- extraits propres à chaque règle
    ("regle", "D1", "D1", "VI §1.1.1", (130, 130), r"1\.1\.1\. Le séjour a permis le diagnostic", r"il ne doit donc pas être\s*mentionné de DR dans le RUM\.", "Le crochet fermant de l'étiquette « [Règle D1 » manque dans le guide lui-même."),
    ("regle", "D2", "D2", "VI §1.1.2", (130, 131), r"1\.1\.2\. Il n'a pas été découvert de cause", r"en l’absence de\s*symptomatologie\.", ""),
    ("regle", "D3", "D3", "VI §1.1.3, 1° à 3°", (131, 132), r"1\.1\.3\. Cas particuliers", r"est enregistrée comme un diagnostic associé\.", "Appel de note « 80 » retiré après « tests allergologiques »."),
    ("regle", "D4", "D4", "VI §1.1.3, 4°", (132, 132), r"4\) Lors des séjours, en général programmés pour une situation d’examen", r"les codes des\s*catégories Z11 à Z13 de la CIM-10 ne doivent pas être employés\.", ""),
    ("regle", "D5", "D5", "VI §1.1.4, 1°", (133, 133), r"1°\) Poussée aigüe de la maladie chronique", r"\(voir le point 1\.3 de ce chapitre\)\.", ""),
    ("regle", "D6", "D6", "VI §1.1.4, 1°", (133, 133), r"L’affection chronique sous-jacente n’est pas le DP", r"– poussée aigüe de pancréatite chronique : K85\.– \.", ""),
    ("regle", "D7", "D7", "VI §1.1.4, 2°", (134, 134), r"2°\) Complication de la maladie chronique", r"le cancer digestif ou la prostatite\s*4?,", "Le texte se termine par une virgule dans le guide (appel de note 4 retiré)."),
    ("regle", "D8", "D8", "VI §1.1.4, 3°", (134, 134), r"3°\) Affection ou lésion intercurrente", r"DP : fracture du col du fémur\.", ""),
    ("regle", "D9", "D9", "VI §1.1.4, 4°", (134, 135), r"4°\) Par convention on considère également", r"mentionnée comme diagnostic associé significatif\s*\.", ""),
    ("regle", "T1", "T1", "VI §1.2.1", (135, 136), r"1\.2\.1\. Traitement répétitif", r"concerne en général des maladies chroniques ou de longue durée\.", ""),
    ("regle", "T2", "T2", "VI §1.2.1, cas particuliers", (136, 137), r"•\s+Cas particuliers\s*\n\s*Il existe des exceptions\s*13?\s*: \[Règle T2\]", r"Le DP n’étant pas un code Z, il ne doit pas être mentionné de DR dans le RUM\.", ""),
    ("regle", "T3", "T3", "VI §1.2.2.1", (137, 137), r"1\.2\.2\.1\. Traitement unique chirurgical", r"Dans cette situation, le DP n’étant pas un code Z, il ne doit pas être mentionné de DR\s*dans le RUM\.", ""),
    ("regle", "T4", "T4", "VI §1.2.2.1, cas particuliers 1°", (137, 138), r"1°\) Un acte de chirurgie esthétique", r"il peut l’être comme DR mais pas comme diagnostic associé\.", ""),
    ("regle", "T5", "T5", "VI §1.2.2.1, cas particuliers 2°", (138, 138), r"2°\) Un acte de chirurgie plastique non esthétique", r"DP J34\.2, pas de DR\.", "La note 16 du guide est reprise à la fin (« Note du guide : … »)."),
    ("regle", "T6", "T6", "VI §1.2.2.1, cas particuliers 3°", (138, 138), r"3°\) Une intervention dite de confort", r"en cohérence avec la prise en charge par\s*l’assurance maladie obligatoire\.", "La règle T6 est rappelée une seconde fois dans le §1.2.2.2 (p. 132) ; ce rappel n'est pas repris."),
    ("regle", "T7", "T7", "VI §1.2.2.1, cas particuliers 4°", (138, 139), r"4°\) Dans la situation de prise en charge pour soins spécifiques de stomies", r"du chapitre V\.", ""),
    ("regle", "T15", "T15", "VI §1.2.2.1, cas particuliers 5°", (139, 139), r"5°\) L’opération prophylactique", r"Ablation\s*prophylactique du sein\.", ""),
    ("regle", "T14", "T14", "VI §1.2.2.1, cas particuliers 6°", (139, 140), r"6°\) Traitement unique en deux temps", r"d’une complication de la maladie absente lors du premier acte\.", ""),
    ("regle", "T8", "T8", "VI §1.2.2.2", (140, 140), r"1\.2\.2\.2\. Traitement Unique « Interventionnel »", r"le DP de la seconde chimioembolisation est\s*l’hépatocarcinome\.", "L'étiquette est écrite [REGLE T8] dans le guide. Le rappel de la règle T6 qui suit n'est pas repris."),
    ("regle", "T9", "T9", "VI §1.2.2.3", (140, 141), r"1\.2\.2\.3\. Traitement Unique Médical", r"celui- ?ci poursuivant le traitement de l’endocardite, elle reste le DP de son RUM\.", ""),
    ("regle", "T9", "T9-initiation-tt-chronic", "VI §1.2.3, 1°", (141, 141), r"1°\) La mise en route du traitement d’une maladie chronique", r"du chapitre I doivent être respectées\.", "Sans étiquette dans le guide : situation équivalente au traitement unique (mise en route du traitement d'une maladie chronique) ; vaut pour la seule ligne T9-initiation-tt-chronic."),
    ("regle", "T9", "T9-diabetes", "VI §1.2.3, 2°", (142, 142), r"2°\) Chez les patients diabétiques", r"avec\s*lequel le patient quittera l’unité\.", "Sans étiquette dans le guide : situation équivalente au traitement unique (changement de stratégie thérapeutique chez le diabétique) ; vaut pour la seule ligne T9-diabetes."),
    ("regle", "T12", "T12", "VI §1.2.3, 3°", (142, 142), r"3°\) L’accouchement normal", r"\[Règle T12\]\s*\.", ""),
    ("regle", "T13", "T13", "VI §1.2.3, 4°", (142, 142), r"4°\) La naissance d’un enfant", r"RUM du nouveau-né en maternité\s*\.", ""),
    ("regle", "IVG", "IVG", "VI §1.2.3, 5°", (142, 142), r"5°\) L’interruption volontaire de grossesse", r"par le quatrième\s*caractère du code O04\.–\.", "Règle IVG : sans étiquette dans le guide (§1.2.3, 5°) ; ligne IVG du tableau. Lettres espacées de l'extraction réparées."),
    ("regle", "IMG", "ITG", "VI §1.2.3, 6°", (142, 142), r"6°\) L’interruption médicale de grossesse", r"la cause fœtale ou\s*maternelle de l’IMG", "Règle IMG : sans étiquette dans le guide (§1.2.3, 6°) ; correspond à la ligne ITG du tableau. Le paragraphe se termine sans point."),
    ("regle", "S1", "S1", "VI §1.3.1", (143, 144), r"1\.3\.1\. Surveillance négative", r"du chapitre XXI de la CIM–10\) du chapitre V\.", "Se termine par la phrase qui précède S2 (consignes d'emploi des codes de surveillance négative)."),
    ("regle", "S2", "S2", "VI §1.3.1", (144, 144), r"Les codes de la catégorie Z94 s’imposent", r"\[Règle S2\]", ""),
    ("regle", "S3", "S3", "VI §1.3.1", (144, 144), r"De même, les codes de la catégorie Z95", r"\[Règle S3\]", ""),
    ("regle", "SD1", "SD1", "VI §1.3.2", (144, 145), r"1\.3\.2\. Surveillance positive", r"l’affection découverte est un\s*diagnostic associé significatif \(DAS\)\.", ""),
    ("regle", "S4", "S4", "VI §1.3.3", (145, 145), r"1\.3\.3\. Situations équivalentes", r"d’autres nourrissons et enfants en bonne santé\.", ""),
    ("regle", "SD2", "SD2", "VI §1.3.3", (145, 145), r"On assimile à la situation de surveillance positive", r"avant la découverte de la récidive\s*\.", ""),
    ("regle", "M1", "M1", "VI §1.5", (148, 148), r"1\.5\. QUE FAIRE SI L’ANALYSE", r"\[Règle M1\]", ""),
    ("regle", "M2", "M2", "VI §1.5", (148, 148), r"Dans le cas où les deux problèmes auraient mobilisé", r"L’affection qui n’est pas retenue comme DP est un DAS\.", ""),
]
SUFFIXES = {("regle", "T5"): NOTE_16}


def pages_pdf() -> list[str]:
    txt = subprocess.run(["pdftotext", "-layout", str(PDF), "-"], capture_output=True, text=True, check=True).stdout
    return txt.split("\f")


def nettoyer_page(page: str) -> str:
    """Retire le numéro de page (première ligne qui n'est qu'un nombre), le bloc des notes de bas de page (à partir de la
    première ligne commençant en colonne 0 par un nombre seul ou suivi d'une lettre) et les appels de note (lignes qui ne
    contiennent qu'un nombre, en retrait)."""
    lignes = page.split("\n")
    # numéro de page : première ligne non vide, un nombre seul
    for i, l in enumerate(lignes):
        if l.strip():
            if re.fullmatch(r"\s*\d{1,3}\s*", l): lignes[i] = ""
            break
    # notes de bas de page
    for i, l in enumerate(lignes):
        # un nombre seul en colonne 0, ou suivi d'une majuscule (« 16 La plupart », « 22Instruction ») ; pas « 10e révision », « 1) », « 1°) »
        if re.match(r"^\d{1,2}(\s*$|\s+[A-ZÀ-Ü«(]|[A-ZÀ-Ü])", l):
            lignes = lignes[:i]; break
    # appels de note : lignes réduites à un ou plusieurs nombres, en retrait
    lignes = [l for l in lignes if not re.fullmatch(r"\s+(\d{1,2}\s*)+", l)]
    return "\n".join(lignes)


def remettre_en_paragraphes(texte: str) -> str:
    """Réunit les lignes d'un même paragraphe ; une ligne vide sépare les paragraphes ; répare les césures."""
    paras, courant = [], []
    retrait_prec = 0
    for l in texte.split("\n"):
        s = l.strip()
        if not s:
            if courant: paras.append(" ".join(courant)); courant = []
            continue
        retrait = len(l) - len(l.lstrip())
        # ouvrent un nouveau paragraphe : puces et numérotations, « Exemple(s) », « N.B. », et un retour en colonne 0 après
        # des lignes en retrait (fin d'une liste ou d'un exemple)
        debut_para = re.match(r"^(–|-|•|▪|o|\d{1,2}[°)]|\d\)|[a-z]\)|Exemples?\b|N\.B\.)(\s|$)", s) or (courant and retrait == 0 and retrait_prec >= 4)
        if courant and debut_para:
            paras.append(" ".join(courant)); courant = []
        courant.append(s)
        retrait_prec = retrait
        # ferment le paragraphe : un titre numéroté court ou ponctué, « Cas habituels / particuliers », une étiquette de règle en fin de ligne
        if re.match(r"^\d{1,2}°\)", s) and (len(s) < 60 or s.endswith((".", "]"))) or re.match(r"^•\s+Cas (habituels|particuliers)$", s) or re.search(r"\[R[èE]gle [A-Z]+\d*\]?\s*$", s):
            paras.append(" ".join(courant)); courant = []
    if courant: paras.append(" ".join(courant))
    # un paragraphe coupé par un changement de page ou un appel de note : pas de ponctuation finale, suite en minuscule
    fusion = []
    for p in paras:
        if fusion and not re.search(r"[.;:!?»)\]]\s*$", fusion[-1]) and re.match(r"^[a-zà-ÿ]", p) and not re.match(r"^(–|-|•|▪|o)\s", p):
            fusion[-1] += " " + p
        else:
            fusion.append(p)
    out = []
    for p in fusion:
        p = re.sub(r"(\w)- (?=[a-zà-ÿ])", r"\1-", p)          # « c’est- à-dire » -> « c’est-à-dire » (césure conservée)
        p = re.sub(r"(?<=[a-zà-ÿ)])\d{1,2}(?=[\s,.;:)])", "", p)   # appel de note collé à un mot (« respectée22 », « exceptions13 »)
        p = re.sub(r"(?<=[a-zà-ÿ\d»])\s+([.,)])", r"\1", p)      # espace laissée par un appel de note retiré avant . , )
        p = re.sub(r"–\s+,", "–,", p)                              # « Z51.0– , » coupé par un retour à la ligne
        p = re.sub(r"\s+([;:!?»])", r" \1", p)
        p = re.sub(r"\s{2,}", " ", p)
        out.append(p)
    return "\n".join(out)


def extraire(pages, pdeb, pfin, debut, fin):
    brut = "\n".join(nettoyer_page(pages[n - 1]) for n in range(pdeb, pfin + 1))
    m1 = re.search(debut, brut)
    if not m1: return None, "repère de début introuvable"
    m2 = re.search(fin, brut[m1.start():])
    if not m2: return None, "repère de fin introuvable"
    morceau = brut[m1.start(): m1.start() + m2.end()]
    for a, b in REPARATIONS: morceau = morceau.replace(a, b)
    return remettre_en_paragraphes(morceau), None


def main() -> None:
    pages = pages_pdf()
    lignes, bilan = [], []
    for typ, regle, regles, section, (pd, pf), deb, fin, note in EXTRAITS:
        texte, err = extraire(pages, pd, pf, deb, fin)
        if err:
            bilan.append(f"  !! {typ:9s} {regle or regles:20s} {section:34s} {err}"); continue
        suffixe = SUFFIXES.get((typ, regle))
        if suffixe: texte += "\n" + suffixe
        page = f"{pd - DECALAGE}" + ("" if pd == pf else f"-{pf - DECALAGE}")
        # `regles` : les règles officielles concernées ; `lignes` : les lignes du tableau concernées quand l'extrait ne vaut pas pour toute la règle
        regles_off = regle if typ == "regle" else " ".join(dict.fromkeys(("IMG" if x == "ITG" else x.split("-")[0]) for x in regles.split())) if regles else ""
        lignes_tab = "" if typ == "preambule" else (regles if (typ == "regle" and regles != regle) or (typ == "commun" and "-" in regles) else "")
        lignes.append({"type": typ, "regle_officielle": regles_off, "lignes": lignes_tab, "section": section, "page": page, "extrait": texte, "note": note})
        bilan.append(f"  {typ:9s} {(regle or regles)[:34]:34s} {section:30s} p. {page:8s} {len(texte):5d} car. ≈ {len(texte) // 4:4d} tokens")
    SORTIE.parent.mkdir(parents=True, exist_ok=True)
    with open(SORTIE, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["type", "regle_officielle", "lignes", "section", "page", "extrait", "note"]); w.writeheader(); w.writerows(lignes)
    # version markdown de relecture (même contenu), par sorte d'extrait
    titres = {"preambule": "Préambule", "commun": "Passages communs à plusieurs règles", "regle": "Extraits propres à chaque règle"}
    md = ["# Extraits officiels du guide méthodologique MCO 2026 (relecture)", "",
          "*Version de relecture, produite depuis `extraits_guide_methodologique_2026.csv` (qui reste le fichier de référence) par "
          "`scripts/referentiels/extraire_guide.py`. Mot pour mot ; seules les coupures de l'extraction ont été réparées. Pages : numéros imprimés. "
          "Lors de l'appel au LLM, la page envoie le préambule, les extraits des règles candidates, et une seule fois chaque passage commun qui concerne au moins l'une d'elles.*", ""]
    for typ in ("preambule", "commun", "regle"):
        tot = sum(len(l["extrait"]) for l in lignes if l["type"] == typ)
        md += [f"# {titres[typ]} ({sum(1 for l in lignes if l['type'] == typ)} extraits, {tot} caractères, ≈ {tot // 4} tokens)", ""]
        for l in lignes:
            if l["type"] != typ: continue
            l = dict(l)
            if typ == "regle": entete = (l["regle_officielle"] or "sans règle officielle") + (f" (ligne {l['lignes']})" if l["lignes"] else "")
            elif l["lignes"]: entete = "lignes " + l["lignes"].replace(" ", ", ")
            else: entete = l["regle_officielle"] and "règles " + l["regle_officielle"].replace(" ", ", ") or "toutes les règles"
            md += [f"## {entete} — {l['section']}, p. {l['page']} ({len(l['extrait'])} car.)", ""]
            if l["note"]: md += [f"> **Note :** {l['note']}", ""]
            for para in l["extrait"].split("\n"): md += [para, ""]
            md += ["---", ""]
    SORTIE.with_suffix(".md").write_text("\n".join(md), encoding="utf-8")
    total = sum(len(l["extrait"]) for l in lignes)
    print("\n".join(bilan)); print(f"\n{len(lignes)} extraits écrits dans {SORTIE.relative_to(RACINE)} (et sa version .md de relecture) ; total {total} caractères ≈ {total // 4} tokens")


if __name__ == "__main__":
    main()
