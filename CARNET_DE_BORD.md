# Carnet de bord de `codeur`

*Ce fichier est lu par Claude Code au début de chaque séance. Il dit ce qu'est le projet, les règles à respecter, où en est le travail, les décisions prises et les pièges connus. Claude Code le met à jour en fin de séance (§5, §7 et §9). Il ne remplace pas la documentation détaillée : il dit où elle est.*

*Dernière mise à jour : 24 novembre 2026 (rédigé par Claude le concepteur le 23 novembre ; §5, §7, §8 et §9 tenus par Claude Code depuis).*

---

## 1. Le projet en bref

`codeur` est un **prototype de recherche** de codage CIM-10 assisté par un LLM, destiné à une centaine de testeurs (médecins DIM, TIM), sur PC hospitaliers. Le testeur **surligne** des passages d'un compte rendu ; un LLM (Mistral par défaut, avec la clé du testeur) **regroupe les passages et propose les codes**, puis **la règle de hiérarchisation et le mode de prise en charge** d'après le guide des situations cliniques ; le testeur corrige, commente, note le compte rendu, et enregistre. Tout est enregistré pour mesurer la qualité de l'aide.

Le responsable du projet est **Rémi Flicoteaux, médecin DIM (AP-HP)**. Il n'est pas développeur de métier : on lui explique en français courant, pas à pas, et on ne décide pas à sa place.

Architecture : **page web statique** (JavaScript simple, sans outil de construction) publiée par GitHub Pages (`https://24p11.github.io/codeur/`, fichiers dans `web/`) ; **base Supabase** (PostgreSQL 17, Irlande, sécurité par ligne, connexion par lien courriel) ; **scripts Python** (uv, polars) sur l'ordinateur de Rémi pour charger les données ; le LLM est appelé **depuis le navigateur**.

Corpus : **PARHAF** (3 827 dossiers, CRH rédigés par des médecins, un dossier par patient) et **500 CRH synthétiques** (générés par Mistral dans le projet connexe STREAM/PARTAGES, avec codage de référence complet). Référentiels : l'index des codes et les formulations de **recode-icd** (kit ATIH 2025), le **guide des situations cliniques** et les **extraits officiels du guide méthodologique MCO 2026**.

## 2. Les règles à ne jamais enfreindre

1. **Le dépôt est public : aucun secret, aucune donnée.** Ni texte de CRH, ni clé, ni identifiant de dossier associé à un code du scénario. `donnees/` et `.env` ne sont jamais suivis par git ; `.env` n'est jamais affiché.
2. **Aucun `git push` sans l'accord explicite de Rémi**, et jamais de réécriture de l'historique poussé.
3. **Aucune commande qui supprime ou vide des données de la base** sans l'avoir expliquée et sans accord explicite.
4. **Toute nouvelle table, colonne ou fonction passe par une migration** du dépôt, avec droits explicites, sécurité par ligne et commentaires ; jamais de modification depuis l'interface web de Supabase ; **essai à blanc montré avant chaque `supabase db push`**. Une fonction en droits du propriétaire fixe son chemin de recherche (`search_path` vide). Une migration est appliquée **avant** le push de la page qui l'utilise.
5. **Le testeur ne voit jamais** le codage `scenario`, le champ `nettoyage`, les réponses brutes du LLM ni les évaluations de l'IA : la base elle-même l'interdit, pas seulement l'affichage.
6. **Aucun code non codable n'entre dans un codage.** La liste des codes codables est l'index recode-icd (table `fiches`).
7. **La clé du LLM reste dans le navigateur** : jamais dans Supabase, jamais dans `appels_llm.requete`, jamais dans un message d'erreur enregistré.
8. **Les textes des documents sont figés** ; les positions sont en points de code Unicode, `debut` inclus, `fin` exclu ; aucune modification d'affichage ne retire un caractère du texte.
9. **Les sources de `donnees/` ne sont jamais modifiées.** La livraison recode-icd (index, formulations, fiches) reste hors git : licences non établies.
10. Les lignes de `codages`, `rum` et `commentaires` ne sont **jamais modifiées ni supprimées** : on ajoute.

