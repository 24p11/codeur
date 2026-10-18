#!/bin/sh
# Lance la page web en local : copie la mention d'information dans web/ (seule version dans le dépôt :
# docs/mention_information.md ; la copie est ignorée par git), puis sert le dossier web/ sur http://localhost:8000/.
# Arrêt : Ctrl+C.
set -e
cd "$(dirname "$0")/../.."
cp docs/mention_information.md web/mention_information.md
echo "Page disponible sur http://localhost:8000/  (Ctrl+C pour arrêter)"
python3 -m http.server 8000 --directory web --bind 127.0.0.1
