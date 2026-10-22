# La page web

*Mode d'emploi de la page `codeur` (lot A1). Le projet est décrit dans `CADRAGE.md`, la base dans `docs/SCHEMA.md` et `docs/base_de_donnees.md`.*

## 1. Organisation des fichiers

| Fichier | Rôle |
|---|---|
| `web/index.html` | La page, un seul fichier HTML avec tous les écrans (connexion, mention et accord, inscription, profil, liste, dossier) |
| `web/app.js` | Le programme de la page : JavaScript simple, sans outil de construction |
| `web/positions.js` | La convention de positions des passages (§6), partagée avec le test Python |
| `web/style.css` | La mise en forme |
| `web/config.js` | La configuration publique : adresse du projet Supabase et clé publique (`sb_publishable_…`). **La clé secrète n'y entre jamais.** |
| `web/mention_information.md` | Copie de `docs/mention_information.md`, faite par `servir.sh` (au lancement : relancer le serveur, ou recopier, après une modification de la mention) et par la publication ; ignorée par git (une seule version dans le dépôt). Le fichier porte deux repères obligatoires : `<!-- version: … -->` en tête et `<!-- fin-de-la-mention -->` avant la section « Votre accord » |
| `scripts/web/servir.sh` | Lancement en local |
| `scripts/admin/generer_lien.py` | Fabrication manuelle d'un lien de connexion |
| `scripts/tests/tester_positions.py` | Test de la convention de positions (avec Node) |
| `.github/workflows/pages.yml` | Publication automatique sur GitHub Pages |

Bibliothèques chargées depuis un CDN, en version exacte figée : `@supabase/supabase-js` 2.117.2 (jsDelivr) pour la connexion et la base ; `marked` 18.0.14 (jsDelivr) pour afficher la mention écrite en markdown. Les fichiers de la page portent un numéro de version (`?v=A1-0.3`, et `versionPage` dans `config.js`) : l'augmenter à chaque modification pour que les navigateurs rechargent les fichiers.

## 2. Lancer la page sur son ordinateur

```
scripts/web/servir.sh
```