## 3. Comment on travaille

- **Pas à pas** : après chaque étape, s'arrêter, montrer le résultat (chiffres, captures, description précise), attendre l'accord.
- **Aucune décision de conception seul** : proposer des options avec une recommandation ; Rémi tranche.
- **Mesurer avant de décider.**
- **Français courant**, interface entièrement en français.
- **Avant un commit** : `git ls-files`, vérification de l'absence de secret et de données ; commit ; attendre l'accord pour le push ; suivre la publication GitHub Pages quand `web/` change.
- **Tests à relancer** à chaque séance qui touche à la page ou à la base : tests de codage (`codage.js`, sans appel réel), de positions, de `regles_compatibles`, essais d'accès (`scripts/tests/tester_acces.py`), vérification du schéma.
- **Documentation à tenir** : `docs/SCHEMA.md` (fait foi pour la base, versionné), `docs/page_web.md`, `docs/chargement.md`, `docs/base_de_donnees.md`, `docs/referentiels/README.md`, et ce carnet.
- **En fin de séance** : la liste des points interprétés, et la mise à jour des §5, §7 et §9 de ce carnet.
- Les briefs de Rémi sont des documents complets ; quand une instruction est courte, elle renvoie à ce carnet.
- **Rémi travaille sur deux ordinateurs.** Au début de chaque séance : `git pull` avant toute chose, et signaler ce qui a changé. En fin de séance : rappeler de pousser. `donnees/` et `.env` ne sont pas partagés entre les deux ordinateurs : signaler tout fichier produit dans `donnees/prepare/` dont l'autre ordinateur aura besoin.

## 4. Où sont les choses

| Quoi | Où |
|---|---|
| Cadrage du projet, lots | `CADRAGE.md` |
| Schéma de la base (fait foi) | `docs/SCHEMA.md` (version 1.7, à relire par Rémi) |
| Page web : organisation, convention de positions, variantes, requêtes | `docs/page_web.md` |
| Chargements (PARHAF, référentiels, synthétiques, guide) | `docs/chargement.md` |
| Migrations et règles d'écriture | `docs/base_de_donnees.md`, `supabase/migrations/` (25 migrations) ; commande Supabase installée dans le projet (`npm install`, puis `npx supabase …`) |
| Référentiels publics | `docs/referentiels/` : `atih/` (format RUM, guide méthodologique MCO 2026), `cim/` (README, chapitres, `listes_codes/`, documentation recode-icd), `ccam/listes_actes/` (vide, README), `situations_cliniques/` (guide CSV, extraits officiels CSV et `.md` de relecture), `qualite/` |
| Livraison recode-icd (hors git) | `donnees/referentiels/recode-icd/65701d6_atih-2025/` |
| Sources des corpus (hors git) | `donnees/parhaf/`, `donnees/synthetiques/` ; fichiers préparés dans `donnees/prepare/`. **Au 24 novembre 2026, `donnees/` n'est pas encore sur le nouvel ordinateur (Mac Intel) : Rémi le copiera plus tard.** La page, les tests et les migrations n'en dépendent pas ; les scripts de chargement et les rapports de `donnees/prepare/`, eux, ne sont pas utilisables d'ici là. |
| Page | `web/` : `index.html`, `app.js`, `codage.js` (logique testable par Node), `positions.js`, `markdown.js`, `style.css`, `config.js` (adresse et clé publique Supabase seulement) |
| Prompts, versionnés | `web/prompts/` : `codage_v1`, `codage_v2`, `codage_v3` (utilisé), `correction_v1`, `caracteristiques_v1` |
| Grille de qualité | `web/grille_qualite.md` |
| Mention d'information | `docs/mention_information.md` (version dans un repère `<!-- version: … -->`) |
| Guide du testeur | `docs/guide_testeur.md`, images dans `docs/images/` |
| Scripts | `scripts/chargement/` (PARHAF, référentiels, synthétiques, listes, situations), `scripts/tests/`, `scripts/admin/generer_lien.py`, `scripts/exploration/`, `scripts/referentiels/extraire_guide.py`, `scripts/web/servir.sh` |
| Page d'essai du LLM | `web/essais/llm.html` ; maquettes dans `web/essais/` |
| Rapports hors dépôt | `donnees/prepare/situations/` (défauts des scénarios avec identifiants, mesures, essai des règles) |

