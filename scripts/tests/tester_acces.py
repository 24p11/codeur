"""Tests réels des règles d'accès de la base (docs/SCHEMA.md §7).

Déroulement :
  1. avec la clé secrète : création de deux comptes de test, d'un lot, d'un document et d'une ligne
     de codage d'étape « scenario » ;
  2. avec la clé publique et le premier compte connecté : série d'essais, chacun avec le résultat attendu ;
  3. avec la clé secrète : suppression des données et des comptes de test (toujours exécutée, même si un essai échoue).

Usage : uv run python -I scripts/tests/tester_acces.py
"""
import secrets
import sys
import uuid
from pathlib import Path

from supabase import create_client

sys.path.insert(0, str(Path(__file__).resolve().parent))
from connexion import charger_env  # noqa: E402

RESULTATS = []


def essai(nom: str, attendu: str, action):
    """Exécute `action` ; `attendu` vaut « succès », « refus » (erreur de la base) ou « vide » (aucune ligne)."""
    try:
        data = action()
        obtenu = "vide" if data in (None, []) else "succès"
        detail = f"{len(data)} ligne(s)" if isinstance(data, list) else ""
    except Exception as e:  # noqa: BLE001
        obtenu = "refus"
        detail = str(getattr(e, "message", e))[:90]
    ok = obtenu == attendu
    RESULTATS.append(ok)
    print(f"  [{'OK' if ok else 'ÉCHEC'}] {nom}\n         attendu : {attendu} ; obtenu : {obtenu} {detail}")
    return ok


def rows(reponse):
    return reponse.data


