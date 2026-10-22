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
| `20261018120000_documents_mesures.sql` | Colonne `documents.mesures` ; insertion dans `documents` accordée colonne par colonne (jamais `mesures`) |
| `20261018130000_dossiers_disponibles.sql` | Lecture de `documents` accordée colonne par colonne (jamais `nettoyage`) ; vue `dossiers_disponibles` pour la liste de la page |
| `20261018140000_documents_colonnes_generees.sql` | Colonnes générées `nb_documents_origine` et `a_corriger`, lisibles ; la vue les lit à la place de `nettoyage` et reste en `security_invoker` |
| `20261018150000_profils_version_mention.sql` | Colonne `profils.version_mention` ; modification de `profils` limitée à nom, prénom, statut, établissement ; fonction `accepter_mention(version)` (seule voie pour `accord_le` et `version_mention`) ; déclencheur : `accord_le` à l'heure de la base à l'inscription |
| `20261022100000_referentiels_recode_icd.sql` | `fiches` : `statut_mco`, `interdit_dp/dr/das` ; `synonymes` : `version_livraison`, unicité (code, formulation, source) ; table `descendants_codables` (lecture seule pour les testeurs) |
| `20261022110000_appels_llm_appel_initial.sql` | `appels_llm.appel_initial` : relie les tours de correction au premier appel |
| `20261022120000_rechercher_codes.sql` / `20261022130000_…operateur.sql` | Fonction `rechercher_codes(recherche, limite, seuil)` : codes codables par ressemblance (trigrammes) ; la seconde corrige l'opérateur qualifié et ajoute le seuil en paramètre |
| `20261022140000_recherche_morceaux_et_recherches.sql` / `20261022150000_…correction.sql` | Fonction `rechercher_codes_morceaux(recherche, limite)` (recherche 🔍 par morceaux de mots) ; table `recherches` (journal des recherches, insertion seule) ; la seconde corrige la fonction et ajoute le critère « mot entier » |
| `20261022160000_recherche_source_formulation.sql` | Les deux fonctions de recherche renvoient aussi la source et l'origine de la formulation |
| `20261022180000_evaluations_version_grille.sql` | Colonne `evaluations.version_grille` (version de `web/grille_qualite.md` utilisée pour la note) ; droits inchangés (insert et select sur la table pour les testeurs, limités par la sécurité par ligne à leurs propres lignes et à leurs évaluations humaines) |
| `20261022170000_valeurs_filtres.sql` | Fonction `valeurs_filtres()` : par lot, les spécialités et types de prise en charge distincts des dossiers disponibles avec leur effectif, pour les listes de filtre de la page (PostgREST renvoie au plus 1 000 lignes par requête ; la page lisait toute la vue). Droits de l'appelant, `search_path` vide, exécutable par les testeurs connectés seulement |

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

Sans ces instructions, la table est inaccessible aux testeurs, ce qui est le comportement voulu par défaut.

**Règle particulière à la table `documents`.** Depuis la migration `20261018130000_dossiers_disponibles.sql`, la lecture de `documents` par les testeurs est accordée **colonne par colonne** (toutes sauf `nettoyage`, jamais affichée), et l'insertion d'une nouvelle version l'est aussi colonne par colonne (depuis `20261018120000_documents_mesures.sql`). **Toute nouvelle colonne de `documents` doit donc recevoir explicitement, dans sa migration, son droit de lecture (`grant select (<colonne>) on public.documents to authenticated;`) et, le cas échéant, son droit d'insertion** ; sinon elle est invisible et non inscriptible pour les testeurs, ce qui est le comportement voulu par défaut. La vue `dossiers_disponibles` (liste des dossiers de la page) est à compléter si la nouvelle colonne doit y figurer.

**Fonctions de la base** : les fonctions appelées par la page (`accepter_mention`, `rechercher_codes`, `rechercher_codes_morceaux`) sont réservées aux testeurs connectés (`revoke … from public, anon` puis `grant execute … to authenticated`), fixent `set search_path = ''` et n'emploient que des noms complets ; `greatest`, `least`, `coalesce` et les opérateurs sont des constructions du langage et ne se qualifient pas, sauf les opérateurs d'extensions (`operator(extensions.%)`). Les réglages de session (seuil de ressemblance) se posent par `set_config(…, true)` dans le corps de la fonction, le rôle des migrations ne pouvant pas les fixer dans sa définition.

Deux colonnes de `documents` sont **générées par la base** à partir de `nettoyage` et lisibles par les testeurs : `nb_documents_origine` et `a_corriger` (migration `20261018140000_documents_colonnes_generees.sql`). C'est grâce à elles que la vue `dossiers_disponibles` reste en mode `security_invoker` (lue avec les seuls droits du testeur) sans jamais lire `nettoyage`.

**Note pour le lot A6 (page d'édition).** Une version créée par la page d'édition ne doit pas hériter du signalement `a_corriger` de la version précédente : la colonne générée se calcule sur le champ `nettoyage` de la nouvelle ligne, dont le contenu sera à définir à ce moment-là (au minimum sans `anomalies.a_corriger`). Par ailleurs, l'insertion d'une nouvelle version doit demander en retour soit rien (`Prefer: return=minimal`), soit uniquement des colonnes lisibles (`select=id`), car le retour « toutes les colonnes » exigerait la lecture de `nettoyage`, refusée. Le script `scripts/tests/verifier_schema.py` affiche les droits et les règles de chaque table ; `scripts/tests/tester_acces.py` est à compléter avec les essais correspondant à la nouvelle table.

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

## 6. Points à connaître pour la page web

- **Insérer sans relire.** Pour `appels_llm` et pour les évaluations de l'IA, le testeur peut écrire mais pas lire : la page doit demander une insertion « sans retour » (`Prefer: return=minimal`, ou `returning="minimal"` dans les bibliothèques Supabase), sinon la base refuse l'insertion.
- **Identifiant des appels au LLM.** La page génère elle-même l'UUID de chaque appel avant de l'insérer, et le reporte dans `codages.appel_llm` ou `evaluations.appel_llm`.
- **Acceptation de la mention.** `accord_le` et `version_mention` ne se modifient que par la fonction `accepter_mention(version)` (appel `rpc` depuis la page) ; à l'inscription, la base impose elle-même l'heure d'accord. Les fonctions en droits du propriétaire fixent toujours `set search_path = ''` et emploient des noms complets (`public.profils`).