## 5. État du projet

*(À tenir à jour par Claude Code : version de la page, nombre de migrations, derniers commits.)*

| Lot | État |
|---|---|
| A1 — lire et surligner | Fait. Connexion par lien, mention versionnée, inscription, liste avec filtres (source, spécialité, type, identifiant), surlignage simple |
| A2 — évaluer et proposer | Fait pour les codes (bouton « Codage », boucle de correction, appels répétés qui complètent) et pour la règle et le mode de prise en charge (second appel automatique). **Reste** : l'évaluation de la qualité du document par le LLM à l'ouverture, avec avertissement |
| A3 — décider | Fait : écran de codage en trois affichages (A liste, B encadrés, C couleur par code), recherche 🔍 par morceaux, commentaires (table), notation du CRH (cinq dimensions) |
| A4 — revoir | **À faire** : revue par l'IA avec les fiches de codes, contrôles fixes, RUM partiel, fils de discussion |
| A5 — noter et diffuser | Grille et guide du testeur faits ; **reste** : mention à compléter, SMTP, clés Mistral, essai depuis un PC de l'AP-HP |
| A6 — éditer les CRH | **À faire** (5 CRH PARHAF `a_corriger` en attente) |
| B1 — PARHAF | Fait (3 827 dossiers ; 21 dossiers à traiter à part : DP père interdit ou inconnu) |
| B2 — CRH synthétiques | Fait (500, graine 20261022, répartition mixte ; rapport des défauts des scénarios dans `docs/`) |
| B3 — référentiels | Fait pour l'index, les formulations, les descendants codables, les chapitres, les listes de codes, le guide des situations cliniques avec extraits officiels ; **reste** : le contenu des fiches (pour A4) |
| B4 — banc d'essai des prompts | **À faire** (comparer `codage_v1/v2/v3`, options a/b/c du second appel, mots-clés demandés au modèle pour la correction) |
| B5 — export et analyse | **À faire** (pondération par gabarit, codes affinables comptés à part, dossiers à part) |
| B6 — dictionnaire de synonymes | En cours côté recode-icd (chantier ouvert) ; `codeur` enregistre déjà les recherches (`recherches`) |

Page publiée : **A2-0.27** (24 novembre 2026 : correctif `top_p` et nouveaux essais sur 429 et 503). Base : **25 migrations**, toutes appliquées (essai à blanc du 24 novembre : rien en attente). Tests du 24 novembre : codage 79, positions 35, règles 14, accès 78, schéma vérifié. Commande Supabase : 3.3.0 par `npx`. **Reste sur le nouvel ordinateur** : `npx supabase login` puis la liaison (par Rémi), et la copie de `donnees/`.

## 6. Les décisions fixées

Les décisions suivantes ont été prises avec Rémi ; on ne les rouvre pas sans lui.

