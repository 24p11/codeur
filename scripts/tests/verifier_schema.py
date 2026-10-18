"""Vérifie que les tables, colonnes, contraintes, index, déclencheurs, règles d'accès et commentaires
décrits dans docs/SCHEMA.md existent dans la base distante. Lecture seule.

Usage : uv run python -I scripts/tests/verifier_schema.py
"""
import sys
from pathlib import Path

import psycopg

sys.path.insert(0, str(Path(__file__).resolve().parent))
from connexion import charger_env, url_postgres  # noqa: E402

TABLES_ATTENDUES = ["lots", "documents", "fiches", "synonymes", "regles_situations",
                    "profils", "appels_llm", "codages", "rum", "evaluations"]


def main() -> None:
    env = charger_env()
    with psycopg.connect(url_postgres(env), connect_timeout=20) as cx, cx.cursor() as cur:
        cur.execute("select current_user, version()")
        u, v = cur.fetchone()
        print(f"connecté en tant que {u} ; {v.split(',')[0]}")

        print("\n=== tables (public) : colonnes, RLS, commentaire ===")
        cur.execute("""
            select c.relname, c.relrowsecurity, obj_description(c.oid, 'pg_class') is not null,
                   (select count(*) from pg_attribute a where a.attrelid = c.oid and a.attnum > 0 and not a.attisdropped),
                   (select count(*) from pg_attribute a where a.attrelid = c.oid and a.attnum > 0 and not a.attisdropped
                      and col_description(c.oid, a.attnum) is null)
            from pg_class c join pg_namespace n on n.oid = c.relnamespace
            where n.nspname = 'public' and c.relkind = 'r' order by 1""")
        trouvees = {}
        for nom, rls, com, ncol, sans_com in cur.fetchall():
            trouvees[nom] = True
            print(f"  {nom:18s} colonnes={ncol:2d}  RLS={'oui' if rls else 'NON'}  commentaire table={'oui' if com else 'NON'}  colonnes sans commentaire={sans_com}")
        manquantes = [t for t in TABLES_ATTENDUES if t not in trouvees]
        print("  tables attendues manquantes :", manquantes or "aucune")

        print("\n=== colonnes de chaque table ===")
        for t in TABLES_ATTENDUES:
            cur.execute("""
                select column_name, data_type, is_nullable, column_default is not null, is_generated
                from information_schema.columns where table_schema='public' and table_name=%s order by ordinal_position""", (t,))
            cols = [f"{c}:{d}{'' if n=='YES' else '!'}{'=' if df else ''}{'~' if g=='ALWAYS' else ''}" for c, d, n, df, g in cur.fetchall()]
            print(f"  {t}: " + ", ".join(cols))
        print("  (légende : ! = obligatoire, = a une valeur par défaut, ~ = calculée)")

        print("\n=== contraintes (hors NOT NULL) ===")
        cur.execute("""
            select conrelid::regclass, conname, contype, pg_get_constraintdef(oid)
            from pg_constraint where connamespace = 'public'::regnamespace order by 1, 3, 2""")
        for rel, nom, typ, d in cur.fetchall():
            print(f"  {str(rel):18s} {typ}  {nom}: {d[:110]}")

        print("\n=== index ===")
        cur.execute("select tablename, indexname, indexdef from pg_indexes where schemaname='public' order by 1, 2")
        for t, i, d in cur.fetchall():
            print(f"  {t:18s} {i}: {d.split(' USING ',1)[1][:90]}")

        print("\n=== déclencheurs et fonctions ===")
        cur.execute("select tgrelid::regclass, tgname from pg_trigger where not tgisinternal and tgrelid::regclass::text not like 'auth.%' order by 1")
        for rel, nom in cur.fetchall():
            print(f"  déclencheur {rel}.{nom}")
        cur.execute("select proname, provolatile from pg_proc where pronamespace='public'::regnamespace order by 1")
        for nom, vol in cur.fetchall():
            print(f"  fonction {nom} (volatilité {vol})")
        cur.execute("select extname, extnamespace::regnamespace from pg_extension where extname in ('unaccent','pg_trgm')")
        for e, s in cur.fetchall():
            print(f"  extension {e} dans le schéma {s}")

        print("\n=== règles d'accès par ligne (policies) ===")
        cur.execute("select tablename, policyname, cmd, roles, qual, with_check from pg_policies where schemaname='public' order by 1, 3, 2")
        for t, p, cmd, roles, q, w in cur.fetchall():
            print(f"  {t:18s} {cmd:7s} {list(roles)} « {p} »  using={q or '-'}  check={w or '-'}")

        print("\n=== droits de table des rôles anon et authenticated ===")
        cur.execute("""
            select table_name, grantee, string_agg(privilege_type, ',' order by privilege_type)
            from information_schema.role_table_grants
            where table_schema='public' and grantee in ('anon','authenticated') group by 1, 2 order by 1, 2""")
        for t, g, p in cur.fetchall():
            print(f"  {t:18s} {g:14s} {p}")
        cur.execute("select count(*) from information_schema.role_table_grants where table_schema='public' and grantee='anon'")
        print("  droits restants pour anon :", cur.fetchone()[0])

        print("\n=== essais fonctionnels (lecture seule) ===")
        cur.execute("select public.normaliser_texte('Diverticulite PERFORÉE du côlon')")
        print("  normaliser_texte :", cur.fetchone()[0])
        cur.execute("select public.empreinte_texte('abc')")
        print("  empreinte_texte('abc') :", cur.fetchone()[0], "(attendu ba7816bf…)")


if __name__ == "__main__":
    main()
