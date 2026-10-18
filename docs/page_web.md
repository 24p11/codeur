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

## 9. Les modes de l'écran du dossier

L'écran du dossier (dans `web/app.js`, section « Écran du dossier ») est réglé par deux constantes au début de cette section :

| `MODE_PANNEAU` | `MODE_ENSEMBLES` | Comportement |
|---|---|---|
| `false` | (ignoré) | **Mode simple, en service au lot A1** : pas de panneau ni de barre. Le passage est surligné dès que la souris est relâchée ; au survol, un passage surligné passe en rouge barré ; un clic le retire ; une sélection qui chevauche un passage existant est fusionnée avec lui en un seul passage. Au-dessus du texte, une ligne discrète : le nombre de passages et « Tout effacer » (confirmation par un second clic). C'est là que viendra « Faire le codage » (lot A2). Fonctions `surlignerSimple`, `retirerPassageSimple`, `rendreCompte`. |
| `true` | `false` | **Mode passages avec panneau** (désactivé) : barre « Surligner (N) » après sélection ; panneau listant les passages dans l'ordre du texte avec texte cité, positions et « Retirer » ; clic dans le panneau pour défiler, clic sur le texte pour mettre en évidence ; chevauchements conservés distincts (hachures). Fonctions `rendrePanneauPassages`, `surligner`. |
| `true` | `true` | **Mode ensembles** (désactivé, conservé pour la revue, lot A3) : regroupement manuel en ensembles numérotés (nouvel ensemble N, ajout à l'ensemble sélectionné A, retrait, suppression, numéros jamais réattribués). Fonctions `rendrePanneauEnsembles`, `nouvelEnsemble`, `ajouterPassage`, `ajouterAuSelectionne`, `retirerPassage`, `supprimerEnsemble`. À reprendre au lot A3 pour déplacer un passage d'un ensemble à un autre, séparer ou fusionner des ensembles. |

Pour réactiver un mode, changer la constante : l'interface (panneau, barre, titres, raccourcis) s'adapte toute seule. Dans tous les modes, la convention de positions, les contrôles, la sauvegarde locale (format version 2 : `passages` et `ensembles`, avec l'empreinte du texte) et le test sont les mêmes.