**Codes et codage**
- Codes écrits **sans point, extension PMSI collée** (`K409`, `Z992+0`, `F03+00`) ; la forme de référence est `code_atih` de recode-icd ; l'extension « ni » n'existe pas dans le kit 2025.
- Seul le **code complet** fait foi ; la catégorie à trois caractères ne sert qu'aux statistiques.
- Un code non codable proposé par le LLM passe par la **boucle de correction** (descendants codables, sinon catégorie, au plus 60 codes, au plus 2 tours, température 0), puis « à choisir » par le codeur. Un code **codable mais affinable** (souche avec descendants, `Z992`) est accepté et signalé « code plus précis possible » (option B).
- Le LLM **désigne les passages par leur numéro** ; la page recopie les positions. Un passage peut appuyer plusieurs codes ; au-delà de deux, signalé.
- Le codage a trois éléments : **pathologie principale, pathologies associées, mode de prise en charge** (`DP` ou code Z, avec libellé), plus la **règle de hiérarchisation**. DP et DR du RUM s'en déduisent.
- **Un passage surligné est un passage à coder** ; antécédents, états sevrés et facteurs de risque se codent (F17, F10, Z85-Z92), pas de codes Z pour le tabac et l'alcool (`codage_v3`).
- Preuves **directes** (nomment l'affection, affichées en gras) et **indirectes** (étayent) ; champ `nature`.
- Règles **M1 et M2** citées mot pour mot dans `codage_v3` pour départager deux pathologies principales ; la page n'en garde qu'une.

**Appels au LLM**
- **Un seul bouton « Codage »**, utilisable autant de fois qu'on veut : on **complète**, on ne refait pas ; seuls les passages rattachés à aucun code partent ; le codage existant est transmis en lecture seule ; les codes supprimés par le codeur sont **rejetés** (`codes_rejetes`) et le modèle est prié de ne pas les reproposer.
- **Température 0** partout (stabilité) ; chaque appel enregistré dans `appels_llm` avec sa version de prompt ; les tours de correction reliés par `appel_initial`.
- **Second appel** (règle et mode) enchaîné automatiquement après le premier, pas de recalcul aux appels suivants, « Recalculer la règle » avec commentaire facultatif ; **option (a)** : tout le guide pertinent est envoyé (préambule, extraits des règles compatibles, passages communs une fois, listes de codes Z), ≈ 12 000 tokens ; passage à (c) prévu par une constante.
- Le guide est donné au LLM par **extraits officiels mot pour mot** du guide méthodologique MCO 2026, avec section et page ; jamais reformulés.
- Les **règles compatibles** avec la pathologie principale sont calculées par la base (`regles_compatibles`) ; T10-irradiations non évaluable (listes d'actes absentes).
- Le prompt est un **fichier versionné** ; une nouvelle version est un nouveau fichier, l'ancien reste intact.

**Base et modèle de données**
- Une ligne de `codages` par étape, **jamais modifiée** ; comparaison par appariement des preuves (même code et chevauchement d'abord).
- **Les commentaires sont dans la table `commentaires`** (objet : séjour, code, mode de prise en charge, règle ; auteur : humain, ia, outil ; type : explication, remarque, discussion, alerte, retrait) ; rattachés au code sur lequel ils ont été écrits ; retrait par une ligne de type `retrait` ; les explications de l'IA sont des commentaires, pas des champs.
- `dr_conforme` est un **contrôle qualité**, affiché, non enregistré dans le codage ; il ira dans `rum.controles` (A4).
- **Plafond de 1 000 lignes** par requête de la page : toute requête qui pourrait le dépasser est paginée ou remplacée par une fonction de la base.
- Les listes de codes et les chapitres sont **dans la base** (`listes_codes`, `chapitres`), les fichiers du dépôt restant la source ; le guide ne garde que les noms des listes.
- Les codes Z80-Z99 en DP ne sont pas comptés comme défauts des scénarios (règle D4).

**Affichage**
- Style **sobre** (police du système, une colonne, bleu d'accent, peu d'encadrés) ; markdown mis en forme sans retirer de caractère.
- Mode de prise en charge présenté **comme un code** en tête du pavé, sur fond neutre ; règle au format d'une preuve.
- La notation du CRH est **facultative**, enregistrée à part, sur la grille `web/grille_qualite.md` (version enregistrée).

## 7. Ce qui reste à faire, par ordre de priorité

*(À tenir à jour.)*

**Avant de diffuser le lien aux testeurs** (côté Rémi, sauf mention contraire)
1. Compléter la **mention d'information** (`[À COMPLÉTER]` : projet, responsable, durée, contact, DPO).
2. Décider comment les testeurs obtiennent une **clé Mistral** (compte personnel ou clés du projet) ; compléter le guide du testeur en conséquence (trois `[À COMPLÉTER]`).
3. **Envoi des liens de connexion** : le service intégré de Supabase est limité à quelques courriels par heure ; brancher un service SMTP au-delà d'une poignée de testeurs (Claude Code, sur demande).
4. **Essai depuis un PC de l'AP-HP** : page, Supabase et API Mistral joignables ? (`docs/page_web.md`, liste d'essais ; `web/essais/llm.html`).
5. Trois captures manquantes dans le guide (mention, liste des dossiers, un code avec ses icônes).

**Petites tâches en suspens**
- Compléter la **liste de codes Z de T1** (tableau dans `donnees/prepare/situations/t1_codes_Z49_Z51.csv`) ; reporter dans la feuille Google de Rémi les corrections du CSV du guide (SD2, T1, T7, T10-irradiations, chapitres étendus).
- Transmettre au projet de génération le rapport des défauts des scénarios.
- Colonne `documents.mesures` : vide, à remplir par un script Python (mesures de NLP, contrat de format avec le projet de génération).

**Lots suivants**
- **A4** : revue par l'IA avec les fiches (chargement du contenu des fiches, prompt de revue, écran des recommandations, contrôles fixes, RUM partiel, `dr_conforme` dans `rum.controles`, fils de discussion ; les explications de l'IA deviendraient des commentaires typés au même endroit).
- **A2, fin** : évaluation de la qualité du document par le LLM à l'ouverture (grille existante, verdict, avertissement « document atypique », option 2 : ne pas montrer les notes).
- **A6** : page d'édition des CRH (nouvelle version, motif ; les 5 PARHAF `a_corriger`).
- **B4, B5, B6** (voir §5). Pour B6 : recode-icd livrera `equivalences.csv` (mode strict : seules les équivalences livrées sont appliquées ; `codeur` enregistre la version du dictionnaire avec chaque recherche et exporte les candidats).

## 8. Les pièges connus

- **PostgREST ne renvoie jamais plus de 1 000 lignes** : menus et descendants l'ont déjà subi.
- **La page démarre deux fois** (session restaurée puis événement de connexion) : toute lecture ou écriture de démarrage doit être protégée ; les boutons sont désactivés pendant l'envoi.
- **Règle de sécurité qui relit sa propre table** = récursion infinie ; passer par une fonction en droits du propriétaire (`commentaire_retirable`).
- **`least`/`greatest` ne se préfixent pas** par `pg_catalog.` dans une fonction (migration 17).
- **Le guide des situations cliniques** avait « chapitres I à XVII », qui excluait à tort XIX (traumatologie) et XXII ; étendu. Le chapitre XVIII reste exclu (symptômes → D2).
- **Z51 entier** dans T1 ferait entrer Z515 (T11) et Z5101 (T10) ; T7 est Z43-Z47 et Z490 seulement.
- **Les formulations de recode-icd ne sont pas un dictionnaire d'équivalences** : « HTA pulmonaire » ou « tumeur / tumorales » ne se rejoignent pas ; la recherche par ressemblance porte sur les lettres, pas le sens (lot B6).
- **Les LLM tronquent les codes** (extension omise, niveau trop large) ; ils n'inventent presque jamais, sauf exception (`M8590+1`).
- Avec **un seul passage** surligné dans un long texte, `codage_v1` codait tout le dossier : la v2 et la v3 restreignent au surligné.
- Le **tour de correction** poursuit la même conversation que l'appel de codage.
- Les scénarios synthétiques ont des **défauts connus** (codes Z en DP, règle incompatible, T1 avec DP, M14 à cinq caractères) : dossiers à traiter à part dans les analyses, comme les 21 PARHAF.
- Les commentaires d'auteur `ia` et `outil` sont écrits **avec la session du testeur** (limite acceptée pour le prototype ; `appel_llm` obligatoire pour une explication de l'IA).
- Les captures d'écran du guide ne doivent montrer **aucune donnée personnelle** ; une image commitée reste dans l'historique public.
- **Mistral, HTTP 429 « Rate limit exceeded »** : limite de débit du compte du testeur. Depuis A2-0.27, la page réessaie d'elle-même sur 429 et 503 (3 essais, `Retry-After` sinon 3 s puis 8 s, plafond 60 s), espace les appels d'une seconde, et propose « Réessayer » si tout échoue (`docs/page_web.md` §21). Conséquence dans `appels_llm` : **une ligne par tentative** ; pour compter les appels, ne garder que les lignes sans `erreur` ou regrouper par `requete.appel_vise`. `Retry-After` n'est lisible par la page que si le fournisseur l'expose (non vérifié chez Mistral).
- **Mistral, HTTP 400 « top_p must be 1 when using greedy sampling »** (code 3054) : constaté le 23 novembre 2026, tous les appels échouaient. D'après `appels_llm`, le refus a commencé **entre le 11 novembre 16 h 11 (dernier appel réussi) et le 17 novembre 11 h 54 (premier refus)** ; 4 appels de codage refusés (3 le 17, 1 le 19), un seul testeur, 4 documents, aucun codé depuis ; aucun codage enregistré n'a été abîmé. La page n'envoyait **pas** `top_p` (seulement `temperature: 0`) : c'est la valeur par défaut appliquée par Mistral qui n'était pas 1. Il faut donc **écrire `top_p: 1`** dans la requête, ne pas l'omettre (A2-0.26). Leçon : ne jamais compter sur les valeurs par défaut du service pour l'échantillonnage. La forme de la requête est fixée en un seul endroit (`corpsRequete`, `web/codage.js`) et vérifiée par les tests de codage. *Correctif non encore essayé sur un appel réel (pas de clé sur cet ordinateur le 23 novembre) : à confirmer par « Tester la connexion ».*

