"""Test de la convention de positions (docs/page_web.md) : la page (web/positions.js, exécuté par Node)
et Python doivent donner les mêmes positions et le même texte cité.

Textes de test : accents, caractères spéciaux (µ, ², →, ᵉ, ⅓), un émoji et une lettre mathématique hors du plan
de base (2 unités UTF-16 chacun), plusieurs documents d'origine avec intitulés et lignes vides.
Pour chaque passage : (1) Python choisit des positions en points de code et le texte attendu texte[debut:fin] ;
Node doit extraire le même texte et valider le passage ; (2) Python calcule les indices UTF-16 correspondants
(ce que donne une sélection dans le navigateur) ; Node doit en déduire les mêmes positions en points de code.

Usage : uv run python -I scripts/tests/tester_positions.py   (Node doit être installé)
"""
import json
import subprocess
import sys
from pathlib import Path

RACINE = Path(__file__).resolve().parents[2]
TEXTES = {
    "accents": "Compte rendu d'hospitalisation\n\nMadame Élodie Lefèvre, 47 ans, hospitalisée pour une pneumopathie aiguë.\nTempérature à 38,5 °C ; créatinine 85 µmol/L ; surface 1,8 m² → DFG 72 mL/min.",
    "speciaux": "Hémoglobine 12,1 g/dL, plaquettes 250 G/L, ⅓ de la dose au 3ᵉ jour, pH ¦ 7,42 ¦ 7,35-7,45.",
    "hors_plan": "Patient 😀 très satisfait ; variable 𝑥 = 3 ; fin.",
    "multi": "— Consultation —\n\nCompte rendu de consultation\n\nLe 14/05/2025, Mme Seguy, 43 ans.\n\n— Compte rendu opératoire —\n\nIntervention : HAL-Doppler.\n\n— Compte rendu d'hospitalisation —\n\nSuites simples.",
}


def u16(texte: str, i: int) -> int:
    """Index UTF-16 (ce que compte JavaScript) correspondant à la position i en points de code."""
    return len(texte[:i].encode("utf-16-le")) // 2


def main() -> None:
    cas, attendus = [], []
    for nom, texte in TEXTES.items():
        n = len(texte)
        choix = [(0, 5), (10, 25), (n - 8, n), (0, n)]
        for motif in ("µmol/L", "1,8 m²", "😀", "𝑥 = 3", "⅓ de la dose", "3ᵉ jour", "Mme Seguy, 43 ans.\n\n— Compte rendu opératoire —\n\nIntervention", "— Consultation —\n\nCompte", "aiguë.\nTempérature"):
            i = texte.find(motif)
            if i >= 0:
                choix.append((i, i + len(motif)))
        for debut, fin in choix:
            attendu = texte[debut:fin]
            cas.append({"nom": nom, "texte": texte, "debut": debut, "fin": fin, "attendu": attendu,
                        "debut16": u16(texte, debut), "fin16": u16(texte, fin)})
            attendus.append((nom, debut, fin, attendu, len(texte)))
    res = subprocess.run(["node", str(RACINE / "scripts" / "tests" / "positions_node.js")], input=json.dumps(cas),
                         capture_output=True, text=True, check=True)
    sorties = json.loads(res.stdout)
    echecs = 0
    for (nom, debut, fin, attendu, longueur), s in zip(attendus, sorties):
        ok = (s["longueur"] == longueur and s["extrait"] == attendu and s["verif"] is True and s["verif_faux"] is False
              and s["passage"] is not None and s["passage"]["debut"] == debut and s["passage"]["fin"] == fin and s["passage"]["texte"] == attendu)
        if not ok:
            echecs += 1
        apercu = attendu.replace("\n", "⏎")[:40]
        print(f"  [{'OK' if ok else 'ÉCHEC'}] {nom:9s} [{debut}:{fin}] {apercu!r}" + ("" if ok else f"  -> Node : {s}"))
    print(f"\nBILAN : {len(cas) - echecs} passages conformes sur {len(cas)} ; "
          f"{sum(1 for c in cas if any(ord(ch) > 0xFFFF for ch in c['texte']))} cas sur des textes contenant des caractères hors plan de base")
    sys.exit(1 if echecs else 0)


if __name__ == "__main__":
    main()
