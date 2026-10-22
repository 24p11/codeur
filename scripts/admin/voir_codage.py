"""Relit, avec la clé secrète, les codages et les appels au LLM d'un dossier, SANS afficher le texte du document
ni le texte cité des preuves (seulement positions et longueurs). Pour vérifier un essai de « Faire le codage ».

Usage : uv run python -I scripts/admin/voir_codage.py CANCERO-ADULTE-00953 [--utilisateur adresse@exemple.fr]
"""
import argparse
import sys
from pathlib import Path

from supabase import create_client

RACINE = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(RACINE / "scripts" / "tests"))
from connexion import charger_env  # noqa: E402


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("id_source")
    ap.add_argument("--utilisateur", help="adresse du testeur (par défaut : tous)")
    args = ap.parse_args()
    env = charger_env()
    a = create_client(env["SUPABASE_URL"], env["SUPABASE_SECRET_KEY"])
    docs = a.table("documents").select("id, id_source, version, nb_documents_origine, empreinte").eq("id_source", args.id_source).order("version").execute().data
    if not docs:
        raise SystemExit("dossier inconnu")
    comptes = {u.id: u.email for u in a.auth.admin.list_users()}
    cible = {uid for uid, e in comptes.items() if not args.utilisateur or e == args.utilisateur}
    for d in docs:
        print(f"document {d['id']} ({d['id_source']} v{d['version']}, {d['nb_documents_origine']} document(s) d'origine, empreinte {d['empreinte'][:12]}…)")
        codages = a.table("codages").select("id, etape, utilisateur, cree_le, codage_precedent, appel_llm, valide, compteurs, codage") \
            .eq("document", d["id"]).neq("etape", "scenario").order("cree_le").execute().data
        codages = [c for c in codages if c["utilisateur"] in cible]
        print(f"  codages (hors scenario, jamais affiché) : {len(codages)}")
        for c in codages:
            j = c["codage"]
            print(f"  - ligne {c['id']} | {c['etape']} | {comptes.get(c['utilisateur'], '?')} | {c['cree_le'][:19]} | précédent {c['codage_precedent']} | appel {str(c['appel_llm'])[:8]}… | valide {c['valide']}")
            print(f"      compteurs : {c['compteurs']}")
            print(f"      règle {j.get('regle_hierarchisation')} ; mode {j.get('mode_prise_en_charge')} ; {len(j['ensembles'])} ensemble(s) ; {len(j.get('passages_non_codes', []))} non codé(s)")
            for e in j["ensembles"]:
                preuves = ", ".join(f"[{p['debut']}–{p['fin']}]" for p in e["preuves"])
                print(f"      · {e['code'] or 'À CHOISIR'} {('(' + e['code_propose_non_codable'] + ')') if e.get('code_propose_non_codable') else ''} {e['categorie']} | libellé : {str(e['libelle'])[:50]} | confiance {e.get('confiance')} | preuves {preuves}")
                for k in e.get("commentaires", []):
                    print(f"          commentaire {k['auteur']}/{k['etape']} : {k['texte'][:100]}")
            for x in j.get("passages_non_codes", []):
                print(f"      · non codé [{x['debut']}–{x['fin']}] ({x['auteur']}) : {x['raison'][:80]}")
        appels = a.table("appels_llm").select("id, cree_le, utilisateur, tache, fournisseur, modele, version_prompt, tokens_entree, tokens_sortie, tokens_total, duree_ms, erreur, appel_initial, requete, reponse") \
            .eq("document", d["id"]).order("cree_le").execute().data
        appels = [x for x in appels if x["utilisateur"] in cible]
        print(f"  appels au LLM : {len(appels)}")
        for x in appels:
            req = x["requete"] or {}
            cle_presente = "sb_secret" in str(req) or any(k in str(req).lower() for k in ("authorization", "bearer "))
            print(f"  - {str(x['id'])[:8]}… | {x['cree_le'][:19]} | {x['tache']} | {x['fournisseur']} / {x['modele']} | prompt {x['version_prompt']} | tour {req.get('tour')} | "
                  f"initial {str(x['appel_initial'])[:8] + '…' if x['appel_initial'] else '—'} | tokens {x['tokens_entree']}+{x['tokens_sortie']}={x['tokens_total']} | {x['duree_ms']} ms | "
                  f"erreur {x['erreur'] or '—'} | passages envoyés {len(req.get('passages', []))} | messages {len(req.get('messages', []))} | réponse {len(x['reponse'] or '')} car. | clé dans la requête : {'OUI !' if cle_presente else 'non'}")


if __name__ == "__main__":
    main()