- **Publication GitHub Pages** : le 24 novembre, l'étape `deploy-pages` a échoué deux fois (« No artifacts named "github-pages" were found ») alors que le paquet existait. Cause : téléversement et publication dans la **même tâche**, la publication cherchant le paquet une fraction de seconde trop tôt (défaut connu, `actions/deploy-pages` n° 451). Mettre les actions à jour (v7, v6, v5, v5) n'a rien changé ; **couper en deux tâches** (« construire », puis « publier » avec `needs`) a réglé le problème. Ne jamais utiliser « Re-run » sur une publication en échec (second paquet dans la même exécution) : lancer une exécution neuve par Actions > Publier la page web > Run workflow. Toujours vérifier que la version publiée (`config.js`) a bien changé après un push. Les journaux d'une exécution ne se lisent pas sans être connecté à GitHub (`gh` absent du nouvel ordinateur).
- **Nouvel ordinateur (Mac Intel, macOS 15)** : Homebrew n'y fournit plus de paquets prêts et bute sur les outils Apple ; la commande Supabase est donc installée dans le projet par npm (`npx supabase`). `supabase link` demande `npx supabase login` (navigateur, par Rémi). Les tests de la base se lancent avec `uv run --group tests`.

## 9. Journal des séances

*(Une ligne ou deux par séance, les plus récentes en bas. À tenir par Claude Code.)*