def main() -> None:
    env = charger_env()
    admin = create_client(env["SUPABASE_URL"], env["SUPABASE_SECRET_KEY"])
    jeton = secrets.token_hex(4)
    comptes = [(f"test-codeur-{jeton}-{i}@example.com", secrets.token_urlsafe(16)) for i in (1, 2)]
    ids_users, lot_id, doc_id, doc2_id = [], f"test-{jeton}", None, None

    try:
        # ---------------------------------------------------------------- 1. préparation (clé secrète)
        print("=== 1. Préparation avec la clé secrète ===")
        for email, mdp in comptes:
            u = admin.auth.admin.create_user({"email": email, "password": mdp, "email_confirm": True})
            ids_users.append(u.user.id)
        print(f"  deux comptes créés ({comptes[0][0]}, {comptes[1][0]})")
        admin.table("lots").insert({"id": lot_id, "source": "test", "version": "0", "description": "lot de test"}).execute()
        doc = admin.table("documents").insert({"lot": lot_id, "id_source": "DOC-TEST", "texte": "Texte de test. HTA traitée.",
                                               "specialite": "Test"}).execute().data[0]
        doc_id = doc["id"]
        print(f"  document de test inséré (id {doc_id}), empreinte calculée : {doc['empreinte'][:16]}…")
        admin.table("codages").insert({"document": doc_id, "etape": "scenario", "codage": {"ensembles": [{"code": "I10", "categorie": "pathologie_principale"}]}}).execute()
        print("  ligne de codage « scenario » insérée")

        # Le déclencheur « texte figé » s'applique même à la clé secrète.
        essai("clé secrète : modifier motif_version d'un document (autorisé)", "succès",
              lambda: rows(admin.table("documents").update({"motif_version": "essai"}).eq("id", doc_id).execute()))
        essai("clé secrète : modifier le texte d'un document (refusé par le déclencheur)", "refus",
              lambda: rows(admin.table("documents").update({"texte": "autre texte"}).eq("id", doc_id).execute()))

        # ---------------------------------------------------------------- 2. essais avec la clé publique
        print("\n=== 2. Visiteur non connecté (clé publique, sans compte) ===")
        anon = create_client(env["SUPABASE_URL"], env["SUPABASE_PUBLISHABLE_KEY"])
        essai("non connecté : lire les documents", "refus", lambda: rows(anon.table("documents").select("id").execute()))
        essai("non connecté : lire les fiches", "refus", lambda: rows(anon.table("fiches").select("code").execute()))
        essai("non connecté : lire la vue dossiers_disponibles", "refus", lambda: rows(anon.table("dossiers_disponibles").select("id").execute()))

        print("\n=== 3. Premier compte connecté (clé publique) ===")
        c1 = create_client(env["SUPABASE_URL"], env["SUPABASE_PUBLISHABLE_KEY"])
        c1.auth.sign_in_with_password({"email": comptes[0][0], "password": comptes[0][1]})
        u1 = ids_users[0]
        c2 = create_client(env["SUPABASE_URL"], env["SUPABASE_PUBLISHABLE_KEY"])
        c2.auth.sign_in_with_password({"email": comptes[1][0], "password": comptes[1][1]})
        u2 = ids_users[1]

        essai("lire le document de test", "succès", lambda: rows(c1.table("documents").select("id, texte").eq("id", doc_id).execute()))
        essai("lire les lots et référentiels", "succès", lambda: rows(c1.table("lots").select("id").eq("id", lot_id).execute()))
        essai("ajouter une ligne de codage à son nom (revue_humain)", "succès",
              lambda: rows(c1.table("codages").insert({"document": doc_id, "etape": "revue_humain", "utilisateur": u1,
                                                       "codage": {"ensembles": []}}).execute()))
        mes_codages = c1.table("codages").select("id, etape, utilisateur").eq("document", doc_id).execute().data
        essai("ne voir aucune ligne d'étape scenario", "vide", lambda: [c for c in mes_codages if c["etape"] == "scenario"])
        essai("ajouter une ligne d'étape scenario (interdit)", "refus",
              lambda: rows(c1.table("codages").insert({"document": doc_id, "etape": "scenario", "codage": {}}, returning="minimal").execute()))
        essai("ajouter une ligne au nom du second compte (interdit)", "refus",
              lambda: rows(c1.table("codages").insert({"document": doc_id, "etape": "revue_humain", "utilisateur": u2, "codage": {}}, returning="minimal").execute()))
        c2.table("codages").insert({"document": doc_id, "etape": "revue_humain", "utilisateur": u2, "codage": {"ensembles": []}}).execute()
        essai("ne pas voir les lignes du second compte", "vide",
              lambda: rows(c1.table("codages").select("id").eq("utilisateur", u2).execute()))
        ma_ligne = [c for c in mes_codages if c["etape"] == "revue_humain"][0]["id"]
        essai("modifier sa propre ligne de codage (interdit)", "refus",
              lambda: rows(c1.table("codages").update({"valide": True}).eq("id", ma_ligne).execute()))
        essai("supprimer sa propre ligne de codage (interdit)", "refus",
              lambda: rows(c1.table("codages").delete().eq("id", ma_ligne).execute()))

        print("\n--- appels au LLM : UUID fourni par la page, puis codage qui y fait référence ---")
        appel_id = str(uuid.uuid4())
        essai("enregistrer un appel avec son propre UUID (sans relecture : returning=minimal)", "vide",
              lambda: rows(c1.table("appels_llm").insert({"id": appel_id, "utilisateur": u1, "document": doc_id, "tache": "codage",
                                                          "fournisseur": "test", "modele": "test", "reponse": "{}"},
                                                         returning="minimal").execute()))
        essai("enregistrer un appel en demandant la ligne en retour (impossible : pas de relecture)", "refus",
              lambda: rows(c1.table("appels_llm").insert({"id": str(uuid.uuid4()), "utilisateur": u1, "document": doc_id, "tache": "codage"}).execute()))
        essai("relire ses appels au LLM (interdit)", "refus", lambda: rows(c1.table("appels_llm").select("id").execute()))
        essai("ajouter une ligne de codage ia_humain qui référence l'appel", "succès",
              lambda: rows(c1.table("codages").insert({"document": doc_id, "etape": "ia_humain", "utilisateur": u1,
                                                       "appel_llm": appel_id, "codage_precedent": ma_ligne,
                                                       "codage": {"ensembles": []}}).execute()))
        essai("relire cette ligne avec la référence à l'appel", "succès",
              lambda: rows(c1.table("codages").select("id").eq("appel_llm", appel_id).execute()))
        essai("référencer un appel inexistant (refusé par la clé étrangère)", "refus",
              lambda: rows(c1.table("codages").insert({"document": doc_id, "etape": "ia_humain", "utilisateur": u1,
                                                       "appel_llm": str(uuid.uuid4()), "codage": {}}, returning="minimal").execute()))

        print("\n--- évaluations ---")
        essai("enregistrer une évaluation de l'IA (sans relecture)", "vide",
              lambda: rows(c1.table("evaluations").insert({"utilisateur": u1, "document": doc_id, "auteur": "ia", "appel_llm": appel_id,
                                                           "verdict": "douteux", "notes": {"organisation": 3}}, returning="minimal").execute()))
        essai("enregistrer sa propre évaluation (humain)", "succès",
              lambda: rows(c1.table("evaluations").insert({"utilisateur": u1, "document": doc_id, "auteur": "humain",
                                                           "notes": {"organisation": 4}}).execute()))
        evals = c1.table("evaluations").select("id, auteur").eq("document", doc_id).execute().data
        essai("relire ses évaluations : seulement celles de l'humain", "succès" if evals and all(e["auteur"] == "humain" for e in evals) else "refus",
              lambda: [e for e in evals if e["auteur"] == "humain"])
        essai("ne jamais relire une évaluation de l'IA", "vide", lambda: [e for e in evals if e["auteur"] == "ia"])

        print("\n--- RUM, profil, nouvelle version de document ---")
        essai("ajouter un RUM à son nom à partir de sa ligne de codage", "succès",
              lambda: rows(c1.table("rum").insert({"document": doc_id, "codage": ma_ligne, "cree_par": u1, "rum": {"DP": "I10"}}).execute()))
        essai("ne pas voir les RUM des autres (aucun autre ici)", "vide",
              lambda: rows(c1.table("rum").select("id").neq("cree_par", u1).execute()))
        essai("créer son profil (accord_le envoyé = 2020 ; la base impose son heure)", "succès",
              lambda: [p for p in rows(c1.table("profils").insert({"id": u1, "nom": "Test", "prenom": "Un", "statut": "medecin_dim",
                                                       "etablissement": "Test", "accord_le": "2020-01-01T00:00:00Z", "version_mention": "0.1"}).execute())
                       if not p["accord_le"].startswith("2020")])
        essai("modifier son profil", "succès", lambda: rows(c1.table("profils").update({"etablissement": "Test 2"}).eq("id", u1).execute()))
        essai("modifier accord_le ou version_mention directement (interdit : colonnes réservées à accepter_mention)", "refus",
              lambda: rows(c1.table("profils").update({"version_mention": "pirate"}).eq("id", u1).execute()))
        essai("accepter la mention (fonction accepter_mention) : accord_le et version_mention mis à jour", "succès",
              lambda: (c1.rpc("accepter_mention", {"version": "0.1-test"}).execute(),
                       [p for p in c1.table("profils").select("version_mention, accord_le").eq("id", u1).execute().data
                        if p["version_mention"] == "0.1-test"])[1])
        essai("non connecté : appeler accepter_mention (interdit)", "refus",
              lambda: rows(anon.rpc("accepter_mention", {"version": "x"}).execute()))
        essai("créer un profil pour un autre compte (interdit)", "refus",
              lambda: rows(c1.table("profils").insert({"id": u2, "nom": "X", "prenom": "Y", "statut": "autre",
                                                       "etablissement": "Z", "accord_le": "2026-10-18T00:00:00Z"}, returning="minimal").execute()))
        # L'insertion ne demande en retour que des colonnes lisibles (nettoyage ne l'est pas) : `select=id`.
        doc2 = essai("ajouter une version 2 du document, signée de son compte (retour limité à id)", "succès",
                     lambda: rows(c1.table("documents").insert({"lot": lot_id, "id_source": "DOC-TEST", "version": 2, "version_precedente": doc_id,
                                                                "motif_version": "test", "texte": "Texte corrigé.", "cree_par": u1})
                                  .execute()) if False else rows(c1.postgrest.from_("documents").insert(
                                      {"lot": lot_id, "id_source": "DOC-TEST", "version": 2, "version_precedente": doc_id,
                                       "motif_version": "test", "texte": "Texte corrigé.", "cree_par": u1}, returning="minimal").execute()) or [{"ok": True}])
        essai("insérer une version en demandant toutes les colonnes en retour (refusé : nettoyage non lisible)", "refus",
              lambda: rows(c1.table("documents").insert({"lot": lot_id, "id_source": "DOC-TEST-RET", "version": 2, "version_precedente": doc_id,
                                                         "motif_version": "test", "texte": "x", "cree_par": u1}).execute()))
        if doc2:
            doc2_id = c1.table("documents").select("id").eq("lot", lot_id).eq("id_source", "DOC-TEST").eq("version", 2).execute().data[0]["id"]
        essai("lire la colonne mesures d'un document", "succès",
              lambda: rows(c1.table("documents").select("id, mesures").eq("id", doc_id).execute()))
        essai("écrire mesures en créant une version 3 (interdit : colonne réservée aux scripts)", "refus",
              lambda: rows(c1.table("documents").insert({"lot": lot_id, "id_source": "DOC-TEST", "version": 3, "version_precedente": doc2_id,
                                                         "motif_version": "test", "texte": "Texte v3.", "cree_par": u1,
                                                         "mesures": {"mots": 2}}, returning="minimal").execute()))
        essai("lire les colonnes générées nb_documents_origine et a_corriger", "succès",
              lambda: rows(c1.table("documents").select("id, nb_documents_origine, a_corriger").eq("id", doc_id).execute()))
        essai("lire la colonne nettoyage d'un document (interdit : colonne jamais affichée)", "refus",
              lambda: rows(c1.table("documents").select("id, nettoyage").eq("id", doc_id).execute()))
        admin.table("documents").insert({"lot": lot_id, "id_source": "DOC-A-CORRIGER", "texte": "Texte à corriger [I10].",
                                         "nettoyage": {"anomalies": {"a_corriger": True, "motif": "test"}}}).execute()
        try:
            vue = c1.table("dossiers_disponibles").select("id_source, nb_documents_origine, longueur").eq("lot", lot_id).execute().data
        except Exception as e:  # noqa: BLE001
            vue = []
            print("         (lecture de la vue impossible :", str(getattr(e, "message", e))[:80] + ")")
        essai("lire la vue dossiers_disponibles : le document de test y est (dernière version, 2)",
              "succès", lambda: [v for v in vue if v["id_source"] == "DOC-TEST"])
        essai("la vue ne montre pas le document signalé à corriger", "vide",
              lambda: [v for v in vue if v["id_source"] == "DOC-A-CORRIGER"])
        essai("la vue ne montre qu'une ligne par document (la dernière version)", "succès" if sum(1 for v in vue if v["id_source"] == "DOC-TEST") == 1 else "refus",
              lambda: [v for v in vue if v["id_source"] == "DOC-TEST"])
        essai("ajouter une version 1 (réservé aux scripts)", "refus",
              lambda: rows(c1.table("documents").insert({"lot": lot_id, "id_source": "DOC-TEST-2", "texte": "x", "cree_par": u1}, returning="minimal").execute()))
        essai("modifier un document (interdit)", "refus",
              lambda: rows(c1.table("documents").update({"specialite": "x"}).eq("id", doc_id).execute()))
        essai("écrire dans une table de référence (interdit)", "refus",
              lambda: rows(c1.table("lots").insert({"id": "x", "source": "x", "version": "x"}, returning="minimal").execute()))

    finally:
        # ---------------------------------------------------------------- 3. nettoyage (clé secrète)
        print("\n=== 4. Nettoyage avec la clé secrète ===")
        try:
            if doc_id is not None:
                ids_docs = [d for d in (doc2_id, doc_id) if d is not None]
                for table in ("rum", "evaluations", "codages", "appels_llm"):
                    admin.table(table).delete().in_("document", ids_docs).execute()
                for d in ids_docs:
                    admin.table("documents").delete().eq("id", d).execute()
                for src in ("DOC-A-CORRIGER", "DOC-TEST-RET"):
                    admin.table("documents").delete().eq("lot", lot_id).eq("id_source", src).execute()
            admin.table("lots").delete().eq("id", lot_id).execute()
            for uid in ids_users:
                admin.auth.admin.delete_user(uid)  # supprime aussi le profil (ON DELETE CASCADE)
            reste = admin.table("documents").select("id").eq("lot", lot_id).execute().data
            print(f"  données et comptes de test supprimés ; documents de test restants : {len(reste)}")
        except Exception as e:  # noqa: BLE001
            print("  ATTENTION, nettoyage incomplet :", e)

    total, ok = len(RESULTATS), sum(RESULTATS)
    print(f"\nBILAN : {ok} essais réussis sur {total}")
    sys.exit(0 if ok == total else 1)


if __name__ == "__main__":
    main()
