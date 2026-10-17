"""Inventaire du corpus PARHAF à partir de la version standalone (JSON + .txt), déclarée canonique.

Produit des comptages : patients par spécialité et par pool, documents par patient (nombre, types,
ordre), longueurs, champs du scénario et du résumé structuré, particularités du texte.

Usage : uv run python -I scripts/exploration/03_inventaire_parhaf.py
"""
import json
import re
import unicodedata
from collections import Counter
from pathlib import Path
from statistics import median

RACINE = Path(__file__).resolve().parents[2]
PARHAF = RACINE / "donnees" / "parhaf"
TEXTES = PARHAF / "standalone" / "textes"


def titre(t: str) -> None:
    print(f"\n===== {t} =====")


def main() -> None:
    patients = json.load(open(PARHAF / "standalone" / "patients.json", encoding="utf-8"))["data"]
    docs = []  # (patient, index dans le patient, document, texte)
    for p in patients:
        for i, d in enumerate(p["documents"]):
            brut = (TEXTES / d["path"]).read_bytes()
            docs.append((p, i, d, brut))

    titre("Patients par spécialité (nombre de patients, de documents)")
    par_spe = Counter(p["specialty"] for p in patients)
    docs_spe = Counter(p["specialty"] for p, *_ in docs)
    for s, n in sorted(par_spe.items()):
        print(f"  {s:28s} {n:5d} patients  {docs_spe[s]:5d} documents")
    titre("Patients par pool")
    for k, n in Counter(p["pool"] for p in patients).most_common():
        print(f"  {k:42s} {n}")

    titre("Documents par patient")
    print("  nombre de documents :", sorted(Counter(len(p["documents"]) for p in patients).items()))
    print("  types de documents  :", Counter(d["type"] for _, _, d, _ in docs).most_common())
    print("  combinaisons (dans l'ordre du fichier) :")
    for combo, n in Counter(tuple(d["type"] for d in p["documents"]) for p in patients).most_common():
        print(f"    {n:5d}  {' > '.join(combo)}")
    print("  patients sans aucun document CRH :", sum(1 for p in patients if "CRH" not in {d["type"] for d in p["documents"]}))
    print("  patients avec plusieurs CRH      :", sum(1 for p in patients if sum(d["type"] == "CRH" for d in p["documents"]) > 1))

    titre("Longueur des documents (mots selon word_count)")
    for t in sorted({d["type"] for _, _, d, _ in docs}):
        wc = [d["word_count"] for _, _, d, _ in docs if d["type"] == t]
        print(f"  {t:12s} n={len(wc):5d}  min={min(wc):5d}  médiane={median(wc):7.0f}  max={max(wc):6d}")
    wc_pat = [sum(d["word_count"] for d in p["documents"]) for p in patients]
    print(f"  par patient (concaténé) : min={min(wc_pat)} médiane={median(wc_pat):.0f} max={max(wc_pat)}")
    # word_count vs comptage réel
    ecarts = 0
    for _, _, d, brut in docs:
        if abs(len(brut.decode("utf-8").split()) - d["word_count"]) > 0:
            ecarts += 1
    print(f"  documents dont word_count diffère d'un simple comptage des mots séparés par des blancs : {ecarts}")

    titre("Champs 'header' des documents (titre)")
    print("  valeurs distinctes :", len({d["header"] for _, _, d, _ in docs}))
    for h, n in Counter(d["header"] for _, _, d, _ in docs).most_common(12):
        print(f"    {n:5d}  {h!r}")
    print("  en-têtes contenant une date (jj/mm/aaaa ou aaaa) :",
          sum(1 for _, _, d, _ in docs if re.search(r"\d{1,2}/\d{1,2}/\d{2,4}|\b(19|20)\d{2}\b", d["header"])))

    titre("Indices de date dans le texte (pour ordonner les documents)")
    motif_date = re.compile(r"\b\d{1,2}[/.-]\d{1,2}[/.-](19|20)?\d{2}\b")
    avec_date = sum(1 for _, _, _, b in docs if motif_date.search(b.decode("utf-8")))
    print(f"  documents dont le texte contient au moins une date au format jj/mm/aaaa : {avec_date} / {len(docs)}")
    debut = Counter(b.decode("utf-8")[:40].split("\n")[0][:30] for _, _, _, b in docs)
    print("  premières lignes les plus fréquentes :")
    for l, n in debut.most_common(8):
        print(f"    {n:5d}  {l!r}")
    print("  aucun champ de date ou d'ordre explicite dans le JSON (clés : type, header, path, word_count).")

    titre("Scénario suggéré")
    cles = Counter()
    nb_dp = Counter()
    code_sans_point = 0
    codes = Counter()
    for p in patients:
        s = p["suggested_scenario"]
        for k, v in s.items():
            if v not in (None, "", [], {}):
                cles[k] += 1
        dp = s.get("primary_diagnosis") or []
        nb_dp[len(dp)] += 1
        for c in dp:
            codes[c.get("code")] += 1
            if c.get("code") and "." not in c["code"]:
                code_sans_point += 1
    print("  champs renseignés (sur", len(patients), "patients) :", dict(cles))
    print("  nombre de diagnostics principaux par patient :", dict(nb_dp))
    print("  codes DP sans point (ex. C341) :", code_sans_point, "/", sum(nb_dp[k] * k for k in nb_dp))
    print("  longueur des codes DP :", Counter(len(c) for c in codes.elements() if c))
    print("  codes DP distincts :", len(codes), "; les plus fréquents :", codes.most_common(8))
    print("  codes DP vides/None :", codes.get(None, 0) + codes.get("", 0))
    print("  age.unit :", Counter(p["suggested_scenario"]["age"]["unit"] for p in patients if p["suggested_scenario"].get("age")))
    print("  sex :", Counter(p["suggested_scenario"].get("sex") for p in patients))
    print("  type_of_care renseigné :", cles["type_of_care"], "; primary_procedure renseigné :", cles["primary_procedure"])

    titre("Résumé structuré (structured_abstract)")
    vide = sum(1 for p in patients if not p.get("structured_abstract"))
    print("  absent ou vide :", vide, "/", len(patients))
    cles_sa = Counter()
    nb_dp_sa = Counter()
    accord = desaccord = 0
    for p in patients:
        sa = p.get("structured_abstract") or {}
        for k, v in sa.items():
            if v not in (None, "", [], {}):
                cles_sa[k] += 1
        dps = sa.get("primary_diagnosis") or []
        nb_dp_sa[len(dps)] += 1
        dp_sc = {c.get("code") for c in (p["suggested_scenario"].get("primary_diagnosis") or [])}
        dp_sa = {c.get("code") for c in dps if c.get("code")}
        if dp_sa:
            if dp_sc & dp_sa:
                accord += 1
            else:
                desaccord += 1
    print("  champs renseignés :", dict(cles_sa))
    print("  nombre de DP dans le résumé :", dict(sorted(nb_dp_sa.items())))
    print(f"  résumé avec code DP : accord avec le scénario {accord}, désaccord {desaccord}")

    titre("Particularités du texte")
    crlf = sum(1 for *_, b in docs if b"\r\n" in b)
    cr = sum(1 for *_, b in docs if b"\r" in b and b"\r\n" not in b)
    bom = sum(1 for *_, b in docs if b.startswith(b"\xef\xbb\xbf"))
    non_utf8 = 0
    for *_, b in docs:
        try:
            b.decode("utf-8")
        except UnicodeDecodeError:
            non_utf8 += 1
    textes = [b.decode("utf-8", errors="replace") for *_, b in docs]
    vides = sum(1 for t in textes if not t.strip())
    blancs_bord = sum(1 for t in textes if t != t.strip())
    nbsp = sum(1 for t in textes if " " in t)
    tab = sum(1 for t in textes if "\t" in t)
    lignes_vides_multiples = sum(1 for t in textes if "\n\n\n" in t)
    ctrl = Counter()
    for t in textes:
        for ch in t:
            if unicodedata.category(ch) in ("Cc", "Cf") and ch not in "\n\r\t":
                ctrl[repr(ch)] += 1
    print(f"  encodage : non-UTF-8 {non_utf8}, BOM {bom}, fins de ligne CRLF {crlf}, CR seul {cr}")
    print(f"  textes vides {vides}, blancs en début/fin {blancs_bord}, espaces insécables {nbsp}, tabulations {tab}, ≥3 sauts consécutifs {lignes_vides_multiples}")
    print(f"  caractères de contrôle/format inhabituels : {dict(ctrl)}")
    doublons = Counter(textes)
    print("  textes strictement identiques entre deux documents :", sum(1 for v in doublons.values() if v > 1))
    ids = Counter(p["id"] for p in patients)
    print("  identifiants patient en double :", sum(1 for v in ids.values() if v > 1))
    chemins = Counter(d["path"] for _, _, d, _ in docs)
    print("  chemins de fichier en double :", sum(1 for v in chemins.values() if v > 1))
    # Caractères non ASCII les plus fréquents hors lettres accentuées courantes
    speciaux = Counter()
    for t in textes:
        for ch in t:
            if ord(ch) > 127 and ch not in "àâäéèêëîïôöùûüçÀÂÄÉÈÊËÎÏÔÖÙÛÜÇœŒæÆ’°«»–—…€":
                speciaux[ch] += 1
    print("  caractères non ASCII inhabituels (hors accents courants) :", speciaux.most_common(25))
    # Présence de rubriques attendues (pour l'évaluation du document)
    rubriques = ["motif", "antécédent", "histoire de la maladie", "examen clinique", "évolution", "conclusion", "traitement de sortie"]
    crh = [t.lower() for (_, _, d, _), t in zip(docs, textes) if d["type"] == "CRH"]
    print(f"  rubriques trouvées dans les {len(crh)} CRH (présence du mot) :",
          {r: sum(1 for t in crh if r in t) for r in rubriques})
    print("  CRH comportant un nom de patient du scénario (champ name) :",
          sum(1 for (p, _, d, _), t in zip(docs, textes) if d["type"] == "CRH" and p["suggested_scenario"].get("name") and p["suggested_scenario"]["name"].split()[-1].lower() in t.lower()))


if __name__ == "__main__":
    main()
