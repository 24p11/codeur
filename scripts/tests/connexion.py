"""Connexion à la base Supabase pour les scripts de vérification et de test.

Lit `.env` (jamais affiché) et construit l'adresse de connexion PostgreSQL à partir de l'adresse
du « pooler » enregistrée par `supabase link` dans supabase/.temp/pooler-url (hôte et utilisateur),
en y ajoutant le mot de passe SUPABASE_DB_PASSWORD.
"""
import os
from pathlib import Path
from urllib.parse import quote

from dotenv import load_dotenv

RACINE = Path(__file__).resolve().parents[2]


def charger_env() -> dict:
    load_dotenv(RACINE / ".env")
    env = {k: os.getenv(k) for k in ("SUPABASE_URL", "SUPABASE_PROJECT_REF", "SUPABASE_PUBLISHABLE_KEY",
                                      "SUPABASE_SECRET_KEY", "SUPABASE_DB_PASSWORD")}
    manquantes = [k for k, v in env.items() if not v]
    if manquantes:
        raise SystemExit(f"variables manquantes dans .env : {', '.join(manquantes)}")
    return env


def url_postgres(env: dict) -> str:
    fichier = RACINE / "supabase" / ".temp" / "pooler-url"
    if fichier.exists():
        base = fichier.read_text().strip()  # postgresql://postgres.<ref>@<hôte>:5432/postgres
        utilisateur, reste = base.removeprefix("postgresql://").split("@", 1)
    else:
        utilisateur, reste = f"postgres.{env['SUPABASE_PROJECT_REF']}", "aws-0-eu-west-1.pooler.supabase.com:5432/postgres"
    return f"postgresql://{utilisateur}:{quote(env['SUPABASE_DB_PASSWORD'], safe='')}@{reste}"
