"""Affiche des patients PARHAF complets (métadonnées, scénario, résumé structuré, documents).

Usage :
  uv run python -I scripts/exploration/04_exemples_parhaf.py                 # trois exemples par défaut
  uv run python -I scripts/exploration/04_exemples_parhaf.py ID1 ID2 ...     # identifiants choisis
Les exemples par défaut : le CRH le plus court, un CRH de longueur médiane en neurologie,
un patient à trois documents en chirurgie viscérale (pool codage CIM-10).
"""
import json
import sys
from pathlib import Path
from statistics import median

RACINE = Path(__file__).resolve().parents[2]
PARHAF = RACINE / "donnees" / "parhaf"
TEXTES = PARHAF / "standalone" / "textes"


def choisir_par_defaut(patients):
    crh = [(d["word_count"], p["id"]) for p in patients for d in p["documents"] if d["type"] == "CRH"]
    plus_court = min(crh)[1]
    neuro = sorted((d["word_count"], p["id"]) for p in patients for d in p["documents"]
                   if d["type"] == "CRH" and p["specialty"] == "NEUROLOGIE")
    med = median(w for w, _ in neuro)
    mediane = min(neuro, key=lambda x: abs(x[0] - med))[1]
    trois = next(p["id"] for p in patients if p["specialty"] == "CHIRURGIE VISCERALE"
                 and p["pool"].startswith("CU 2") and len(p["documents"]) == 3)
    return [plus_court, mediane, trois]


def main() -> None:
    patients = json.load(open(PARHAF / "standalone" / "patients.json", encoding="utf-8"))["data"]
    par_id = {p["id"]: p for p in patients}
    ids = sys.argv[1:] or choisir_par_defaut(patients)
    for pid in ids:
        p = par_id[pid]
        print("\n" + "#" * 100)
        print(f"# PATIENT {pid} | spécialité {p['specialty']} | pool {p['pool']} | auteur {p['author']} | relecteur {p['reviewer']}")
        print("# scénario suggéré :", json.dumps(p["suggested_scenario"], ensure_ascii=False))
        print("# résumé structuré :", json.dumps(p.get("structured_abstract"), ensure_ascii=False))
        for i, d in enumerate(p["documents"], 1):
            print(f"\n--- document {i}/{len(p['documents'])} | type {d['type']} | header {d['header']!r} | {d['word_count']} mots | {d['path']}")
            print((TEXTES / d["path"]).read_text(encoding="utf-8"))


if __name__ == "__main__":
    main()
