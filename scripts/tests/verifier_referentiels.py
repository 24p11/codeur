"""Vérifie, connecté comme testeur (clé publique + compte de test), que la recherche de codes fonctionne
comme la page la fera : par code (exact, par préfixe), descendants codables, par mots dans les formulations
(insensible aux accents et à la casse). Le compte de test est créé puis supprimé.

Usage : uv run python -I scripts/tests/verifier_referentiels.py
"""
import secrets
import sys
import unicodedata
from pathlib import Path

from supabase import create_client

sys.path.insert(0, str(Path(__file__).resolve().parent))
from connexion import charger_env  # noqa: E402


def normaliser(s: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFD", s.lower()) if unicodedata.category(c) != "Mn")


def main() -> None:
    env = charger_env()
    admin = create_client(env["SUPABASE_URL"], env["SUPABASE_SECRET_KEY"])
    email, mdp = f"test-ref-{secrets.token_hex(4)}@example.com", secrets.token_urlsafe(16)
    u = admin.auth.admin.create_user({"email": email, "password": mdp, "email_confirm": True})
    ok_total = 0
    total = 0
    try:
        c = create_client(env["SUPABASE_URL"], env["SUPABASE_PUBLISHABLE_KEY"])
        c.auth.sign_in_with_password({"email": email, "password": mdp})

        def essai(nom, attendu_ok, resultat):
            nonlocal ok_total, total
            total += 1; ok_total += bool(attendu_ok)
            print(f"  [{'OK' if attendu_ok else 'ÉCHEC'}] {nom} : {resultat}")

        r = c.table("fiches").select("code, libelle, codable, statut_mco").eq("code", "I10").execute().data
        essai("par code exact I10", r and r[0]["codable"], r)
        r = c.table("fiches").select("code, libelle, codable").eq("code", "Z992").execute().data
        essai("Z992 : codable (souche)", r and r[0]["codable"], r)
        r = c.table("descendants_codables").select("code, libelle, ordre_kit").eq("noeud", "Z992").order("ordre_kit").execute().data
        essai("descendants codables de Z992", [x["code"] for x in r] == ["Z992+0", "Z992+1", "Z992+8"], [x["code"] for x in r])
        r = c.table("fiches").select("code, codable, statut_mco").eq("code", "C50").execute().data
        essai("C50 : non codable, père interdit", r and not r[0]["codable"] and r[0]["statut_mco"] == "pere_interdit", r)
        r = c.table("descendants_codables").select("code").eq("noeud", "C50").execute().data
        essai("descendants codables de C50 (pour la boucle de correction)", len(r) >= 5, f"{len(r)} descendants, ex. {[x['code'] for x in r[:4]]}")
        r = c.table("fiches").select("code").eq("code", "I10.0").execute().data
        essai("I10.0 (avec point) : inconnu, la page devra normaliser", r == [], r)
        r = c.table("fiches").select("code").eq("code", "N571").execute().data
        essai("N571 : inconnu du kit", r == [], r)
        # Par mots : la page interrogera formulation_normalisee (minuscules, sans accents) avec ilike.
        for mot, code_attendu in (("hypertension", "I10"), ("HTA", "I10"), ("hypertensión", "I10"), ("diverticulite perforee", None), ("hernie inguinale", "K409")):
            motif = "%" + normaliser(mot) + "%"
            r = c.table("synonymes").select("code, formulation, origine, source").ilike("formulation_normalisee", motif).limit(2000).execute().data
            codes = sorted({x["code"] for x in r})
            cible = code_attendu in codes if code_attendu else len(r) > 0
            essai(f"par mots « {mot} »", cible, f"{len(r)} formulations, {len(codes)} codes" + (f", contient {code_attendu}" if code_attendu and cible else "") + f" ; ex. {[(x['code'], x['formulation']) for x in r[:3]]}")
        r = c.table("synonymes").select("formulation, origine, source").eq("code", "I10").eq("origine", "libelle").execute().data
        essai("libellé officiel de I10 présent dans synonymes", r and r[0]["source"] == "ATIH kit 2025", r)
        r = c.table("fiches").select("code", count="exact", head=True).execute().count
        essai("nombre de fiches lisibles", r == 42897, r)
        try:
            c.table("fiches").insert({"code": "X999", "libelle": "x", "codable": True, "version_livraison": "x"}, returning="minimal").execute()
            essai("écrire dans fiches (interdit)", False, "accepté !")
        except Exception as e:  # noqa: BLE001
            essai("écrire dans fiches (interdit)", True, str(getattr(e, "message", e))[:60])
    finally:
        admin.auth.admin.delete_user(u.user.id)
        print(f"  compte de test supprimé\nBILAN : {ok_total} vérifications réussies sur {total}")
    sys.exit(0 if ok_total == total else 1)


if __name__ == "__main__":
    main()