- **18 oct. 2026** — Exploration des corpus ; schéma de la base ; création des tables (7 migrations) ; chargement de PARHAF (B1) ; page A1 (connexion, mention, inscription, liste, surlignage simple). Migrations 8-11 (`mesures`, `nettoyage` fermé, colonnes calculées, version de la mention).
- **21-22 oct.** — Lots A2-A3 : test réseau Mistral (appel direct possible), index et formulations recode-icd (migration 12), réglages de l'IA, prompts `codage_v1` et `correction_v1`, « Faire le codage » avec boucle de correction, écran de codage, appels répétés, recherche 🔍 par morceaux (migrations 13-18, table `recherches`). B2 : 500 CRH synthétiques, filtre par source, markdown (migration 19). Brief 7 : style sobre, trois affichages, commentaires, notation (migration 20).
- **23 oct.** — Un seul bouton « Codage », codes rejetés, `codage_v2` (preuves directes/indirectes), température 0 confirmée.
- **23-24 oct.** — Brief 8 : référentiels CIM dans `docs/` et dans la base (migration 21), extraits officiels du guide méthodologique, guide des situations cliniques v1 (migration 22), `regles_compatibles` (23), second appel règle et mode de prise en charge (`caracteristiques_v1`), table `commentaires` (24, 25), `codage_v3` (M1-M2, facteurs de risque), SCHEMA 1.6. Page A2-0.24.
- **26 oct.** — Guide du testeur (`docs/guide_testeur.md`), lien « Aide », README. Page A2-0.25.
- **10 nov.** — Erreur Mistral 429 (limite de débit) constatée ; correction demandée (nouveaux essais automatiques). *À confirmer par Claude Code : faite ou non.*
- **23 nov.** — Erreur Mistral 400 `top_p` constatée ; reprise sur un nouvel ordinateur. Correctif A2-0.26 : `top_p: 1` écrit dans toutes les requêtes, forme de la requête dans `web/codage.js`, 4 contrôles ajoutés (codage : 67). **Nouvel ordinateur incomplet** : pas de commande `supabase`, pas de `.env`, pas de `donnees/` ; donc liaison Supabase, essai à blanc des migrations, tests règles/accès/schéma et recherche du code 3054 dans `appels_llm` **non faits**. La correction du 429 (10 nov.) n'était **pas** dans le dépôt.
- **24 nov.** — Push de A2-0.26, publication en échec (§8). Page A2-0.27 : nouveaux essais sur 429 et 503, une ligne d'`appels_llm` par tentative, pauses d'une seconde, bouton « Réessayer » ; 12 contrôles ajoutés (codage : 79) ; SCHEMA 1.7 ; carnet commité. Publication réparée (deux tâches, §8) : page **A2-0.27 en ligne**. Commande Supabase par npm (`package.json`). `.env` copié : migrations 25 sur 25, essai à blanc sans rien en attente, tests règles 14, accès 78, schéma vérifié ; code 3054 daté dans `appels_llm` (§8). **Restent** : `npx supabase login` et la liaison (Rémi), la copie de `donnees/`, et l'essai du correctif `top_p` et des nouveaux essais sur un appel réel (Rémi, « Tester la connexion »).

