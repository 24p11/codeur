# La base de données : appliquer le schéma et tester les accès

*Le schéma lui-même est décrit dans `docs/SCHEMA.md`, qui fait foi. Cette note dit seulement comment le mettre en place et le vérifier.*

## 1. Où est le schéma

Le schéma est écrit sous forme de **migrations** : des fichiers SQL numérotés dans `supabase/migrations/`, appliqués dans l'ordre. Chaque fichier décrit une modification de la base ; on ne modifie jamais un fichier déjà appliqué, on en ajoute un nouveau. Ainsi la base peut toujours être reconstruite à l'identique, et chaque évolution laisse une trace.

| Fichier | Contenu |
|---|---|
| `20261018100000_extensions_et_fonctions.sql` | Extensions `unaccent` et `pg_trgm` ; fonctions `normaliser_texte` et `empreinte_texte` |
| `20261018100100_tables_reference.sql` | `lots`, `documents`, `fiches`, `synonymes`, `regles_situations` ; déclencheur « texte figé » |
| `20261018100200_tables_travail.sql` | `profils`, `appels_llm`, `codages`, `rum`, `evaluations` |
| `20261018100300_index.sql` | Les index |
| `20261018100400_acces.sql` | Les droits de table et les règles d'accès par ligne (RLS) |
| `20261018100500_droits_residuels.sql` | Retrait des droits accordés par défaut par Supabase et non prévus (TRUNCATE, TRIGGER, REFERENCES) ; plus aucun droit par défaut sur les tables futures |
| `20261018110000_commentaire_rum_emplacement_atih.sql` | Mise à jour du commentaire de `rum.rum` après le déplacement du fichier ATIH dans `docs/referentiels/atih/` |

## 2. Ce qu'il faut sur l'ordinateur

- L'outil en ligne de commande de Supabase : `brew install supabase/tap/supabase`.
- Une connexion au compte Supabase : `supabase login` (ouvre le navigateur ; à faire une fois).
- Le dépôt relié au projet : `supabase link --project-ref <identifiant du projet>` (à faire une fois ; crée `supabase/.temp/`, ignoré par git).
- Le fichier `.env` à la racine, jamais versionné, avec les variables listées dans `.env.exemple` :
  `SUPABASE_URL`, `SUPABASE_PROJECT_REF`, `SUPABASE_PUBLISHABLE_KEY` (clé publique), `SUPABASE_SECRET_KEY` (clé secrète), `SUPABASE_DB_PASSWORD` (mot de passe de la base). L'outil Supabase lit lui-même `SUPABASE_DB_PASSWORD` s'il est présent dans l'environnement : les commandes ci-dessous le chargent avec `set -a && . ./.env && set +a`.

## 3. Appliquer les migrations

```
set -a && . ./.env && set +a
supabase migration list          # compare les fichiers locaux et ce que la base a déjà appliqué
supabase db push --dry-run       # affiche les migrations qui seraient appliquées, sans rien faire
supabase db push                 # applique les migrations manquantes, dans l'ordre
```

Règles du projet : avant chaque `supabase db push`, montrer la liste des migrations qui vont être appliquées ; ne jamais lancer une commande qui réinitialise, vide ou supprime la base distante (`supabase db reset` sur le projet relié, par exemple) sans accord explicite du responsable.

Pour faire évoluer le schéma : créer un nouveau fichier `supabase/migrations/<AAAAMMJJHHMMSS>_<nom>.sql`, mettre `docs/SCHEMA.md` à jour, puis appliquer.

**Règle pour toute nouvelle table.** Depuis la migration `20261018100500_droits_residuels.sql`, plus aucun droit n'est accordé par défaut aux testeurs connectés (`authenticated`) ni aux visiteurs (`anon`) sur les tables créées par les migrations. **Toute nouvelle table doit donc recevoir explicitement, dans sa propre migration :**

1. ses droits de table (`grant select, insert … on public.<table> to authenticated;`), limités à ce que `docs/SCHEMA.md` §7 prévoit ;
2. l'activation de la sécurité par ligne (`alter table public.<table> enable row level security;`) ;
3. ses règles par ligne (`create policy …`), une par opération autorisée ;
4. un commentaire sur la table et sur chaque colonne.

Sans ces instructions, la table est inaccessible aux testeurs, ce qui est le comportement voulu par défaut. Le script `scripts/tests/verifier_schema.py` affiche les droits et les règles de chaque table ; `scripts/tests/tester_acces.py` est à compléter avec les essais correspondant à la nouvelle table.

## 4. Vérifier le schéma

```
uv run python -I scripts/tests/verifier_schema.py
```

Lecture seule. Le script se connecte directement à la base (via l'adresse enregistrée par `supabase link` et le mot de passe du `.env`) et affiche les tables avec l'état de la RLS et des commentaires, les colonnes, les contraintes, les index, les déclencheurs, les règles par ligne et les droits des rôles `anon` et `authenticated`.

## 5. Tester les règles d'accès

```
uv run python -I scripts/tests/tester_acces.py
```

Le script crée deux comptes de test et des données de test avec la clé secrète, puis, avec la clé publique et le premier compte connecté, vérifie chaque règle de `docs/SCHEMA.md` §7 : lecture des documents et des référentiels, ajout de ses propres lignes de codage, invisibilité de l'étape `scenario` et des lignes des autres comptes, impossibilité de modifier ou supprimer, enregistrement d'un appel au LLM avec un UUID fourni par la page puis d'un codage qui y fait référence, impossibilité de relire les appels et les évaluations de l'IA, RUM, profil, nouvelle version de document, visiteur non connecté. Il supprime ensuite les données et les comptes de test, même si un essai a échoué. Chaque essai affiche le résultat attendu et le résultat obtenu ; le script se termine en erreur si un essai échoue.

Les bibliothèques nécessaires (`supabase`, `psycopg`) sont dans le groupe de dépendances `tests` du `pyproject.toml` ; `uv run` les installe automatiquement.

## 6. Deux points à connaître pour la page web

- **Insérer sans relire.** Pour `appels_llm` et pour les évaluations de l'IA, le testeur peut écrire mais pas lire : la page doit demander une insertion « sans retour » (`Prefer: return=minimal`, ou `returning="minimal"` dans les bibliothèques Supabase), sinon la base refuse l'insertion.
- **Identifiant des appels au LLM.** La page génère elle-même l'UUID de chaque appel avant de l'insérer, et le reporte dans `codages.appel_llm` ou `evaluations.appel_llm`.
