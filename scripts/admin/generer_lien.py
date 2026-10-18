"""Fabrique un lien de connexion pour une adresse électronique, SANS l'envoyer (clé secrète).

À utiliser quand le service d'envoi intégré de Supabase (quelques courriels par heure) ne suffit pas :
le lien est affiché, à copier dans un courriel envoyé par vos soins.
Si l'adresse n'a pas encore de compte, Supabase le crée au passage (comme le ferait la demande de lien depuis la page).

Usage :
  uv run python -I scripts/admin/generer_lien.py adresse@exemple.fr
  uv run python -I scripts/admin/generer_lien.py adresse@exemple.fr --local   # retour sur http://localhost:8000/

Validité : celle réglée dans Supabase, Authentication > Providers > Email > « Email OTP expiration »
(3600 secondes, soit une heure, par défaut). Le lien est à usage unique.
"""
import argparse
import sys
from pathlib import Path

from supabase import create_client

RACINE = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(RACINE / "scripts" / "tests"))
from connexion import charger_env  # noqa: E402

ADRESSE_PUBLIEE = "https://24p11.github.io/codeur/"
ADRESSE_LOCALE = "http://localhost:8000/"


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("email", help="adresse électronique du testeur")
    ap.add_argument("--local", action="store_true", help="lien ramenant sur la page servie en local")
    args = ap.parse_args()
    env = charger_env()
    admin = create_client(env["SUPABASE_URL"], env["SUPABASE_SECRET_KEY"])
    retour = ADRESSE_LOCALE if args.local else ADRESSE_PUBLIEE
    rep = admin.auth.admin.generate_link({"type": "magiclink", "email": args.email, "options": {"redirect_to": retour}})
    lien = rep.properties.action_link
    print(f"Lien de connexion pour {args.email} (retour sur {retour}), à usage unique, valable le temps réglé dans Supabase (une heure par défaut) :\n")
    print(lien)
    print("\nÀ envoyer vous-même au testeur. Ne pas le publier.")


if __name__ == "__main__":
    main()