## 10. Pour Rémi : écrire une instruction courte

Avec ce carnet, une instruction peut tenir en quelques lignes. Le modèle :

> Lis `CARNET_DE_BORD.md`, puis `[les sections de la documentation utiles]`.
> **Objectif** : `[une phrase]`.
> **Dans la séance** : `[ce qu'il faut faire, en étapes numérotées]`.
> **Hors de la séance** : `[ce qu'on ne touche pas]`.
> Les règles du §2 et la façon de travailler du §3 s'appliquent. `[Si une migration ou un prompt est en jeu : « montre-moi … avant de … »]`.
> À la fin : tests, documentation, liste des points interprétés, mise à jour du carnet, commit, et attends mon accord pour le push.

Trois exemples :

> Lis `CARNET_DE_BORD.md`. Objectif : brancher un service SMTP pour l'envoi des liens de connexion. Propose-moi les options (fournisseurs, coût, réglages Supabase), sans rien configurer avant mon accord. Les secrets vont dans `.env`, jamais dans le dépôt.

> Lis `CARNET_DE_BORD.md` et `docs/page_web.md` §19. Défaut constaté : `[description]`, sur le dossier `[identifiant]`. Reproduis, trouve la cause, corrige, ajoute un test, et montre-moi avant de commiter.

> Lis `CARNET_DE_BORD.md` et `docs/SCHEMA.md` §4 et §5.5. Objectif : lot A4, revue par l'IA avec les fiches. Avant d'écrire du code, propose-moi le déroulement et les écrans, avec les options et ta recommandation ; je trancherai, puis Claude (le concepteur) rédigera le brief complet.

Ce qu'il est inutile de répéter : les règles de sécurité, la façon de travailler, l'architecture. Ce qu'il faut toujours dire : l'objectif, le périmètre, et les points où tu veux être consulté avant que ça avance.