Copie la mention dans `web/` puis sert le dossier sur `http://localhost:8000/` (Ctrl+C pour arrêter ; ouvrir un second terminal pour lancer d'autres commandes pendant ce temps). La page locale parle à la même base Supabase que la page publiée.

## 3. Publier sur GitHub Pages

- À chaque push sur `main` qui touche `web/`, la mention ou le fichier d'automatisation, `.github/workflows/pages.yml` copie la mention dans `web/`, vérifie qu'aucune clé secrète ne s'y trouve, et publie le seul dossier `web/`. Adresse : `https://24p11.github.io/codeur/`.
- Réglage fait une fois dans le dépôt : Settings > Pages > Build and deployment > Source : « GitHub Actions ».
- Suivi d'une publication : onglet Actions du dépôt (ou `gh run list --workflow pages.yml`).

## 4. Réglages Supabase pour la connexion

- Authentication > URL Configuration : **Site URL** `https://24p11.github.io/codeur/` ; **Redirect URLs** `https://24p11.github.io/codeur/**` et `http://localhost:8000/**`.
- Le fournisseur « Email » est actif (connexion par lien, sans mot de passe) ; durée de validité du lien : « Email OTP Expiration » (une heure par défaut).
- **Limite d'envoi** : le service d'envoi intégré de Supabase n'envoie que quelques courriels par heure (message « email rate limit exceeded » sur la page). Avant la diffusion à une centaine de testeurs, brancher un service d'envoi externe (Settings > Authentication > SMTP) ou relever la limite (Authentication > Rate Limits). En attendant, le script de lien manuel ci-dessous.
- La page utilise le mode de connexion « implicite » de Supabase (jetons dans l'adresse de retour), le seul compatible avec les liens fabriqués par le script.

## 5. Fabriquer un lien de connexion à la main

```
uv run python -I scripts/admin/generer_lien.py adresse@exemple.fr           # retour sur la page publiée
uv run python -I scripts/admin/generer_lien.py adresse@exemple.fr --local   # retour sur http://localhost:8000/
```

Affiche un lien à usage unique, valable le temps réglé dans Supabase (une heure par défaut), **sans l'envoyer** : à copier dans un courriel envoyé par vos soins. Si l'adresse n'a pas de compte, Supabase le crée. Attention à bien remplacer l'adresse d'exemple par la vraie adresse du testeur. Si le script s'arrête sur « ReadTimeout » (service d'authentification lent), le relancer. Le serveur local doit être lancé au moment où l'on ouvre un lien `--local`.

## 6. Convention de positions

Toute position dans un texte est un **nombre de points de code Unicode** depuis le début du texte de référence (`documents.texte`), `debut` inclus et `fin` exclu, de sorte que `texte[debut:fin]` en Python, `substr(texte, debut + 1, fin - debut)` en PostgreSQL et `CodeurPositions.extraire(texte, debut, fin)` dans la page donnent exactement le texte cité (`docs/SCHEMA.md` §3.4 : `{ "debut", "fin", "texte" }`).

- JavaScript compte nativement en unités UTF-16 : un caractère hors du plan de base (émoji, lettre mathématique) y compte 2, contre 1 en Python et en PostgreSQL. `web/positions.js` fait la conversion, avec une table de correspondance calculée une fois par texte. La page ne stocke jamais une position UTF-16.
- Les textes sont en forme NFC (accents composés) et ne sont jamais transformés par la page (pas de rendu markdown, pas de fusion d'espaces : `white-space: pre-wrap`).
- À chaque création de passage, la page vérifie que le texte cité est exactement l'extrait aux positions indiquées, et refuse le passage sinon.
- Les scripts Python et les prompts du LLM doivent suivre la même convention. Test : `uv run python -I scripts/tests/tester_positions.py` (Node requis) compare la page et Python sur des textes avec accents, caractères spéciaux, émoji et plusieurs documents d'origine.

## 7. Ce que la page enregistre, et où

- **Dans la base** : le profil (`profils`, à l'inscription et à la modification). Rien d'autre au lot A1.
- **Dans le navigateur seulement** : la session Supabase ; les surlignages (ensembles et passages) par utilisateur et par document, sous la clé `codeur.surlignages.<utilisateur>.<document>`, avec l'empreinte du texte. Si le stockage du navigateur est indisponible, la page l'indique et fonctionne sans sauvegarde. Les surlignages entreront dans la base avec le premier codage (lot A2).
- **Jamais** : la clé secrète ; le codage `scenario` ; le champ `nettoyage` (la base en refuse la lecture aux testeurs).

## 8. Liste d'essais (à faire par Rémi, en particulier depuis un PC de l'AP-HP)

Noter pour chaque essai : navigateur et version, réussite ou échec, message éventuel.

1. **Accès réseau** depuis le réseau hospitalier : `https://24p11.github.io/codeur/` s'affiche ; dans la console du navigateur (F12 > Console), aucune erreur de chargement des bibliothèques (jsDelivr) ; la connexion à Supabase fonctionne (la liste des dossiers se charge) ; pour plus tard, `https://api.mistral.ai/v1/models` répond (une réponse « 401 Unauthorized » suffit : le service est joignable).
2. **Connexion par lien** : saisir l'adresse, recevoir le courriel, cliquer, arriver connecté (adresse en haut à droite). Variante : lien fabriqué par le script.
3. **Première connexion** : mention affichée, bouton « Continuer » inactif tant que les deux cases ne sont pas cochées, fiche d'inscription, arrivée sur la liste. **Mon profil** : date d'accord affichée, modification du nom ou de l'établissement enregistrée.
   **Mention mise à jour** : quand la version du fichier (`<!-- version: … -->`) diffère de celle du profil, la mention est réaffichée avec un bandeau et le bouton « Confirmer mon accord » ; « Mon profil » montre ensuite la version acceptée et la nouvelle date. Si un repère (`version` ou `fin-de-la-mention`) manque dans le fichier, la page refuse d'afficher la mention et signale l'erreur.
4. **Liste** : 3 822 dossiers, pagination, filtres spécialité et type (valeurs en clair avec effectifs), recherche par identifiant, « Effacer ». Aucun texte ni code visible. Les dossiers à corriger (ex. `HEMATOLOGIE-CLINIQUE-00049`) sont absents.
5. **Dossier** : texte lisible, intitulés présents sur un dossier à trois documents (ex. `CHIRURGIE-VISCERALE-00203`), aucun bloc « Résumé structuré ».
6. **Surlignage** : sélectionner un passage à la souris : il est surligné au relâchement ; le compteur au-dessus du texte augmente ; passage à cheval sur deux documents ; une sélection qui chevauche un passage surligné le fusionne (un seul passage) ; au survol d'un passage surligné il passe en rouge barré, un clic le retire ; double-clic sur un mot : le mot est surligné.
7. **Fermeture puis réouverture** du dossier, et du navigateur : surlignages retrouvés. « Tout effacer » avec confirmation.
8. **Déconnexion** : retour à l'écran de connexion ; après reconnexion, les surlignages sont toujours là (ils sont attachés au compte, dans ce navigateur).
9. **Deux navigateurs** (ou deux PC) : les surlignages ne se suivent pas d'un navigateur à l'autre (attendu au lot A1).
10. **Accès au LLM depuis le réseau** : `https://24p11.github.io/codeur/essais/llm.html`, coller sa clé, « Envoyer » : les deux essais (texte, JSON) doivent réussir ; sinon copier le bloc « Résultat ».
11. **Réglages de l'IA** : saisir adresse, modèle, clé ; « Tester la connexion » réussit ; « Oublier mes réglages » efface la clé ; choix de l'affichage A ou B.
12. **Faire le codage** sur un dossier avec 4 à 6 passages surlignés : indicateur d'attente, bouton désactivé, puis le codage sous le texte avec « Principal » sur un seul code, les preuves, les avertissements éventuels ; en cas de code non codable, le tour de correction est visible dans les messages d'étape.
13. **Écran de codage** : changer la catégorie par l'étiquette, 🔍 (début de code, morceaux, suggestions pour un code à choisir, secours « orthographe approchée », infobulle de source), ✕ et ⋯ sur une preuve, glisser-déposer, menu après sélection d'un passage, « Supprimer » un code, « Coder ce passage » dans les rubriques du bas, « Enregistrer mon codage » (compteurs affichés), réouverture avec modifications retrouvées, variantes A et B.
14. **Appel répété** : nouveaux surlignages puis « Faire le codage » : enregistrement automatique de la revue si des modifications existent, chevauchement signalé, seuls les nouveaux passages envoyés, propositions ajoutées ; sans nouveau passage, refus avec message.

## 9. Les modes de l'écran du dossier

L'écran du dossier (dans `web/app.js`, section « Écran du dossier ») est réglé par deux constantes au début de cette section :

| `MODE_PANNEAU` | `MODE_ENSEMBLES` | Comportement |
|---|---|---|
| `false` | (ignoré) | **Mode simple, en service au lot A1** : pas de panneau ni de barre. Le passage est surligné dès que la souris est relâchée ; au survol, un passage surligné passe en rouge barré ; un clic le retire ; une sélection qui chevauche un passage existant est fusionnée avec lui en un seul passage. Au-dessus du texte, une ligne discrète : le nombre de passages et « Tout effacer » (confirmation par un second clic). C'est là que viendra « Faire le codage » (lot A2). Fonctions `surlignerSimple`, `retirerPassageSimple`, `rendreCompte`. |
| `true` | `false` | **Mode passages avec panneau** (désactivé) : barre « Surligner (N) » après sélection ; panneau listant les passages dans l'ordre du texte avec texte cité, positions et « Retirer » ; clic dans le panneau pour défiler, clic sur le texte pour mettre en évidence ; chevauchements conservés distincts (hachures). Fonctions `rendrePanneauPassages`, `surligner`. |
| `true` | `true` | **Mode ensembles** (désactivé, conservé pour la revue, lot A3) : regroupement manuel en ensembles numérotés (nouvel ensemble N, ajout à l'ensemble sélectionné A, retrait, suppression, numéros jamais réattribués). Fonctions `rendrePanneauEnsembles`, `nouvelEnsemble`, `ajouterPassage`, `ajouterAuSelectionne`, `retirerPassage`, `supprimerEnsemble`. À reprendre au lot A3 pour déplacer un passage d'un ensemble à un autre, séparer ou fusionner des ensembles. |

Pour réactiver un mode, changer la constante : l'interface (panneau, barre, titres, raccourcis) s'adapte toute seule. Dans tous les modes, la convention de positions, les contrôles, la sauvegarde locale (format version 2 : `passages` et `ensembles`, avec l'empreinte du texte) et le test sont les mêmes.

## 10. La recherche de codes 🔍

**Recherche par morceaux de mots** (fonction de la base `rechercher_codes_morceaux`, migrations 16 et 17) : ce qui est tapé est normalisé (minuscules, sans accents) et découpé en morceaux aux espaces ; on garde les formulations de `synonymes` qui contiennent **tous** les morceaux, n'importe où (« fract tum » → « Fracture osseuse au cours de maladies tumorales ») ; un morceau de trois lettres ou moins (abréviation : HTA, IDM, FA) ne compte qu'en début de mot. Résultats : codes **codables** seulement, un par code avec sa meilleure formulation, classés : morceaux trouvés comme **mots entiers** d'abord, puis **en début de mot**, puis ceux dont le **libellé officiel** contient les morceaux, puis une autre formulation, puis la formulation la plus courte. L'index trigrammes de `synonymes.formulation_normalisee` est utilisé (1 à 4 ms côté base, 50 à 70 ms aller-retour compris pour « fract tum », « HTA », « insuf card », « hernie ing »).

Dans la page : attente de 300 ms après la dernière touche ; **un code tapé** (M84, C50) est toujours aussi cherché par début de code, **en tête** ; en dessous de trois caractères, seule cette recherche par début de code est faite (une abréviation de deux lettres, comme « FA », serait trop peu sélective : 2,5 s) ; pour un code affinable, ses descendants sont proposés d'abord ; pour un code à choisir, la recherche est préremplie avec le libellé donné par l'IA. Si la recherche par morceaux ne trouve rien, la **ressemblance** (fonction `rechercher_codes`, trigrammes, seuil 0,3) sert de secours, signalée « orthographe approchée ». Chaque recherche est journalisée dans la table `recherches` (texte tapé, mode, nombre de résultats, code choisi ou aucun, contexte), insérée par le testeur sans relecture, pour alimenter plus tard un dictionnaire de synonymes (lot B6).

**La boucle de correction** (`SCHEMA.md` §3.10) utilise, pour un code inconnu ou sans descendant, les codes codables de la catégorie (20 au plus) et la **ressemblance** avec le libellé du modèle (seuil 0,15, 60 au plus), la ressemblance d'abord pour un code inconnu.

- **Limite constatée** (essais du 22 octobre 2026) : la ressemblance porte sur les lettres, pas sur le sens. Pour « Fracture pathologique au cours d'une tumeur maligne secondaire de l'os », les premiers candidats sont des « tumeurs malignes secondaires » d'autres sièges, puis `C795` et `M844` ; `M907x` « Fracture osseuse au cours de maladies tumorales » n'est pas dans les 15 premiers (« maladies tumorales » n'est pas rapproché de « tumeur maligne secondaire »). La recherche par morceaux à partir du libellé du modèle a aussi été essayée : avec les mots les plus longs (pathologique, secondaire, fracture), 0 résultat à trois ou deux mots, 161 résultats hors sujet avec un seul ; avec les mots tronqués à cinq ou quatre lettres, rien de mieux ; avec toutes les paires de mots, seule la paire « fracture + cours » (grâce à « au cours de ») donne `M907`. Elle n'est donc pas utilisée dans la boucle.
- **Piste pour le lot B4** : demander au modèle, avec chaque code, deux ou trois **mots-clés de recherche** (ce qui revient à taper « fract tum »), et les passer à la recherche par morceaux ; c'est le modèle qui sait quels mots comptent.

## 11. L'appel au LLM et l'écran de codage (lot A2-A3)

### 11.1 Réglages de l'IA

Écran « Réglages de l'IA » : adresse du service (défaut `https://api.mistral.ai/v1`), modèle (défaut `mistral-large-latest`), clé, et l'affichage du codage (A liste simple, B encadrés de couleur). Enregistrés **dans le navigateur uniquement** (stockage local, lectures et écritures protégées ; si le stockage est indisponible, les réglages valent pour la session et la clé est redemandée). « Tester la connexion » envoie une mini-demande JSON ; « Oublier mes réglages » efface la clé (à faire sur un PC partagé). « Faire le codage » sans réglages ouvre cet écran. Le **fournisseur** enregistré dans `appels_llm` est déduit de l'adresse (`mistral` pour `api.mistral.ai`, sinon le nom du serveur). La clé ne quitte le navigateur que vers le service du LLM ; elle n'est jamais dans la base, ni dans `appels_llm.requete`, ni dans les messages d'erreur (remplacée par `***` si le service la renvoyait). Mistral autorise les appels directs depuis une page web (vérifié le 21 octobre 2026, page `web/essais/llm.html`).

### 11.2 Les prompts (`web/prompts/`)

Fichiers du dépôt, lus par la page, avec un repère `<!-- version: … -->` en tête, enregistré dans `appels_llm.version_prompt` : `codage_v1.md` (message système du codage ; le message utilisateur est construit par la page : texte complet, liste numérotée des passages, et, pour un appel répété, les codes déjà retenus en lecture seule) et `correction_v1.md` (tour de correction, dans la même conversation). Réponses demandées en JSON strict (`response_format`), température 0.

### 11.3 « Faire le codage » : appel, contrôles, correction, enregistrement

Logique pure dans `web/codage.js` (testée sans appel réel par `scripts/tests/tester_codage.py`, 34 contrôles), enchaînement dans `web/app.js`.

1. UUID de l'appel fabriqué par la page ; appel ; enregistrement dans `appels_llm` dans tous les cas (réussi ou échoué) : tâche `codage`, fournisseur, modèle, version du prompt, requête sans la clé (adresse, modèle, passages numérotés avec positions, messages), réponse brute, tokens, durée, erreur, `appel_initial` (vide pour le premier appel, l'UUID du premier pour les tours de correction).
2. Contrôles : JSON lisible et conforme (sinon message, rien d'enregistré) ; chaque passage présent dans un ensemble ou parmi les non codés (un passage manquant est rangé dans `passages_non_codes` avec l'auteur `outil`, « Passage non traité par l'IA ») ; numéro inconnu ignoré et signalé ; ensemble sans passage valide écarté ; passage dans plusieurs ensembles accepté et signalé ; passage à la fois dans un ensemble et déclaré non codé : l'ensemble l'emporte ; au plus une pathologie principale (la plus confiante gardée, les autres en diagnostic associé, signalé) ; chaque code normalisé (sans point, majuscules) puis cherché dans `fiches` (codable, libellé officiel) et `descendants_codables`.
3. Boucle de correction (`SCHEMA.md` §3.10) : au plus deux tours, dans la même conversation ; candidats = descendants codables (seule liste pour un code tronqué ou père interdit) ; pour un code inconnu ou sans descendant : codes dont une formulation ressemble au libellé du modèle (seuil 0,15) puis 20 codables de la catégorie (catégorie d'abord pour un code connu sans descendant) ; 60 codes au plus ; le modèle répond `{"corrections": {…}}` ; choix hors liste ignoré et signalé.
4. Enregistrement : ligne `ia_humain` avec `codage_precedent` (dernière ligne du testeur sur ce document), `appel_llm` (dernier tour), compteurs (§3.7 : appariement par même code et preuves chevauchantes d'abord, puis par chevauchement), JSON §3.4 avec libellés officiels, preuves recopiées des passages (aucune position ne vient du modèle), codes non codables à `null` avec `code_propose_non_codable`, `libelle_propose` et commentaire `outil`, codes affinables signalés « code plus précis possible », `passages_non_codes`, et le champ `affichage` (variante A ou B utilisée).

### 11.4 L'écran de codage

Sous le texte, dans la même fenêtre. Deux variantes (choix dans les réglages, lu par `varianteAffichage()` dans l'ordre : valeur imposée par le responsable (réservé, à construire), choix du testeur, défaut A) : **A** liste simple (surlignage jaune dans le texte) ; **B** encadrés de couleur (huit couleurs pastel réutilisées, gris pour un code à choisir, la même couleur sur les passages du texte ; un passage partagé garde la couleur du premier code). Pathologie principale en tête. Par code : code et libellé officiel, étiquette « Principal ▾ » / « Associé ▾ » (clic : choix ; « Principal » rétrograde l'ancien), étiquettes « code plus précis possible », « proposé : …, non codable » (code à choisir), « sans preuve », « preuve ajoutée par l'IA », ⓘ (explication et confiance en infobulle), 🔍, « Supprimer ». Par preuve : ✕ (retirer), ⋯ (« Déplacer vers… », « Nouveau code… »), glisser-déposer vers un autre code. Survol d'un code ou d'une preuve : ses passages ressortent dans le texte ; clic sur une preuve dans le texte : son code ressort. Sélection d'un passage dans le texte : menu « Ajouter à … », « Nouveau code… », « Surligner seulement (pour un prochain codage) ». Rubriques du bas : passages non codés (selon l'IA), non traités par l'IA, surlignés pas encore codés, chacun avec « Coder ce passage ». Les remarques `outil` « code à choisir » et « code plus précis possible » disparaissent quand le code change ; la trace « M142 → M1427 » reste.

Sauvegarde : chaque modification est sauvegardée dans le navigateur (`codeur.codage.<utilisateur>.<document>`, avec l'empreinte du texte et l'identifiant de la ligne de base) ; « Enregistrer mon codage » est **actif dès qu'un codage est affiché, même sans modification** (A2-0.14) : il crée la ligne `revue_humain` (compteurs affichés) ; un enregistrement sans modification vaut acceptation du codage tel quel (compteurs « tout conservé »), avec un court message de confirmation. **Réouverture** : la page charge la dernière ligne du testeur sur ce document, puis ses modifications locales si elles ont été faites à partir de cette ligne ; sinon, un bandeau propose « Reprendre mes modifications » ou « Les abandonner ». Le contrôle des positions s'applique à toute preuve ajoutée.

### 11.5 Les appels répétés (`SCHEMA.md` §3.6)

Quand un codage existe : un nouveau surlignage qui chevauche une preuve existante complète ce code (geste du codeur, non envoyé, signalé) ; s'il existe des modifications non enregistrées, la page enregistre d'abord automatiquement une ligne `revue_humain` ; seuls les passages non rattachés sont envoyés, avec les codes retenus en lecture seule dans le message (prompt unique `codage_v1`) ; la page assemble : codes retenus inchangés, propositions sur les nouveaux passages ajoutées (une pathologie principale déjà désignée fait passer la proposition en diagnostic associé), proposition sans nouveau passage écartée et signalée, proposition identique à un code retenu : ses passages ajoutés aux preuves avec commentaire `outil`, étiquette « preuve ajoutée par l'IA » et signalement (à retirer avec ✕). Sans nouveau passage, pas d'appel.

### 11.6 Relire un essai

`uv run python -I scripts/admin/voir_codage.py <id_source>` (clé secrète) affiche les lignes de codage (hors `scenario`) et les appels d'un dossier, sans le texte ni les textes cités, avec le contrôle « clé dans la requête : non ».

## 12. Le filtre par source et la limite de 1 000 lignes (A2-0.13)

La liste des dossiers a un menu **Source** (PARHAF, Synthétique…), alimenté par la table `lots` ; une colonne « Source » dans le tableau ; un tri par source puis identifiant ; les identifiants UUID des CRH synthétiques sont abrégés à l'écran (8 caractères, complet au survol et dans l'en-tête du dossier). Les menus de spécialité et de type ne montrent que les valeurs de la source choisie, avec leur effectif.

**PostgREST ne renvoie jamais plus de 1 000 lignes par requête**, quelle que soit la limite demandée. Les valeurs des menus viennent donc de la fonction `valeurs_filtres()` (migration 19 : par lot, les valeurs distinctes et leur effectif, en une requête courte, droits de l'appelant). Requêtes de la page contrôlées le 22 octobre 2026 au regard de cette limite :

| Requête | Lignes au plus | Verdict |
|---|---|---|
| liste des dossiers (`dossiers_disponibles`, `range` par page de 50, `count: exact`) | 50 | sûre ; le total vient du compte |
| valeurs des menus (`valeurs_filtres()`) | quelques dizaines (2 lots × 56 spécialités × 12 types au plus) | sûre ; remplace la lecture de toute la vue (4 322 lignes, tronquée à 1 000) |
| lots (`lots`) | nombre de lots | sûre |
| ouverture d'un dossier (`documents`, `single`), profil (`profils`), dernier codage (`limit 1`) | 1 | sûre |
| index des codes proposés (`fiches`, `in`) | nombre de codes proposés par le LLM (quelques dizaines) | sûre |
| descendants des codes proposés (`descendants_codables`) | **une requête par code, `limit` = 60 candidats** | corrigée : une seule requête `in` sur tous les codes pouvait dépasser 1 000 lignes (F01 et F02 ont 126 descendants chacun ; les 20 plus gros nœuds en totalisent 1 916) |
| descendants d'un code dans l'écran de codage (`eq noeud`) | 126 au plus (plus gros nœud du kit) | sûre |
| candidats de catégorie (`fiches like`, `limit 60`), recherche 🔍 (`limit 40`), ressemblance (`limite 20` ou `60`), début de code (`limit 40`) | 20 à 60 | sûres |
| écritures (`appels_llm`, `codages`, `recherches`, `profils`) | 1 | sans objet |

## 13. La mise en forme du texte sans retirer un caractère (A2-0.13)

Les CRH synthétiques sont en markdown (`###`, `**`, `---`). Le texte affiché reste **exactement** le texte de référence : `web/markdown.js` repère seulement des intervalles à décorer (en index UTF-16 : ligne de titre `#` à `######` suivi d'une espace ; `**gras**` sur une même ligne ; ligne `---`), et `rendreTexte()` enveloppe chaque morceau dans un `<span>` portant ses classes (`md-titre`, `md-gras`, `md-marque` pour les `#` et `**` eux-mêmes, `md-trait`). Les marques restent dans la page, en gris clair ; le trait `---` est rendu en couleur transparente avec une ligne fine en dessous (les trois tirets sont toujours là, sélectionnables). Les bornes de ces intervalles s'ajoutent aux bornes des surlignages et des preuves ; le calcul des positions à la sélection (`positionDansBloc`, somme des nœuds texte) ne voit aucune différence.

**Interrupteur** : le bouton « Texte brut » / « Mise en forme » au-dessus du texte, mémorisé dans le navigateur (`localStorage`, clé `codeur.mise_en_forme`, mise en forme active par défaut) ; il ne change qu'une classe CSS, sans re-rendu ni effet sur les positions.

**Vérification** : `scripts/tests/tester_positions.py` comporte un texte markdown (titres, gras, trait, un caractère hors plan de base) ; pour chaque passage de chaque texte, Node découpe le texte avec les décorations et le passage, et vérifie que les morceaux restituent le texte entier et que ceux couverts par le passage restituent exactement l'extrait attendu (35 passages sur 35 le 22 octobre 2026 ; 14 décorations sur le texte markdown).

**Corrections A2-0.14** : le menu « Source » affichait chaque source en double, parce que deux appels rapprochés de la liste (restauration de la session, puis changement d'état de connexion) remplissaient chacun les menus avant la fin du premier chargement ; une seule promesse partagée corrige la course, et les menus sont vidés avant d'être remplis.

**Double démarrage et écritures (A2-0.15).** La page reçoit la session deux fois à l'ouverture (lecture de la session, puis événement de changement d'état) ; `demarrer()` ne s'exécute désormais qu'une fois par utilisateur connecté, ce qui protège toutes les lectures de démarrage (profil, mention, liste et ses menus). Contrôle de chaque écriture dans la base, le 22 octobre 2026 : aucune ne part au démarrage, toutes sont déclenchées par un bouton ; envoi du lien de connexion, inscription, « Faire le codage » (appel, codages, revue automatique) et « Enregistrer mon codage » désactivaient déjà leur bouton pendant l'envoi ; le journal des recherches s'efface après une écriture ; **corrigés** : l'accord sur la mention (`accepter_mention`) et la fiche de profil, dont le bouton n'était pas désactivé pendant l'envoi (un double clic envoyait deux fois).

## 14. Le style « Neutre » (brief 7, étape 1, A2-0.16)

Décidé le 22 octobre 2026 sur les essais `web/essais/style.html` (première maquette, écartée) puis `web/essais/dossier.html` (retenu ; dossiers inventés). Le style général de la page ne change pas (police, bleu d'accent, cadres existants) ; l'écran du dossier est réorganisé :

- **La ligne d'informations** (spécialité, puis type de prise en charge, puis documents d'origine, longueur et version, sur trois lignes) est dans un cadre à fond gris clair juste au-dessus du texte, à la largeur du texte.
- **Sous le texte** : le compte des passages (« 3 passages surlignés — cliquez sur un passage pour le retirer »), puis, en dessous, les boutons côte à côte et petits : **Codage · Évaluation · Tout effacer**. « Codage » et « Évaluation » s'excluent (l'un ou l'autre est affiché, le bouton actif est bleu plein). « Codage » lance le codage quand il n'en existe pas encore (il est grisé sans surlignage) et affiche le pavé ; un codage existant se complète par le bouton « Coder les nouveaux passages », qui n'apparaît dans le pavé que si des passages surlignés ne sont rattachés à aucun code (appel répété, SCHEMA.md §3.6). « Évaluation » affiche à la place la rubrique « Noter ce compte rendu » (étape 4).
- **Pavé du codage** inchangé dans sa forme (fond gris, variantes A et B). **Chaque code** : son texte (« K409 – Hernie inguinale… ») sur sa ligne, puis la ligne des fonctions : pastille Principal / Associé (cliquable), « Supprimer », 🔍, 💬 avec le nombre de commentaires, puis les avertissements devenus icônes avec leur explication au survol (⚠ code non codable proposé, ◎ code plus précis possible, ◌ sans preuve, ⚑ preuve ajoutée par l'IA, ⓘ explication de l'IA) ; puis les passages cités à puces (« aucun passage cité » en italique).
- **💬** ouvre les commentaires du code dans la marge à droite du pavé, en face du code (sous le code quand l'écran fait moins de 1 150 px) : auteur en petites capitales (VOUS, IA, OUTIL en italique, SOURCE). La saisie arrive à l'étape 3 du brief 7.
- **« Enregistrer mon codage »** : la ligne d'état, puis le bouton en dessous.
- L'interrupteur « Texte brut » est retiré : la mise en forme du markdown (§13) est toujours active. Le texte du bloc reste exactement le texte de référence ; test de positions 35 sur 35.

## 15. La notation de la qualité du compte rendu (brief 7, étape 4, A2-0.17)

Le bouton **Évaluation** sous le texte affiche, à la place du codage, la rubrique « Noter ce compte rendu ». **La grille** est le fichier versionné `web/grille_qualite.md` (repère `<!-- version: grille_v1 -->`) : un titre `##` par dimension (le sous-titre après « : » est affiché en petit), une ligne par niveau « n — repère ». La page le lit à l'ouverture d'un dossier et refuse une grille incomplète (cinq dimensions, cinq niveaux chacune). Les clés des notes suivent l'ordre des dimensions : `organisation`, `langage`, `coherence_medicale`, `synthese`, `qualite_generale`. La même grille servira plus tard à l'évaluation par le LLM.

**L'écran** : cinq lignes, cinq pastilles de 1 à 5 (le repère de chaque niveau au survol ; un second clic sur la pastille choisie retire la note) ; le repère du niveau choisi reste affiché sous la ligne, « Non notée. » sinon ; un commentaire libre facultatif (1 000 caractères au plus, compte affiché, rappel « Aucune donnée concernant un patient réel ») ; le bouton « Enregistrer ma note », indépendant du codage.

**Règles** : la notation est facultative et ne bloque rien. Une note **incomplète** est acceptée : les dimensions non notées sont enregistrées à `null` (jamais 0), la ligne d'état le rappelle (« 2 dimensions notées sur 5 : une note incomplète peut être enregistrée ») ; l'enregistrement est refusé seulement si aucune dimension n'est notée et le commentaire vide. Chaque enregistrement **ajoute une ligne** dans `evaluations` (auteur `humain`, `notes`, `commentaire`, `version_grille`) ; à la réouverture du dossier, la page relit et affiche la dernière note du testeur (date dans l'en-tête, version de grille signalée si elle diffère de la grille courante). La page ne lit jamais une évaluation de l'IA (la base le refuse, §7 du schéma) et ne montre rien du codage de référence.

## 16. Les trois affichages du codage (brief 7, étape 2, A2-0.18)

Le réglage « Affichage du codage » (navigateur) propose trois variantes, mêmes données et mêmes actions ; la variante utilisée est enregistrée dans `affichage` (`A`, `B` ou `C`) de chaque ligne écrite par la page. **Décidé le 22 octobre 2026 sur l'essai `web/essais/dossier.html`** :

- **A** : le pavé gris, liste simple sans encadré de couleur.
- **B** : chaque code dans un cadre de sa couleur sur fond blanc (le format des cadres de `web/essais/maquette_codage.html` : bord de 2 px, coins arrondis, fond teinté), couleurs d'origine selon le rang du code ; dans le texte, le surlignage reste jaune.
- **C, variante par défaut** : mêmes cadres, avec **une couleur par code, reprise dans le texte** une fois le codage fait.
  - **Palette** : huit teintes claires dérivées d'Okabe-Ito (orange, bleu ciel, vert, jaune, lavande, saumon, mauve, gris), distinguables en vision daltonienne et lisibles sous un texte noir ; au-delà de huit codes, les couleurs reprennent au début.
  - **Stabilité** : la couleur est attribuée par ordre d'apparition et conservée pendant la séance (supprimer un code ne change pas les autres ; un code ajouté prend la première couleur libre ; changer le code d'un ensemble lui garde sa couleur) ; à la réouverture, l'ordre du codage enregistré est repris.
  - **Passage partagé** par deux codes : bandes obliques des deux couleurs, infobulle « Passage partagé par … ».
  - **Après le codage** : les passages surlignés pas encore codés restent jaunes ; les passages déclarés non codés par l'IA sont marqués en gris clair (infobulle avec la raison), en C seulement. Avant le codage, le surlignage garde sa couleur habituelle.
  - Un code à choisir (sans code) est en gris neutre.

## 17. Les commentaires (brief 7, étape 3, A2-0.19)

Le format du codage prévoit des commentaires sur chaque code (`ensembles[].commentaires`) et sur le codage entier (`commentaires`), chacun avec `auteur` et `etape` (SCHEMA.md §3.4).

- **Sur un code** : l'icône 💬 de la ligne des fonctions, avec le nombre de commentaires en exposant, ouvre la marge à droite du pavé (sous le code sur un écran étroit) : les commentaires existants avec leur auteur (VOUS, IA, OUTIL en italique, SOURCE), puis une zone de saisie avec le rappel « Aucune donnée concernant un patient réel », le compte de caractères et « Ajouter ». **Limite : 500 caractères** par commentaire de code.
- **Sur le dossier** : la ligne « Commentaire sur le dossier 💬 » sous la liste des codes ouvre la même marge ; **limite : 1 000 caractères**.
- **Non enregistré** : un commentaire saisi porte, jusqu'à l'enregistrement, la mention « non enregistré » et les boutons ✎ (modifier) et ✕ (supprimer) ; les commentaires déjà enregistrés, ceux de l'IA et de l'outil ne se modifient pas. Toute saisie active « Enregistrer mon codage » et entre dans la sauvegarde locale, comme le reste du codage (§11.4).
- **Enregistrement** : avec le codage, au clic sur « Enregistrer mon codage » (ou lors de la revue automatique avant un appel répété) : les commentaires saisis reçoivent `auteur` `humain` et l'étape de la ligne (`revue_humain`) ; la marque transitoire disparaît. Ils passent d'une ligne à la suivante avec le code auquel ils sont attachés (règles du §3.4).
- Les commentaires d'auteur `outil` restent affichés en italique dans la marge et portés par les icônes d'avertissement (§14).
- Les commentaires ancrés sur un passage du texte ne sont pas dans cette séance.

**Sélecteur d'affichage** : l'en-tête du pavé porte les trois boutons A · B · C, qui changent l'affichage immédiatement et mémorisent le choix dans le navigateur (le même que le réglage « Affichage du codage »).
