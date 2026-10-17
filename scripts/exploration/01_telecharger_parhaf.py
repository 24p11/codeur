"""Télécharge le corpus PARHAF (HealthDataHub/PARHAF) dans donnees/parhaf/.

Récupère les quatre fichiers utiles :
- data/train-00000-of-00001.parquet  : version Hugging Face (texte inclus)
- standalone/patients.json           : index de la version canonique
- standalone/data.zip                : textes bruts de la version canonique
- doc/...pdf                         : guide méthodologique de rédaction

L'archive est décompressée dans donnees/parhaf/standalone/textes/.
Les fichiers téléchargés ne sont jamais modifiés.

Usage : uv run python -I scripts/exploration/01_telecharger_parhaf.py
"""
import os
import zipfile
from pathlib import Path

from dotenv import load_dotenv
from huggingface_hub import hf_hub_download

RACINE = Path(__file__).resolve().parents[2]
DEST = RACINE / "donnees" / "parhaf"
DEPOT = "HealthDataHub/PARHAF"
FICHIERS = [
    "README.md",
    "data/train-00000-of-00001.parquet",
    "standalone/patients.json",
    "standalone/data.zip",
    "doc/PARTAGES_Guide_methodologique_de_redaction_et_de_relecture_des_CR_fictifs.pdf",
]


def main() -> None:
    load_dotenv(RACINE / ".env")
    jeton = os.getenv("HF_TOKEN") or None
    DEST.mkdir(parents=True, exist_ok=True)
    for nom in FICHIERS:
        chemin = hf_hub_download(DEPOT, nom, repo_type="dataset", local_dir=DEST, token=jeton)
        taille = Path(chemin).stat().st_size / 1e6
        print(f"{taille:8.2f} Mo  {Path(chemin).relative_to(RACINE)}")

    archive = DEST / "standalone" / "data.zip"
    textes = DEST / "standalone" / "textes"
    if not textes.exists():
        with zipfile.ZipFile(archive) as z:
            noms = z.namelist()
            z.extractall(textes)
        print(f"archive décompressée : {len(noms)} entrées dans {textes.relative_to(RACINE)}")
    else:
        print(f"archive déjà décompressée dans {textes.relative_to(RACINE)}")


if __name__ == "__main__":
    main()
